from .models import DBUser, DBProject
from .enter import db_context

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker, DeclarativeBase


def find_project_by_name(session: Session, project_name: str) -> list[DBProject]:
    """
    Found user sequence with project name, the name need be full-matched.
    :param session: a db Session
    :param project_name: str, the project name.
    :return:
    """
    return session.query(DBProject).filter_by(name=project_name).all()


def find_project_by_owner_name(session: Session, owner_name: str) -> list[DBProject]:
    """
    Found user sequence with project's owner's name, the name need be full-matched.
    :param session: a db Session
    :param owner_name: str, the project owner's name.
    :raise KeyError: the user for `owner_name` not found
    :return:
    """
    users = find_user_by_username(session, owner_name)
    try:
        user = users[0]
    except IndexError:
        raise KeyError(f"the user for `{owner_name}` not found")
    return find_project_by_owner_id(session, user.uuid)


def find_project_by_owner_id(session: Session, owner_id: str) -> list[DBProject]:
    """
    Found user sequence with owner id (user.uuid), the id need be full-matched.
    :param session: a db Session
    :param owner_id: str, user.uuid.
    :return:
    """
    return session.query(DBProject).filter_by(owner_id=owner_id).all()



def find_user_by_email_host(session: Session, email_host: str) -> list[DBUser]:
    """
    Found user sequence with the host of email, like `@outlook.com` or `liv.ac.uk`.
    :param session: a db Session
    :param email_host: str, with `@` or not.
    :return:
    """
    endswith = email_host if email_host.startswith("@") else f'@{email_host}'
    query = select(DBUser).where(DBUser.email.endswith(endswith))
    return session.execute(query).scalars().all()


def find_user_by_username(session: Session, username: str) -> list[DBUser]:
    """
    Found user sequence with username, the username need be full-matched.
    :param session: a db Session
    :param username: str, the username.
    :return:
    """
    return session.query(DBUser).filter_by(username=username).all()
