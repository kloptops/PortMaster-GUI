# SPDX-License-Identifier: MIT

import pytest

import harbourmaster
from harbourmaster import hardware


def test_device_info_from_environment():
    info = harbourmaster.device_info()

    assert info['name'] == "default"
    assert info['device'] == "testing"
    assert info['model'] == "Testing"
    assert info['resolution'] == (640, 480)
    assert info['primary_arch'] == "aarch64"
    assert info['capabilities'] == ["aarch64", "640x480", "power", "opengl"]
    assert info['ram'] == 1024
    assert info['glibc'] == "2.30"
    assert info['analogsticks'] == 2


def test_device_info_is_cached(monkeypatch):
    first = harbourmaster.device_info()
    monkeypatch.setenv("DISPLAY_WIDTH", "1280")
    assert harbourmaster.device_info() is first


def test_device_info_defaults(monkeypatch):
    for key in ("DISPLAY_WIDTH", "DISPLAY_HEIGHT", "DEVICE_RAM", "CFW_GLIBC", "DEVICE_CAPABILITIES"):
        monkeypatch.delenv(key)

    info = harbourmaster.device_info()

    assert info['resolution'] == (640, 480)
    assert info['ram'] == 1024
    assert info['glibc'] == "0.0.0"
    assert info['capabilities'] == []


def test_device_info_from_env_file(tmp_path, monkeypatch):
    for key in ("DEVICE_NAME", "DEVICE_CPU", "CFW_NAME"):
        monkeypatch.delenv(key)

    for key in ("DISPLAY_WIDTH", "DISPLAY_HEIGHT", "DEVICE_ARCH", "DEVICE_CAPABILITIES"):
        monkeypatch.delenv(key)

    (tmp_path / "device_info_muos_rg35xx.env").write_text(
        "# comment\n"
        "DEVICE_NAME='RG35XX'\n"
        "CFW_NAME=\"muOS\"\n"
        "DISPLAY_WIDTH=640\n"
        "DISPLAY_HEIGHT=480\n"
        "DEVICE_ARCH=armhf\n"
        "DEVICE_CAPABILITIES=armhf 640x480\n"
        "padding_to_get_past_the_size_check=xxxxxxxxxxxxxxxx\n")

    info = hardware.HardwareDetector(tmp_path).get_info()

    assert info['name'] == "muos"
    assert info['model'] == "RG35XX"
    assert info['primary_arch'] == "armhf"
    assert info['capabilities'] == ["armhf", "640x480"]


def test_read_env_file(tmp_path):
    env_file = tmp_path / "test.env"
    env_file.write_text("A=1\n# skip=me\n\nNo equals here\nB = 'two' \nC=x=y\n")

    assert hardware._read_env_file(env_file) == {'a': '1', 'b': 'two', 'c': 'x=y'}
    assert hardware._read_env_file(tmp_path / "missing.env") == {}


@pytest.mark.parametrize("raw, expected", [
    ("2.30", "2.30"),
    ("231", "2.31"),
    ("", "0.0.0"),
    ("unknown", "0.0.0"),
    ("0", "0.0.0"),
    ])
def test_normalize_glibc(raw, expected):
    assert hardware._normalize_glibc(raw) == expected


def test_expand_info_override_resolution():
    info = harbourmaster.expand_info({'name': 'x'}, override_resolution=(1280, 720))

    assert info['name'] == 'x'
    assert info['resolution'] == (1280, 720)
    assert "1280x720" in info['capabilities']
    assert "640x480" not in info['capabilities']
    assert "aarch64" in info['capabilities']


def test_find_device_by_resolution():
    assert harbourmaster.find_device_by_resolution((640, 480)) == "testing"
    assert harbourmaster.find_device_by_resolution((1, 1)) == "default"
