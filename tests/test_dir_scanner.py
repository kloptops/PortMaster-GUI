# SPDX-License-Identifier: MIT
#
# DirectoryScanner works out installed port sizes a few steps per frame.

import pytest


pytestmark = pytest.mark.sdl


@pytest.fixture
def tree(tmp_path):
    root = tmp_path / "port"
    (root / "a" / "b").mkdir(parents=True)
    (root / "c").mkdir()
    (root / "one.bin").write_bytes(b"x" * 100)
    (root / "a" / "two.bin").write_bytes(b"x" * 200)
    (root / "a" / "b" / "three.bin").write_bytes(b"x" * 300)
    (root / "c" / "four.bin").write_bytes(b"x" * 400)
    return root


def run_scanner(scanner, max_iterations=100):
    for _ in range(max_iterations):
        if not scanner.scans:
            return

        scanner.iterate(1)

    raise AssertionError("scanner never finished")


def test_scan_directory_total(pugwash, tree):
    scanner = pugwash.DirectoryScanner()
    results = []
    scanner.callback = lambda scan_dir, size, is_final: results.append((scan_dir, size, is_final))

    ## First call starts the scan.
    assert scanner.check_directory(tree, False) is None
    assert scanner.check_directory(tree) == "~ 0 B"

    run_scanner(scanner)

    assert scanner.check_directory(tree, False) == 1000
    assert scanner.check_directory(tree) == "0.98 KB"

    ## Progress is reported with growing totals, then a final result.
    sizes = [size for _, size, _ in results]
    assert sizes == sorted(sizes)
    assert results[-1] == (tree, 1000, True)


def test_scan_multiple_directories(pugwash, tree):
    scanner = pugwash.DirectoryScanner()

    scanner.check_directory(tree / "a", False)
    scanner.check_directory(tree / "c", False)
    run_scanner(scanner)

    assert scanner.check_directory(tree / "a", False) == 500
    assert scanner.check_directory(tree / "c", False) == 400


def test_clear_directory(pugwash, tree):
    scanner = pugwash.DirectoryScanner()

    scanner.check_directory(tree, False)
    scanner.clear_directory(tree)

    assert scanner.scans == {}
    assert scanner.results == {}
