"""Production-ready intent classification API with hot model reload and rollback."""

from __future__ import annotations

import argparse
import copy
import json
import logging
import os
import threading
import time
import uuid
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Deque, Dict, List, Optional

import torch
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from peft import PeftModel


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("project2_1.intent_api")


BASE_MODEL_NAME = os.getenv("BASE_MODEL_NAME", "Qwen/Qwen3-8B")
DEFAULT_MODEL_PATH = os.getenv("MODEL_PATH", "./qwen3-intent-lora")
REQUIRE_MODEL_ON_STARTUP = os.getenv("REQUIRE_MODEL_ON_STARTUP", "true").lower() == "true"
MAX_HISTORY_MODELS = int(os.getenv("MAX_HISTORY_MODELS", "2"))
MAX_RELOAD_JOBS = int(os.getenv("MAX_RELOAD_JOBS", "30"))
PREDICT_MAX_LENGTH = int(os.getenv("PREDICT_MAX_LENGTH", "128"))


class ModelManagerError(Exception):
    """Base class for model manager related errors."""


class ModelNotReadyError(ModelManagerError):
    """Raised when active model is not available."""


class ReloadInProgressError(ModelManagerError):
    """Raised when another reload task is already running."""


class ReloadJobNotFoundError(ModelManagerError):
    """Raised when reload job id is not found."""


class RollbackNotAvailableError(ModelManagerError):
    """Raised when no rollback target is available."""


class ModelLoadError(ModelManagerError):
    """Raised when model loading failed."""


@dataclass
class ModelBundle:
    """Immutable snapshot of a loaded model."""

    model: Any
    tokenizer: Any
    id2label: Dict[str, str]
    model_path: str
    version: str
    loaded_at: float


class IntentRequest(BaseModel):
    """Inference request body."""

    text: str = Field(..., description="User natural language sentence", examples=["我要退票"])


class IntentResponse(BaseModel):
    """Inference response body."""

    model_config = {"protected_namespaces": ()}

    text: str
    intent: str
    confidence: float
    model_version: str
    model_path: str


class ReloadRequest(BaseModel):
    """Admin reload request."""

    model_config = {"protected_namespaces": ()}

    model_path: str = Field(..., description="Filesystem path of new model or LoRA adapter")
    version: Optional[str] = Field(default=None, description="Human readable model version")
    warmup_texts: Optional[List[str]] = Field(
        default=None,
        description="Optional warmup texts; each text is a dry-run prediction",
    )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_device() -> str:
    return "cuda" if torch.cuda.is_available() else "cpu"


def _resolve_dtype() -> torch.dtype:
    return torch.float16 if torch.cuda.is_available() else torch.float32


def _normalize_id2label(mapping: Dict[Any, Any]) -> Dict[str, str]:
    normalized = {}
    for key, value in mapping.items():
        normalized[str(key)] = str(value)
    return normalized


def _load_label_mapping(model_path: str, model_config: Optional[Any] = None) -> Dict[str, str]:
    mapping_path = os.path.join(model_path, "label_mapping.json")
    if os.path.exists(mapping_path):
        with open(mapping_path, "r", encoding="utf-8") as file:
            payload = json.load(file)
        id2label = payload.get("id2label")
        if not isinstance(id2label, dict):
            raise ModelLoadError(f"invalid label_mapping.json: {mapping_path}")
        return _normalize_id2label(id2label)

    if model_config is not None and getattr(model_config, "id2label", None):
        return _normalize_id2label(model_config.id2label)

    raise ModelLoadError(
        f"label mapping not found under {model_path}; expected label_mapping.json or model config id2label"
    )


