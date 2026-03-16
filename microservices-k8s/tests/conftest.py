import os
import subprocess
import time
from pathlib import Path

import httpx
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TIMEOUT_SECONDS = float(os.getenv("WAIT_TIMEOUT_SECONDS", "90"))
DEFAULT_POLL_INTERVAL_SECONDS = float(os.getenv("WAIT_POLL_INTERVAL_SECONDS", "1"))


@pytest.fixture(scope="session")
def base_url() -> str:
    return os.getenv("BASE_URL", "http://localhost:8080/api")


@pytest.fixture(scope="session")
def orchestrator() -> str:
    return os.getenv("ORCHESTRATOR", "compose")


@pytest.fixture(scope="session")
def project_root() -> Path:
    return PROJECT_ROOT


def wait_for_url(url: str, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> None:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            response = httpx.get(url, timeout=3)
            if response.status_code < 500:
                return
        except httpx.HTTPError as exc:
            last_error = exc
        time.sleep(DEFAULT_POLL_INTERVAL_SECONDS)
    raise RuntimeError(f"Timed out waiting for {url}: {last_error}")


def run_service_action(orchestrator: str, action: str, service_name: str) -> None:
    if orchestrator == "compose":
        subprocess.run(
            ["docker", "compose", action, service_name],
            cwd=PROJECT_ROOT,
            check=True,
        )
        return

    if orchestrator == "k8s":
        replicas = "0" if action == "stop" else "1"
        subprocess.run(
            ["kubectl", "scale", f"deployment/{service_name}", f"--replicas={replicas}"],
            check=True,
        )
        return

    raise ValueError(f"Unsupported orchestrator: {orchestrator}")


@pytest.fixture(scope="session", autouse=True)
def wait_for_gateway(base_url: str):
    wait_for_url(f"{base_url}/menu")
