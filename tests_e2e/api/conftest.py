import pytest
import httpx
from conftest import BASE_URL


@pytest.fixture(scope="session", autouse=True)
def require_stack():
    """Skip all API tests if the stack is unreachable."""
    try:
        httpx.get(f"{BASE_URL}/health", timeout=3.0)
    except (httpx.ConnectError, httpx.TimeoutException):
        pytest.skip(
            f"Stack not reachable at {BASE_URL}. "
            "Start locally with 'docker compose up' or set E2E_BASE_URL=https://secure.wowmyspace.com",
            allow_module_level=True,
        )
