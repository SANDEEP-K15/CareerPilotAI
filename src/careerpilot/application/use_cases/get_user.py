from __future__ import annotations

from uuid import UUID

from careerpilot.application.errors import UserNotFoundError
from careerpilot.domain.entities.user import User
from careerpilot.ports.repositories import UserRepository


class GetUserUseCase:
    def __init__(self, *, users: UserRepository) -> None:
        self._users = users

    async def execute(self, user_id: UUID) -> User:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(str(user_id))
        return user
