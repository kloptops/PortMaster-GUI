# SPDX-License-Identifier: MIT
#
# harbourmaster.config resolves its directories at import time, so these run in
# a fresh interpreter each time.

import json
import os
import subprocess
import sys

from conftest import EXLIB_PATH, PYLIB_PATH


SCRIPT = f"""
import builtins, json, sys
sys.path.insert(0, {str(EXLIB_PATH)!r})
sys.path.insert(0, {str(PYLIB_PATH)!r})
builtins.PYLIB_PATH = {str(PYLIB_PATH)!r}
builtins.PORTMASTER_DEBUG = False
from loguru import logger
logger.remove()
from harbourmaster import config
print(json.dumps({{
    'tools': str(config.HM_TOOLS_DIR),
    'ports': str(config.HM_PORTS_DIR),
    'scripts': str(config.HM_SCRIPTS_DIR),
    'testing': config.HM_TESTING,
    }}))
"""


def run_config(cwd, **env):
    run_env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("HM_")}

    run_env.update(env)

    output = subprocess.check_output([sys.executable, "-c", SCRIPT], cwd=str(cwd), env=run_env)
    return json.loads(output.decode().strip().split("\n")[-1])


def test_env_overrides(tmp_path):
    result = run_config(
        tmp_path,
        HM_TOOLS_DIR=str(tmp_path / "tools"),
        HM_PORTS_DIR=str(tmp_path / "ports"),
        HM_SCRIPTS_DIR=str(tmp_path / "scripts"))

    assert result['tools'] == str(tmp_path / "tools")
    assert result['ports'] == str((tmp_path / "ports").resolve())
    assert result['scripts'] == str(tmp_path / "scripts")
    assert result['testing'] is False


def test_git_checkout_is_testing_mode(tmp_path):
    (tmp_path / ".git").mkdir()

    result = run_config(tmp_path)

    assert result['testing'] is True
    assert result['tools'] == str(tmp_path)
    assert result['ports'] == str(tmp_path / "ports")
    assert result['scripts'] == str(tmp_path / "ports")


def test_git_checkout_from_subdir_is_testing_mode(tmp_path):
    ## Running from PortMaster/ inside a checkout chdirs up a level.
    (tmp_path / ".git").mkdir()
    (tmp_path / "PortMaster").mkdir()

    result = run_config(tmp_path / "PortMaster")

    assert result['testing'] is True
    assert result['tools'] == str(tmp_path)