def _default_model_loader(model_path: str) -> ModelBundle:
    if not os.path.exists(model_path):
        raise ModelLoadError(f"model path does not exist: {model_path}")

    device = _resolve_device()
    dtype = _resolve_dtype()
    adapter_config_path = os.path.join(model_path, "adapter_config.json")
    is_lora_adapter = os.path.exists(adapter_config_path)

    base_model_name = BASE_MODEL_NAME
    if is_lora_adapter:
        with open(adapter_config_path, "r", encoding="utf-8") as file:
            adapter_config = json.load(file)
        base_model_name = adapter_config.get("base_model_name_or_path") or BASE_MODEL_NAME

    try:
        tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    except Exception:
        tokenizer = AutoTokenizer.from_pretrained(base_model_name, trust_remote_code=True)

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model_kwargs: Dict[str, Any] = {
        "trust_remote_code": True,
        "torch_dtype": dtype,
    }
    if device == "cuda":
        model_kwargs["device_map"] = "auto"

    if is_lora_adapter:
        id2label = _load_label_mapping(model_path)
        base_model = AutoModelForSequenceClassification.from_pretrained(
            base_model_name,
            num_labels=len(id2label),
            **model_kwargs,
        )
        model = PeftModel.from_pretrained(base_model, model_path)
    else:
        model = AutoModelForSequenceClassification.from_pretrained(
            model_path,
            **model_kwargs,
        )
        id2label = _load_label_mapping(model_path, model_config=getattr(model, "config", None))

    if device != "cuda":
        model = model.to("cpu")

    model.eval()
    version = os.path.basename(os.path.abspath(model_path)) or model_path
    return ModelBundle(
        model=model,
        tokenizer=tokenizer,
        id2label=id2label,
        model_path=model_path,
        version=version,
        loaded_at=time.time(),
    )


def _predict_with_bundle(bundle: ModelBundle, text: str) -> Dict[str, Any]:
    inputs = bundle.tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=PREDICT_MAX_LENGTH,
        padding=True,
    )

    model_device = getattr(bundle.model, "device", None)
    if model_device is None:
        try:
            model_device = next(bundle.model.parameters()).device
        except StopIteration:
            model_device = torch.device("cpu")

    prepared_inputs = {}
    for key, value in inputs.items():
        prepared_inputs[key] = value.to(model_device) if hasattr(value, "to") else value

    with torch.no_grad():
        outputs = bundle.model(**prepared_inputs)
        logits = outputs.logits
        probabilities = torch.softmax(logits, dim=1)
        predicted_class_id = int(torch.argmax(logits, dim=1).item())
        confidence = float(probabilities[0][predicted_class_id].detach().cpu().item())

    predicted_intent = bundle.id2label.get(str(predicted_class_id), str(predicted_class_id))
    return {
        "text": text,
        "intent": predicted_intent,
        "confidence": confidence,
        "model_version": bundle.version,
        "model_path": bundle.model_path,
    }


def _default_warmup_runner(
    predictor: Callable[[ModelBundle, str], Dict[str, Any]],
) -> Callable[[ModelBundle, List[str]], None]:
    def warmup(bundle: ModelBundle, warmup_texts: List[str]) -> None:
        for text in warmup_texts:
            if text and text.strip():
                predictor(bundle, text.strip())

    return warmup


