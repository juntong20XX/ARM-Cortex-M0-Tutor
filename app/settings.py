"""

"""
from .defender import retry, stop_after_attempt, wait_fixed, logger

import os
import tomllib
from pathlib import Path
from dataclasses import dataclass


@dataclass(frozen=True)
class AppSetting:
    database_url: str


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