from .models import DBUser, DBProject, OAuthProvider
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


def find_oauth_provider_by_name(session: Session, provider_name: str) -> list[OAuthProvider]:
    """

    :param session:
    :param provider_name:
    :return:
    """
    return session.query(OAuthProvider).filter_by(name=provider_name).all()


def add_provider(session: Session, 
                name: str,
                client_id: str, 
                client_secret: str,
                authorize_url: str,
                token_url: str,
                user_info_url: str,
                scope: str,
                commit: bool = False) -> OAuthProvider:
    """
    Add a new OAuth provider to the database.
    
    :param session: a db Session
    :param name: str, unique name for the OAuth provider
    :param client_id: str, OAuth client ID from the provider
    :param client_secret: str, OAuth client secret from the provider  
    :param authorize_url: str, OAuth authorization endpoint URL
    :param token_url: str, OAuth token endpoint URL
    :param user_info_url: str, URL to get user information from provider
    :param scope: str, OAuth scope permissions
    :return: OAuthProvider object that was created
    :raise ValueError: if provider with the same name already exists
    """
    # Check if provider already exists
    existing_providers = find_oauth_provider_by_name(session, name)
    if existing_providers:
        raise ValueError(f"OAuth provider with name '{name}' already exists")
    
    # Create new provider
    new_provider = OAuthProvider(
        name=name,
        client_id=client_id,
        client_secret=client_secret,
        authorize_url=authorize_url,
        token_url=token_url,
        user_info_url=user_info_url,
        scope=scope
    )
    
    # Add to session and commit
    session.add(new_provider)
    if commit:
        session.commit()
        session.refresh(new_provider)
    
    return new_provider


def update_provider(session: Session,
                   name: str,
                   client_id: str = None,
                   client_secret: str = None,
                   authorize_url: str = None,
                   token_url: str = None,
                   user_info_url: str = None,
                   scope: str = None,
                   commit: bool = False) -> OAuthProvider:
    """
    Update an existing OAuth provider in the database.
    
    :param session: a db Session
    :param name: str, name of the OAuth provider to update
    :param client_id: str, optional new OAuth client ID
    :param client_secret: str, optional new OAuth client secret
    :param authorize_url: str, optional new OAuth authorization endpoint URL
    :param token_url: str, optional new OAuth token endpoint URL
    :param user_info_url: str, optional new URL to get user information
    :param scope: str, optional new OAuth scope permissions
    :return: OAuthProvider object that was updated
    :raise KeyError: if provider with the given name doesn't exist
    """
    providers = find_oauth_provider_by_name(session, name)
    if not providers:
        raise KeyError(f"OAuth provider with name '{name}' not found")
    
    provider = providers[0]
    
    # Update only the fields that are provided
    if client_id is not None:
        provider.client_id = client_id
    if client_secret is not None:
        provider.client_secret = client_secret
    if authorize_url is not None:
        provider.authorize_url = authorize_url
    if token_url is not None:
        provider.token_url = token_url
    if user_info_url is not None:
        provider.user_info_url = user_info_url
    if scope is not None:
        provider.scope = scope

    if commit:
        session.commit()
        session.refresh(provider)
    
    return provider
