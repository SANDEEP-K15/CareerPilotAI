from __future__ import annotations

from dataclasses import dataclass

from careerpilot.domain.entities.user import User
from careerpilot.ports.clock import ClockPort
from careerpilot.ports.ids import IdGeneratorPort
from careerpilot.ports.repositories import UserRepository


@dataclass(frozen=True, slots=True)
class RegisterUserCommand:
    display_name: str | None = None


class RegisterUserUseCase:
    def __init__(
        self,
        *,
        users: UserRepository,
        clock: ClockPort,
        ids: IdGeneratorPort,
    ) -> None:
        self._users = users
        self._clock = clock
        self._ids = ids

    async def execute(self, command: RegisterUserCommand) -> User:
        user = User.new(
            user_id=self._ids.new_id(),
            now=self._clock.now(),
            display_name=command.display_name,
        )
        await self._users.add(user)
        return user
