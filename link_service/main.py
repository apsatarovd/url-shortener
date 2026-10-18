from contextlib import asynccontextmanager
from fastapi import FastAPI
from link_service.database import engine, Base
from link_service.models import Link
from link_service.routers.link_router import router as link_router
from link_service.routers.stats_router import router as stats_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(title="URL Shortener", lifespan=lifespan)

app.include_router(link_router)
app.include_router(stats_router, prefix="/api", tags=["Statistics"])
@app.get("/")
async def root():
    return {"message": "URL Shortener API is running"}