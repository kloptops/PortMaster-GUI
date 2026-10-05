# SPDX-License-Identifier: MIT
#
# Starts pugwash headless in fifo_control mode and drives it the same way
# PortMaster/PortMasterDialog.txt does:
#
#   printf "WAIT" > $PM_DONE
#   echo $(printf "%s\1" "$@") > $PM_PIPE
#   wait until $PM_DONE != WAIT

import json
import os
import subprocess
import sys
import time

import pytest

from conftest import PM_DIR, REPO_DIR, basic_port_files, write_port_zip


pytestmark = pytest.mark.sdl

TIMEOUT = 30


class FifoGui:
    def __init__(self, process, pipe_file, done_file):
        self.process = process
        self.pipe_file = pipe_file
        self.done_file = done_file

    def wait_done(self):
        end = time.monotonic() + TIMEOUT
        while time.monotonic() < end:
            if self.process.poll() is not None:
                raise AssertionError(f"pugwash exited early:\n{self.process.stdout.read().decode()}")

            if self.done_file.is_file() and self.pipe_file.exists():
                result = self.done_file.read_text()
                if result not in ("", "WAIT"):
                    return result

            time.sleep(0.05)

        raise AssertionError("timed out waiting for pugwash")

    def send(self, *args):
        self.done_file.write_text("WAIT")

        with open(str(self.pipe_file), "w") as fh:
            fh.write("".join(f"{arg}\1" for arg in args) + "\n")

        return self.wait_done()

    def exit(self):
        with open(str(self.pipe_file), "w") as fh:
            fh.write("exit\n")

        try:
            result = self.process.wait(TIMEOUT)
            output = self.process.stdout.read().decode()

        finally:
            self.process.stdout.close()

        ## main() is wrapped in logger.catch, so a crash still exits with 0.
        assert "Traceback" not in output, output
        return result


@pytest.fixture(params=["device", "git-checkout"])
def fifo_gui(request, hm_dirs, tmp_path):
    """
    "device" runs from a plain directory, "git-checkout" runs from the repo so
    harbourmaster switches to HM_TESTING mode, like a developer running it.
    """
    cwd = tmp_path if request.param == "device" else REPO_DIR

    env = dict(os.environ)
    env.update({
        'HM_TOOLS_DIR': str(hm_dirs['tools_dir']),
        'HM_PORTS_DIR': str(hm_dirs['ports_dir']),
        'HM_SCRIPTS_DIR': str(hm_dirs['scripts_dir']),
        })

    pipe_file = tmp_path / "pm_pipe"
    done_file = tmp_path / "pm_done"
    done_file.write_text("WAIT")

    process = subprocess.Popen(
        [sys.executable, str(PM_DIR / "pugwash"), "--offline", "--no-check", "--no-log",
            "fifo_control", str(pipe_file), str(done_file)],
        cwd=str(cwd), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    gui = FifoGui(process, pipe_file, done_file)

    try:
        ## pugwash writes DONE once the pipe is ready.
        assert gui.wait_done() == "DONE"
        yield gui

    finally:
        if process.poll() is None:
            process.kill()
            process.wait()


def test_messages_and_progress(fifo_gui):
    assert fifo_gui.send("messages_begin") == "DONE"
    assert fifo_gui.send("message", "Hello from the tests") == "DONE"
    assert fifo_gui.send("progress", "Working", "50", "100") == "DONE"
    assert fifo_gui.send("progress_clear") == "DONE"
    assert fifo_gui.send("messages_end") == "DONE"

    assert fifo_gui.exit() == 0


def test_bad_commands(fifo_gui):
    ## Ending messages that were never started fails.
    assert fifo_gui.send("messages_end") == "FAIL"
    assert fifo_gui.send("message") == "FAIL"
    assert fifo_gui.send("not_a_command") == "DONE"

    assert fifo_gui.exit() == 0


def test_register(fifo_gui):
    assert fifo_gui.send("register_set_info", "ports", "game", "title:Game", "size:10") == "DONE"
    assert json.loads(fifo_gui.send("register_dump", "ports")) == {"game": {"title": "Game", "size": "10"}}
    assert fifo_gui.send("register_clear", "ports") == "DONE"
    assert fifo_gui.send("register_dump", "ports") == "FAIL"

    assert fifo_gui.exit() == 0


def test_install_local_zip(fifo_gui, hm_dirs, tmp_path):
    ## Runs HarbourMaster.install_port on pugwash's worker thread.
    zip_file = write_port_zip(tmp_path / "testport.zip", basic_port_files())

    assert fifo_gui.send("messages_begin") == "DONE"
    assert fifo_gui.send("install", str(zip_file)) == "OKAY"
    assert fifo_gui.send("messages_end") == "DONE"

    assert (hm_dirs['ports_dir'] / "Test Port.sh").is_file()
    assert (hm_dirs['ports_dir'] / "testport" / "port.json").is_file()

    assert fifo_gui.exit() == 0


def test_install_bad_zip_fails(fifo_gui, tmp_path):
    zip_file = write_port_zip(tmp_path / "bad.zip", {"Bad.sh": "#!/bin/bash\n"})

    assert fifo_gui.send("install", str(zip_file)) == "FAIL"
    assert fifo_gui.exit() == 0
