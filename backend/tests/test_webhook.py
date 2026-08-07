import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_webhook_unauthorized_signature() -> None:
    """
    Test that a webhook request without a valid signature is rejected.
    """
    # TODO: Perform POST /api/v1/webhook request with bad/missing signature headers
    # TODO: Verify status code is 401/403/422 as designed
    pass


def test_webhook_successful_payload() -> None:
    """
    Test that a valid webhook payload is successfully processed.
    """
    # TODO: Mock signature validation
    # TODO: Send a standard webhook payload mock
    # TODO: Verify response status code is 202
    pass
