from sqlalchemy.ext.asyncio import AsyncSession


class LikeRepository:
    def __init__(self, bd: AsyncSession):
        self._bd = bd


