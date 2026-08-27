# SPDX-FileCopyrightText: 2025-present Erik Abair <erik.abair@bearbrains.work>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os
from unittest.mock import patch

from nxdk_pgraph_test_repacker import (
    download_latest_iso,
    ensure_extract_xiso,
    extract_config,
    extract_file,
    repack_config,
    replace_file,
)


def test_download_works(tmp_path):
    output_file = tmp_path / "downloaded.iso"

    assert download_latest_iso(output_file)

    assert os.path.isfile(output_file)


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
