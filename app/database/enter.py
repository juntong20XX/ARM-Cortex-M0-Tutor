"""
read setting and setup database session
"""
from app.core.settings import load_config, AppSetting
from . import models
from .dbtools import ensure_default_groups

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

from contextlib import contextmanager


# Important variables, used in db functions.
_engine = None
_SessionLocal = None


def init_database(app_setting: None | AppSetting = None):
    """
    load database
    :param app_setting: None -> setting.load_config
    :return:
    """
    if app_setting is None:
        app_setting = load_config()
    return _init_database_from_url(app_setting.database_url)



def _init_database_from_url(url: str):
    global _engine, _SessionLocal

    _engine = create_engine(url)
    # do something for different db
    if url.lower().startswith("sqlite"):
        # SQLite 启用外键约束
        @event.listens_for(_engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    # Create SessionLocal.
    _SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=_engine
    )


def get_db() -> Session:
    """
    get db session
    :return: Session
    """
    if _SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")

    db = _SessionLocal()
    # 创建表
    models.DBBase.metadata.create_all(bind=_engine)
    ensure_default_groups(db)
    db.flush()  # 使 ensure_default_groups 添加的组对同 session 内后续查询可见
    return db


@contextmanager
def db_context():
    """
    use `with` to get db session, with auto commit and rollback
    :return: Session
    :raise RuntimeError: when an Exception caught.
    """
    db = get_db()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

__all__ = ["get_db", "db_context", "init_database"]