class ModelManager:
    """Thread-safe model manager with async reload jobs and rollback support."""

    def __init__(
        self,
        model_loader: Callable[[str], ModelBundle],
        predictor: Optional[Callable[[ModelBundle, str], Dict[str, Any]]] = None,
        warmup_runner: Optional[Callable[[ModelBundle, List[str]], None]] = None,
        history_limit: int = MAX_HISTORY_MODELS,
        max_jobs: int = MAX_RELOAD_JOBS,
    ):
        self._model_loader = model_loader
        self._predictor = predictor or _predict_with_bundle
        self._warmup_runner = warmup_runner
        self._history_limit = max(1, history_limit)
        self._max_jobs = max(10, max_jobs)

        self._state_lock = threading.RLock()
        self._active: Optional[ModelBundle] = None
        self._history: Deque[ModelBundle] = deque(maxlen=self._history_limit)
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._running_job_id: Optional[str] = None

    def initialize(self, model_path: str, version: Optional[str] = None) -> Dict[str, Any]:
        bundle = self._model_loader(model_path)
        if version:
            bundle.version = version
        with self._state_lock:
            self._active = bundle
            self._history.clear()
        logger.info("initial model loaded: %s (version=%s)", model_path, bundle.version)
        return self._bundle_summary(bundle)

    def submit_reload(
        self,
        model_path: str,
        version: Optional[str] = None,
        warmup_texts: Optional[List[str]] = None,
    ) -> str:
        with self._state_lock:
            if self._running_job_id is not None:
                raise ReloadInProgressError(
                    f"reload already running with job_id={self._running_job_id}"
                )

            job_id = str(uuid.uuid4())
            self._jobs[job_id] = {
                "job_id": job_id,
                "state": "running",
                "model_path": model_path,
                "version": version,
                "warmup_texts_count": len(warmup_texts or []),
                "created_at": _utc_now(),
                "updated_at": _utc_now(),
                "error": None,
            }
            self._running_job_id = job_id

        thread = threading.Thread(
            target=self._run_reload_job,
            args=(job_id, model_path, version, warmup_texts or []),
            daemon=True,
        )
        thread.start()
        return job_id

    def _run_reload_job(
        self,
        job_id: str,
        model_path: str,
        version: Optional[str],
        warmup_texts: List[str],
    ) -> None:
        try:
            bundle = self._model_loader(model_path)
            if version:
                bundle.version = version
            if warmup_texts and self._warmup_runner is not None:
                self._warmup_runner(bundle, warmup_texts)
            self._swap_active(bundle)
            self._update_job(
                job_id,
                {
                    "state": "succeeded",
                    "updated_at": _utc_now(),
                    "active": self._bundle_summary(bundle),
                    "error": None,
                },
            )
            logger.info("reload succeeded for model_path=%s version=%s", model_path, bundle.version)
        except Exception as exc:
            logger.exception("reload failed for model_path=%s", model_path)
            self._update_job(
                job_id,
                {
                    "state": "failed",
                    "updated_at": _utc_now(),
                    "error": str(exc),
                },
            )
        finally:
            with self._state_lock:
                self._running_job_id = None

    def _update_job(self, job_id: str, patch: Dict[str, Any]) -> None:
        with self._state_lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.update(patch)
            while len(self._jobs) > self._max_jobs:
                oldest_key = next(iter(self._jobs.keys()))
                if oldest_key == self._running_job_id:
                    break
                self._jobs.pop(oldest_key, None)

    def _swap_active(self, bundle: ModelBundle) -> None:
        with self._state_lock:
            if self._active is not None:
                self._history.append(self._active)
            self._active = bundle

    def rollback(self) -> Dict[str, Any]:
        with self._state_lock:
            if self._running_job_id is not None:
                raise ReloadInProgressError(
                    f"cannot rollback while reload job is running: {self._running_job_id}"
                )
            if not self._history:
                raise RollbackNotAvailableError("no previous model available for rollback")

            current = self._active
            target = self._history.pop()
            self._active = target
            if current is not None:
                self._history.append(current)

            result = {
                "rolled_back_from": current.model_path if current else None,
                "active": self._bundle_summary(target),
                "history_size": len(self._history),
                "timestamp": _utc_now(),
            }
            logger.warning(
                "rollback completed: from=%s to=%s",
                result["rolled_back_from"],
                target.model_path,
            )
            return result

    def get_reload_job(self, job_id: str) -> Dict[str, Any]:
        with self._state_lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise ReloadJobNotFoundError(f"reload job not found: {job_id}")
            return copy.deepcopy(job)

    def get_status(self) -> Dict[str, Any]:
        with self._state_lock:
            return {
                "active": self._bundle_summary(self._active),
                "history_size": len(self._history),
                "reload_in_progress": self._running_job_id is not None,
                "running_job_id": self._running_job_id,
                "known_jobs": len(self._jobs),
                "timestamp": _utc_now(),
            }

    def predict(self, text: str) -> Dict[str, Any]:
        bundle = self._active
        if bundle is None:
            raise ModelNotReadyError("model is not loaded")
        return self._predictor(bundle, text)

    def get_active_bundle(self) -> ModelBundle:
        bundle = self._active
        if bundle is None:
            raise ModelNotReadyError("model is not loaded")
        return bundle

    @staticmethod
    def _bundle_summary(bundle: Optional[ModelBundle]) -> Optional[Dict[str, Any]]:
        if bundle is None:
            return None
        return {
            "model_path": bundle.model_path,
            "version": bundle.version,
            "loaded_at": bundle.loaded_at,
            "labels_count": len(bundle.id2label),
        }


def _create_default_manager() -> ModelManager:
    predictor = _predict_with_bundle
    warmup_runner = _default_warmup_runner(predictor)
    return ModelManager(
        model_loader=_default_model_loader,
        predictor=predictor,
        warmup_runner=warmup_runner,
        history_limit=MAX_HISTORY_MODELS,
        max_jobs=MAX_RELOAD_JOBS,
    )


