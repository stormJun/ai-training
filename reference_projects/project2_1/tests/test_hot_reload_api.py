"""Tests for production-grade hot model reload and rollback behavior."""

from __future__ import annotations

import importlib.util
import asyncio
import sys
import threading
import time
import uuid
from pathlib import Path

import pytest


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def load_app_module():
    """Load the app module from file so tests are isolated from global import state."""
    module_name = f"project2_1_app_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, APP_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def wait_job_done(manager, job_id: str, timeout: float = 5.0):
    """Poll reload job status until terminal state."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = manager.get_reload_job(job_id)
        if status["state"] in {"succeeded", "failed"}:
            return status
        time.sleep(0.05)
    raise AssertionError(f"job {job_id} did not finish within timeout")


def get_route_endpoint(app, path: str, method: str):
    """Find route endpoint function by path and method."""
    for route in app.routes:
        if getattr(route, "path", None) == path and method.upper() in getattr(route, "methods", set()):
            return route.endpoint
    raise AssertionError(f"route not found: {method} {path}")


def test_model_manager_rejects_concurrent_reload():
    module = load_app_module()
    assert hasattr(module, "ModelManager")
    assert hasattr(module, "ReloadInProgressError")

    load_gate = threading.Event()

    def fake_loader(model_path: str):
        if model_path == "v2":
            load_gate.wait(timeout=3.0)
        return module.ModelBundle(
            model=object(),
            tokenizer=object(),
            id2label={"0": "ticket_refund"},
            model_path=model_path,
            version=model_path,
            loaded_at=time.time(),
        )

    manager = module.ModelManager(model_loader=fake_loader)
    manager.initialize("v1")

    first_job = manager.submit_reload("v2")
    with pytest.raises(module.ReloadInProgressError):
        manager.submit_reload("v3")

    load_gate.set()
    first_status = wait_job_done(manager, first_job)
    assert first_status["state"] == "succeeded"
    assert manager.get_status()["active"]["model_path"] == "v2"


def test_model_manager_rollback_to_previous_version():
    module = load_app_module()
    assert hasattr(module, "ModelManager")

    def fake_loader(model_path: str):
        return module.ModelBundle(
            model=object(),
            tokenizer=object(),
            id2label={"0": "ticket_refund"},
            model_path=model_path,
            version=model_path,
            loaded_at=time.time(),
        )

    manager = module.ModelManager(model_loader=fake_loader)
    manager.initialize("v1")
    reload_job = manager.submit_reload("v2")
    reload_status = wait_job_done(manager, reload_job)
    assert reload_status["state"] == "succeeded"
    assert manager.get_status()["active"]["model_path"] == "v2"

    rollback_info = manager.rollback()
    assert rollback_info["active"]["model_path"] == "v1"
    assert rollback_info["rolled_back_from"] == "v2"


def test_admin_reload_and_rollback_endpoints():
    module = load_app_module()
    assert hasattr(module, "create_app")

    class FakeManager:
        def __init__(self):
            self.reload_calls = []
            self.rollback_calls = 0

        def submit_reload(self, model_path: str, version=None, warmup_texts=None):
            self.reload_calls.append(
                {"model_path": model_path, "version": version, "warmup_texts": warmup_texts}
            )
            return "job-1"

        def rollback(self):
            self.rollback_calls += 1
            return {
                "rolled_back_from": "v2",
                "active": {"model_path": "v1", "version": "v1"},
                "history_size": 1,
            }

        def get_reload_job(self, job_id: str):
            return {"job_id": job_id, "state": "succeeded"}

        def get_status(self):
            return {"active": {"model_path": "v1", "version": "v1"}, "history_size": 0}

        def predict(self, text: str):
            return {
                "text": text,
                "intent": "ticket_refund",
                "confidence": 0.9,
                "model_version": "v1",
                "model_path": "v1",
            }

    fake_manager = FakeManager()
    test_app = module.create_app(model_manager=fake_manager)
    reload_handler = get_route_endpoint(test_app, "/admin/reload", "POST")
    rollback_handler = get_route_endpoint(test_app, "/admin/rollback", "POST")

    reload_req = module.ReloadRequest(
        model_path="v2",
        version="v2",
        warmup_texts=["我要退票"],
    )
    reload_resp = asyncio.run(reload_handler(reload_req))
    assert reload_resp["job_id"] == "job-1"
    assert fake_manager.reload_calls[0]["model_path"] == "v2"

    rollback_resp = asyncio.run(rollback_handler())
    assert rollback_resp["active"]["model_path"] == "v1"
    assert fake_manager.rollback_calls == 1
