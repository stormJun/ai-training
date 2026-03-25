"""Start both subagent services, run the host agent, then stop everything."""

from __future__ import annotations

import argparse
import threading
import time

import httpx
import uvicorn

from .apps.analysis_service import app as analysis_app
from .apps.stock_service import app as stock_app
from .host_agent import run_host_agent


def start_server(app, host: str, port: int) -> tuple[uvicorn.Server, threading.Thread]:
    """Start a uvicorn server in a background thread."""

    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    return server, thread


def wait_for_health(url: str, timeout: float = 5.0) -> None:
    """Wait until a health endpoint becomes available."""

    deadline = time.time() + timeout
    with httpx.Client(timeout=1.0) as client:
        while time.time() < deadline:
            try:
                response = client.get(url)
                if response.status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            time.sleep(0.1)
    raise RuntimeError(f"Service {url} did not become healthy in time.")


def main() -> None:
    """CLI entry point."""

    parser = argparse.ArgumentParser(description="Run the full master/subagent demo.")
    parser.add_argument("--query", required=True, help="Question to send to the host agent.")
    args = parser.parse_args()

    stock_server, stock_thread = start_server(stock_app, "127.0.0.1", 8011)
    analysis_server, analysis_thread = start_server(analysis_app, "127.0.0.1", 8012)

    try:
        wait_for_health("http://127.0.0.1:8011/health")
        wait_for_health("http://127.0.0.1:8012/health")
        print(run_host_agent(args.query, mode="remote"))
    finally:
        stock_server.should_exit = True
        analysis_server.should_exit = True
        stock_thread.join(timeout=5)
        analysis_thread.join(timeout=5)


if __name__ == "__main__":
    main()
