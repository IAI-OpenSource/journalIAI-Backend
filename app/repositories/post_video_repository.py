from sqlalchemy.ext.asyncio import AsyncSession


class VideoUploadRepository:

    def __init__(self, bd_session : AsyncSession):
        self.bd_session = bd_session

    async def save_post_video(self):
        pass
