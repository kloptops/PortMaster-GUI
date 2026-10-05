# SPDX-License-Identifier: MIT

import pytest

from conftest import PYLIB_PATH


pytestmark = pytest.mark.sdl


@pytest.fixture(scope="module")
def pugtheme():
    import pugtheme
    return pugtheme


@pytest.mark.parametrize("text, expected", [
    ("element", ("element", [])),
    ("element[opengl]", ("element", ["opengl"])),
    ("element[opengl, !power]", ("element", ["opengl", "!power"])),
    ("element[a][b]", ("element_bad", [])),
    ("element[a", ("element_bad", [])),
    ])
def test_extract_requirements(pugtheme, text, expected):
    assert pugtheme.extract_requirements(text) == expected


def test_extract_requirements_strict(pugtheme):
    assert pugtheme.extract_requirements("element", strict=True) == ("element", None)


def test_theme_update_applies_requirements(pugtheme):
    ## Test device capabilities are "aarch64 640x480 power opengl".
    source = {
        "font": "base",
        "font[640x480]": "small",
        "font[1280x720]": "large",
        "colour[!opengl]": "never",
        "nested": {"a": 1, "list": [1, 2]},
        }

    result = pugtheme.theme_update({"nested": {"b": 2}}, source)

    assert result == {
        "font": "small",
        "nested": {"a": 1, "b": 2, "list": [1, 2]},
        }

    ## Lists are copied, not shared.
    assert result["nested"]["list"] is not source["nested"]["list"]


def test_theme_merge_does_not_modify_inputs(pugtheme):
    target = {"a": {"x": 1}}
    source = {"a": {"y": 2}}

    assert pugtheme.theme_merge(target, source) == {"a": {"x": 1, "y": 2}}
    assert target == {"a": {"x": 1}}


def test_default_theme(pugtheme):
    theme = pugtheme.Theme(PYLIB_PATH / "default_theme")

    assert theme.name != ""
    assert isinstance(theme.schemes, list)
    for scene in ("main_menu", "option_menu", "ports_list"):
        assert scene in theme.theme_data, scene


def test_missing_theme(pugtheme, tmp_path):
    with pytest.raises(ValueError):
        pugtheme.Theme(tmp_path)