def create_app(model_manager: Optional[ModelManager] = None) -> FastAPI:
    manager = model_manager or _create_default_manager()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if model_manager is None:
            if os.path.exists(DEFAULT_MODEL_PATH):
                try:
                    manager.initialize(DEFAULT_MODEL_PATH)
                except Exception as exc:
                    logger.exception("startup model loading failed")
                    if REQUIRE_MODEL_ON_STARTUP:
                        raise RuntimeError(f"failed to load startup model: {exc}") from exc
            elif REQUIRE_MODEL_ON_STARTUP:
                raise RuntimeError(f"startup model path not found: {DEFAULT_MODEL_PATH}")
            else:
                logger.warning(
                    "startup model path %s not found; service starts without model",
                    DEFAULT_MODEL_PATH,
                )
        yield

    app = FastAPI(
        title="Qwen3 Intent Classification API",
        description="Intent classification service with production-grade hot model reload and rollback",
        version="2.0.0",
        lifespan=lifespan,
    )
    app.state.model_manager = manager

    @app.exception_handler(ModelManagerError)
    async def model_manager_error_handler(request: Request, exc: ModelManagerError):
        logger.error("manager error on %s: %s", request.url.path, str(exc))
        status_code = 500
        if isinstance(exc, ModelNotReadyError):
            status_code = 503
        elif isinstance(exc, ReloadInProgressError):
            status_code = 409
        elif isinstance(exc, ReloadJobNotFoundError):
            status_code = 404
        elif isinstance(exc, RollbackNotAvailableError):
            status_code = 409
        return JSONResponse(
            status_code=status_code,
            content={"error": exc.__class__.__name__, "detail": str(exc)},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("unhandled exception on %s", request.url.path)
        return JSONResponse(
            status_code=500,
            content={"error": "InternalServerError", "detail": str(exc)},
        )

    @app.get("/")
    async def root():
        return {
            "message": "Qwen3 intent classification API",
            "version": "2.0.0",
            "docs": "/docs",
            "endpoints": {
                "predict": "POST /predict",
                "health": "GET /health",
                "intents": "GET /intents",
                "admin_status": "GET /admin/status",
                "admin_reload": "POST /admin/reload",
                "admin_reload_job": "GET /admin/reload/{job_id}",
                "admin_rollback": "POST /admin/rollback",
            },
        }

    @app.get("/health")
    async def health_check():
        status = app.state.model_manager.get_status()
        return {
            "status": "healthy" if status["active"] is not None else "degraded",
            "model_loaded": status["active"] is not None,
            "active_model": status["active"],
            "reload_in_progress": status["reload_in_progress"],
            "timestamp": status["timestamp"],
        }

    @app.get("/intents")
    async def get_available_intents():
        manager_ref = app.state.model_manager
        active = manager_ref.get_status()["active"]
        if active is None:
            raise ModelNotReadyError("model is not loaded")
        bundle = manager_ref.get_active_bundle()
        return {
            "intents": sorted(set(bundle.id2label.values())),
            "count": len(bundle.id2label),
            "model_version": bundle.version,
        }

    @app.post("/predict", response_model=IntentResponse)
    async def predict_intent(request: IntentRequest):
        text = request.text.strip()
        if not text:
            raise HTTPException(status_code=400, detail="input text must not be empty")

        result = app.state.model_manager.predict(text)
        return IntentResponse(**result)

    @app.get("/admin/status")
    async def admin_status():
        return app.state.model_manager.get_status()

    @app.post("/admin/reload", status_code=202)
    async def admin_reload(request: ReloadRequest):
        job_id = app.state.model_manager.submit_reload(
            model_path=request.model_path,
            version=request.version,
            warmup_texts=request.warmup_texts,
        )
        return {"job_id": job_id, "state": "running", "submitted_at": _utc_now()}

    @app.get("/admin/reload/{job_id}")
    async def admin_reload_job(job_id: str):
        return app.state.model_manager.get_reload_job(job_id)

    @app.post("/admin/rollback")
    async def admin_rollback():
        return app.state.model_manager.rollback()

    return app


app = create_app()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run intent classification API")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="listen host")
    parser.add_argument("--port", type=int, default=8000, help="listen port")
    parser.add_argument("--reload", action="store_true", help="code autoreload for local development")
    parser.add_argument("--log-level", type=str, default="info", help="uvicorn log level")
    args = parser.parse_args()

    import uvicorn

    uvicorn.run(
        "app:app" if args.reload else app,
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level,
    )


if __name__ == "__main__":
    main()
