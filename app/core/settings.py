"""

"""
from app.core.defender import logger

import os
import tomllib
from enum import Enum
from dataclasses import dataclass


class LoginAction(str, Enum):
    """
    Login action chooses.
    :arg username_domain: User input username, automatically determines the login method and OAuth domain.
    :arg oauth: User can choose OAuth Provider.
    :arg password: username and password login
    :arg oauth_pw: OAuth list and password login
    :arg direct_oauth: Redirect to OAuth page directly, only works when just 1 OAuth Provider.
    """
    username_domain = "username_domain"
    oauth = "oauth"
    password = "password"
    oauth_pw = "oauth_pw"
    direct_oauth = "direct_oauth"


@dataclass(frozen=True)
class AppSetting:
    database_url: str
    secret_key: str  # for gen session token
    login_action: LoginAction = LoginAction.oauth_pw


def _load_config_from_file(path="./config.toml") -> dict:
    try:
        with open(path, "b") as fp:
            return tomllib.load(fp)
    except (FileNotFoundError, IsADirectoryError, PermissionError) as err:
        logger.error("Error occurred when load config file", path, err)
        return {}


def _load_config_from_env(env=None) -> dict:
    # 说实话想不到这里能报什么错.
    if env is None:
        env = os.environ
    ret = {}
    for key in ("database_url",):
        val = env.get(key, None)
        if val:
            ret[key] = val
    return ret

def load_config() -> AppSetting:
    """
    load config from
    :return:
    """
    ret = {}
    ret.update(_load_config_from_file())
    ret.update(_load_config_from_env())
    return AppSetting(**ret)