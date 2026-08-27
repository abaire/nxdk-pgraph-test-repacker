# SPDX-FileCopyrightText: 2025-present Erik Abair <erik.abair@bearbrains.work>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from nxdk_pgraph_test_repacker import (
    _copy_file,
    _ensure_output_directory,
    download_latest_iso,
    ensure_extract_xiso,
    extract_config,
    extract_file,
    repack_config,
    replace_file,
    run,
)


def test_download_works(tmp_path):
    output_file = tmp_path / "downloaded.iso"

    def _fake_download(target: str, url: str) -> bool:
        del target, url
        output_file.write_text("iso")
        return True

    with (
        patch(
            "nxdk_pgraph_test_repacker.fetch_github_release_info",
            return_value={
                "assets": [
                    {
                        "name": "nxdk_pgraph_tests.iso",
                        "browser_download_url": "https://example.com/test.iso",
                    }
                ]
            },
        ) as mock_fetch,
        patch(
            "nxdk_pgraph_test_repacker.download_artifact",
            side_effect=_fake_download,
        ) as mock_download,
    ):
        assert download_latest_iso(output_file)
        assert os.path.isfile(output_file)
        mock_fetch.assert_called_once()
        mock_download.assert_called_once_with(str(output_file), "https://example.com/test.iso")


def test_copy_file(tmp_path):
    src = tmp_path / "src.txt"
    src.write_text("hello")
    dst = tmp_path / "nested" / "dir" / "dst.txt"
    _copy_file(str(src), str(dst))
    assert dst.read_text() == "hello"


def test_exports_available():
    assert callable(ensure_extract_xiso)
    assert callable(replace_file)
    assert callable(extract_file)
    assert callable(repack_config)
    assert callable(extract_config)


def test_repack_config(tmp_path):
    iso_file = tmp_path / "test.iso"
    iso_file.write_text("fake iso")
    output_file = tmp_path / "out.iso"
    config_file = tmp_path / "config.json"
    config_file.write_text("{}")

    with patch("nxdk_pgraph_test_repacker.replace_file", return_value=True) as mock_replace:
        assert repack_config(str(iso_file), str(output_file), str(config_file), "extract-xiso")
        mock_replace.assert_called_once_with(
            iso_file=str(iso_file),
            output_file=str(output_file),
            target_file="nxdk_pgraph_tests_config.json",
            replacement_file=str(config_file),
            extract_xiso_binary="extract-xiso",
        )


def test_extract_config_direct(tmp_path):
    iso_file = tmp_path / "test.iso"
    iso_file.write_text("fake iso")
    output_file = tmp_path / "out.json"

    with patch("nxdk_pgraph_test_repacker.extract_file", return_value=True) as mock_extract:
        assert extract_config(str(iso_file), str(output_file), "extract-xiso")
        mock_extract.assert_called_once_with(
            str(iso_file),
            "nxdk_pgraph_tests_config.json",
            str(output_file),
            "extract-xiso",
        )


def test_extract_config_fallback(tmp_path):
    iso_file = tmp_path / "test.iso"
    iso_file.write_text("fake iso")
    output_file = tmp_path / "nested" / "out.json"

    def fake_run(cmd: list[str], **_kwargs: object) -> None:
        extracted_dir = cmd[2]
        config = os.path.join(extracted_dir, "nxdk_pgraph_tests_config.json")
        with open(config, "w") as f:
            f.write('{"test": 1}')

    with (
        patch("nxdk_pgraph_test_repacker.extract_file", return_value=False),
        patch("nxdk_pgraph_test_repacker.subprocess.run", side_effect=fake_run),
    ):
        assert extract_config(str(iso_file), str(output_file), "extract-xiso")
        assert output_file.read_text() == '{"test": 1}'


def test_ensure_output_directory(tmp_path):
    # Case 1: path ending in .iso
    iso_path = str(tmp_path / "custom" / "my.iso")
    res = _ensure_output_directory(iso_path)
    assert res == iso_path
    assert os.path.isdir(tmp_path / "custom")

    # Case 2: existing directory
    dir_path = tmp_path / "existing_dir"
    dir_path.mkdir()
    res = _ensure_output_directory(str(dir_path))
    assert res == str(dir_path / "nxdk_pgraph_tests_xiso-updated.iso")

    # Case 3: non-.iso filename / non-existing directory path
    no_ext = str(tmp_path / "some_folder")
    res = _ensure_output_directory(no_ext)
    assert res == str(tmp_path / "some_folder" / "nxdk_pgraph_tests_xiso-updated.iso")


