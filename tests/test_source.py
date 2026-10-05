# SPDX-License-Identifier: MIT

import json

import pytest

import harbourmaster
from harbourmaster import source as hm_source


@pytest.fixture
def pm_source(hm, ports_json_data, monkeypatch):
    """The default PortMaster source, updated from tests/data/ports.json."""
    fetched = []

    def fake_fetch_json(url):
        fetched.append(url)
        return json.loads(json.dumps(ports_json_data))

    monkeypatch.setattr(hm_source, "fetch_json", fake_fetch_json)

    source = hm.sources['pm']
    source.update()
    source.fetched = fetched
    return source


def test_default_sources(hm):
    assert sorted(hm.sources) == ['pm', 'pmmv']
    assert all(isinstance(source, hm_source.PortMasterV3) for source in hm.sources.values())
    assert hm.sources['pm'].name == "PortMaster"


def test_update_loads_ports(pm_source, ports_json_data):
    assert pm_source.fetched == [pm_source._config['url']]
    assert sorted(pm_source.ports) == sorted(ports_json_data['ports'])
    ## Runtimes are keyed by runtime_name, so each arch build adds the same name again.
    assert sorted(pm_source.utils) == [
        'ags_3.6.squashfs', 'ags_3.6.squashfs', 'dotnet-8.0.12.squashfs', 'gameinfo.zip', 'gmtoolkit.squashfs']

    info = pm_source.port_info("100LilJumps.zip")
    assert info['attr']['title'] == "100 Lil Jumps"
    assert pm_source.port_info("missing.zip") == {}

    expected = ports_json_data['ports']['100liljumps.zip']['source']
    assert pm_source.port_download_size("100liljumps.zip", check_runtime=False) == expected['size']
    assert pm_source.port_download_url("100liljumps.zip") == expected['url']


def test_update_registers_runtimes_per_arch(pm_source, hm):
    ags = hm.runtimes_info['ags_3.6.squashfs']

    assert ags['name'] == "Adventure Game Studio 3.6"
    assert sorted(ags['remote']) == ['aarch64', 'x86_64']


def test_update_saves_and_reloads(pm_source, make_hm, ports_json_data):
    ## A second HarbourMaster on the same dirs loads the cached source without fetching.
    hm2 = make_hm()
    assert sorted(hm2.sources['pm'].ports) == sorted(ports_json_data['ports'])


def test_runtime_size_added_to_download_size(pm_source, hm, ports_json_data):
    port = ports_json_data['ports']['sprout.zip']
    size = pm_source.port_download_size("sprout.zip", check_runtime=False)

    assert size == port['source']['size']
    assert pm_source.port_download_size("sprout.zip") > size


def test_download_unknown_port(pm_source, callback):
    assert pm_source.download("missing.zip") is None
    assert len(callback.message_boxes) == 1


def test_update_failure_keeps_going(hm, monkeypatch):
    monkeypatch.setattr(hm_source, "fetch_json", lambda url: None)

    source = hm.sources['pm']
    source.update()

    assert source.ports == []
