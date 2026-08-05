"""User repository."""

from sqlalchemy import func, select

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(func.lower(User.email) == email.lower())
        return await self.db.scalar(stmt)

    async def get_by_reset_token(self, token: str) -> User | None:
        stmt = select(User).where(User.reset_token == token)
        return await self.db.scalar(stmt)