def test_run_download_flag(tmp_path):
    iso_file = tmp_path / "nxdk_pgraph_tests_xiso-latest.iso"
    iso_file.write_text("fake iso")

    with (
        patch("nxdk_pgraph_test_repacker.download_latest_iso", return_value=True) as mock_download,
        patch("os.path.isfile", return_value=True),
        pytest.raises(SystemExit) as excinfo,
    ):
        run(["--download"])
    assert excinfo.value.code == 0
    mock_download.assert_called_once_with("nxdk_pgraph_tests_xiso-latest.iso")


def test_run_download_custom_file():
    with (
        patch("nxdk_pgraph_test_repacker.download_latest_iso", return_value=True) as mock_download,
        patch("os.path.isfile", return_value=True),
        pytest.raises(SystemExit) as excinfo,
    ):
        run(["--download", "custom.iso"])
    assert excinfo.value.code == 0
    mock_download.assert_called_once_with("custom.iso")


def test_run_download_failed():
    with (
        patch("nxdk_pgraph_test_repacker.download_latest_iso", return_value=False),
        pytest.raises(SystemExit) as excinfo,
    ):
        run(["--download"])
    assert excinfo.value.code == 1


def test_run_iso_not_found(tmp_path):
    with pytest.raises(SystemExit) as excinfo:
        run(["--iso", str(tmp_path / "nonexistent.iso")])
    assert excinfo.value.code == 2


def test_run_repack_success(tmp_path):
    iso_file = tmp_path / "test.iso"
    iso_file.write_text("fake iso")
    config_file = tmp_path / "config.json"
    config_file.write_text("{}")
    output_file = tmp_path / "out.iso"

    with (
        patch(
            "nxdk_pgraph_test_repacker.ensure_extract_xiso",
            return_value="/path/to/extract-xiso",
        ),
        patch("nxdk_pgraph_test_repacker.repack_config", return_value=True) as mock_repack,
        pytest.raises(SystemExit) as excinfo,
    ):
        run(
            [
                "--iso",
                str(iso_file),
                "--config",
                str(config_file),
                "--output",
                str(output_file),
            ]
        )
    assert excinfo.value.code == 0
    mock_repack.assert_called_once_with(str(iso_file), str(output_file), str(config_file), "/path/to/extract-xiso")


def test_run_extract_config_success(tmp_path):
    iso_file = tmp_path / "test.iso"
    iso_file.write_text("fake iso")
    output_config = tmp_path / "out.json"

    with (
        patch(
            "nxdk_pgraph_test_repacker.ensure_extract_xiso",
            return_value="/path/to/extract-xiso",
        ),
        patch("nxdk_pgraph_test_repacker.extract_config", return_value=True) as mock_extract,
        pytest.raises(SystemExit) as excinfo,
    ):
        run(["--iso", str(iso_file), "--extract-config", str(output_config)])
    assert excinfo.value.code == 0
    mock_extract.assert_called_once_with(str(iso_file), str(output_config), "/path/to/extract-xiso")


def test_run_missing_extract_xiso(tmp_path):
    iso_file = tmp_path / "test.iso"
    iso_file.write_text("fake iso")
    config_file = tmp_path / "config.json"
    config_file.write_text("{}")

    with (
        patch("nxdk_pgraph_test_repacker.ensure_extract_xiso", return_value=None) as mock_tool,
        pytest.raises(SystemExit) as excinfo,
    ):
        run(["--iso", str(iso_file), "--config", str(config_file)])
    assert excinfo.value.code == 3
    mock_tool.assert_called_once()


def test_run_repack_failure(tmp_path):
    iso_file = tmp_path / "test.iso"
    iso_file.write_text("fake iso")
    config_file = tmp_path / "config.json"
    config_file.write_text("{}")

    with (
        patch(
            "nxdk_pgraph_test_repacker.ensure_extract_xiso",
            return_value="/path/to/extract-xiso",
        ),
        patch("nxdk_pgraph_test_repacker.repack_config", return_value=False),
        pytest.raises(SystemExit) as excinfo,
    ):
        run(["--iso", str(iso_file), "--config", str(config_file)])
    assert excinfo.value.code == 100


def test_run_extract_config_failure(tmp_path):
    iso_file = tmp_path / "test.iso"
    iso_file.write_text("fake iso")
    output_config = tmp_path / "out.json"

    with (
        patch(
            "nxdk_pgraph_test_repacker.ensure_extract_xiso",
            return_value="/path/to/extract-xiso",
        ),
        patch("nxdk_pgraph_test_repacker.extract_config", return_value=False),
        pytest.raises(SystemExit) as excinfo,
    ):
        run(["--iso", str(iso_file), "--extract-config", str(output_config)])
    assert excinfo.value.code == 100
