import asyncio
import logging
import os

from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from src.db.models import Base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./mddata.db")

engine_kwargs: dict[str, object] = {"future": True, "pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)


def create_schema() -> None:
    Base.metadata.create_all(bind=engine)


async def init_db(retries: int = 5, delay: float = 1.0) -> None:
    for attempt in range(1, retries + 1):
        try:
            create_schema()
            return
        except OperationalError as exc:
            logging.warning("Database not ready on attempt %s/%s: %s", attempt, retries, exc)
            if attempt == retries:
                logging.warning("Continuing without persistent database initialization.")
                return
            await asyncio.sleep(delay)
        except Exception as exc:
            logging.exception("Database initialization failed: %s", exc)
            return
