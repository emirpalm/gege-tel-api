import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/gegetel.db")


class Base(DeclarativeBase):
    pass


def make_engine(url: str = DATABASE_URL, **kwargs):
    return create_engine(url, connect_args={"check_same_thread": False}, **kwargs)


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
