from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.base import engine

# Creation d'une session qui va permettre d'interagir avec la db
AsyncSessionLocal = async_sessionmaker(
    engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False  # garde les objets utilisables après commit
)


# Function get_db qui permet d'acceder/ouvrrir une session avec la db

async def get_db():
    """Ouvre une session avec la db et attend la fin de toutes operations engagées"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise