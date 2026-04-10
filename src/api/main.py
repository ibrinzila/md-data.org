import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.status import router as status_router
from src.api.v1.router import api_router
from src.db.session import init_db

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logging.info("md-data.org API started")
    yield


app = FastAPI(title="md-data.org API", version="1.0.0", docs_url="/docs", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(status_router)
app.include_router(api_router, prefix="/v1")


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Welcome to md-data.org - Moldova Public Data API"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
