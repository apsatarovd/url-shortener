from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://Dastan:postgres@localhost:5432/shortener"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

engine = create_async_engine(settings.DATABASE_URL, echo=True)
Base = declarative_base()

async_session = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db():
    async with async_session() as session:
        yield session