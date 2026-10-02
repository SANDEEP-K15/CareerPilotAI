from __future__ import annotations

import hmac
from typing import Annotated

from fastapi import Header, Request

from careerpilot.application.errors import ApplicationError
from careerpilot.config.settings import ClientApiSettings


class ClientAuthenticationError(ApplicationError):
    def __init__(self) -> None:
        super().__init__("Client API authentication failed.", code="unauthorized")


def _extract_bearer_token(authorization: str | None) -> str | None:
    if authorization is None:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


async def require_client_api_token(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    settings: ClientApiSettings | None = getattr(request.app.state, "client_api_settings", None)
    if settings is None or settings.api_token is None:
        raise ClientAuthenticationError()
    expected = settings.api_token.get_secret_value()
    if not expected:
        raise ClientAuthenticationError()
    provided = _extract_bearer_token(authorization)
    if provided is None or not hmac.compare_digest(provided, expected):
        raise ClientAuthenticationError()
