# SPDX-FileCopyrightText: 2025-present Erik Abair <erik.abair@bearbrains.work>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import glob
import logging
import os
import subprocess
import sys
import tempfile
from os import PathLike
from typing import TYPE_CHECKING

from python_xiso_repacker import _copy_file, ensure_extract_xiso, extract_file, replace_file
from python_xiso_repacker.util.github import download_github_release_asset

if TYPE_CHECKING:
    from collections.abc import Sequence


logger = logging.getLogger(__name__)

_NXDK_PGRAPH_TESTS_REPO_API = "https://api.github.com/repos/abaire/nxdk_pgraph_tests"
_NXDK_PGRAPH_TESTS_CONFIG_FILE = "nxdk_pgraph_tests_config.json"

__all__ = [
    "download_latest_iso",
    "ensure_extract_xiso",
    "extract_config",
    "extract_file",
    "repack_config",
    "replace_file",
    "run",
]


def download_latest_iso(output_path: str | PathLike) -> bool:
    """Downloads the latest nxdk_pgraph_tests xiso."""
    logger.info("Downloading latest nxdk_pgraph_tests xiso...")
    return download_github_release_asset(
        _NXDK_PGRAPH_TESTS_REPO_API,
        output_path,
        name_ends_with=".iso",
    )


def _ensure_output_directory(output: str) -> str:
    if os.path.isdir(output) or not output.endswith(".iso"):
        output = os.path.join(output, "nxdk_pgraph_tests_xiso-updated.iso")

    output_dirname = os.path.dirname(output)
    if output_dirname:
        os.makedirs(output_dirname, exist_ok=True)

    return output


def repack_config(iso_file: str, output_file: str, config_file: str, extract_xiso_binary: str) -> bool:
    """Updates the given nxdk_pgraph_tests xiso with a new JSON config file and writes it to the given location."""
    logger.info(
        "Repacking config in %s from %s using %s",
        iso_file,
        config_file,
        extract_xiso_binary,
    )
    return replace_file(
        iso_file=iso_file,
        output_file=output_file,
        target_file=_NXDK_PGRAPH_TESTS_CONFIG_FILE,
        replacement_file=config_file,
        extract_xiso_binary=extract_xiso_binary,
    )


def extract_config(iso_file: str, output_file: str, extract_xiso_binary: str) -> bool:
    """Extracts the JSON config file from the given nxdk_pgraph_tests xiso and writes it to the given location."""
    logger.info("Extracting config from %s using %s", iso_file, extract_xiso_binary)

    # First attempt direct extraction of the standard config file name
    if extract_file(iso_file, _NXDK_PGRAPH_TESTS_CONFIG_FILE, output_file, extract_xiso_binary):
        return True

    # Fall back to extracting any JSON config file present in the ISO
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            subprocess.run(
                [extract_xiso_binary, "-d", tmpdir, "-x", iso_file],
                capture_output=True,
                check=True,
            )
        except KeyboardInterrupt:
            raise
        except Exception:
            logger.exception("Failed to extract iso %s using %s", iso_file, extract_xiso_binary)
            return False

        accepted_config_file = ""
        for config_file in glob.glob(os.path.join(tmpdir, "*.json")):
            accepted_config_file = config_file
            if os.path.basename(config_file) == _NXDK_PGRAPH_TESTS_CONFIG_FILE:
                break

        if not accepted_config_file:
            return False

        logger.info("Retrieved %s", os.path.basename(accepted_config_file))
        _copy_file(accepted_config_file, output_file)
        return True


def run(argv: Sequence[str] | None = None):
    """Parses program arguments and executes the repacker."""

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enables verbose logging information",
    )

    parser.add_argument(
        "--output",
        "-o",
        help="Path to where the reconfigured xiso should be saved",
        default="nxdk_pgraph_tests_xiso-updated.iso",
    )
    parser.add_argument("--extract-xiso-tool", "-T", help="Path to the extract-xiso tool")

    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--download",
        "-d",
        default="nxdk_pgraph_tests_xiso-latest.iso",
        help="Download the latest nxdk_pgraph_tests xiso",
    )
    source.add_argument(
        "--iso",
        "-i",
        help="Path to an existing nxdk_pgraph_tests xiso file to reconfigure",
    )

    action = parser.add_mutually_exclusive_group()
    action.add_argument(
        "--config",
        "-c",
        metavar="config_json_filepath",
        help="Path to the new JSON config to inject into the xiso",
    )
    action.add_argument(
        "--extract-config",
        "-e",
        metavar="extracted_config_filepath",
        help="Extract the existing config from the xiso instead of repacking",
    )

    args = parser.parse_args(argv)

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level)

    output = _ensure_output_directory(args.output)

    if args.iso:
        iso_file = args.iso
    else:
        if not download_latest_iso(args.download):
            sys.exit(1)
        iso_file = args.download

    if not os.path.isfile(iso_file):
        logger.error("Input ISO '%s' not found!", iso_file)
        sys.exit(2)

    if not (args.config or args.extract_config):
        sys.exit(0)

    extract_xiso = ensure_extract_xiso(args.extract_xiso_tool)
    if not extract_xiso:
        logger.error("extract-xiso tool not found")
        sys.exit(3)

    if args.config and not repack_config(iso_file, output, args.config, extract_xiso):
        sys.exit(100)
    if args.extract_config and not extract_config(iso_file, args.extract_config, extract_xiso):
        sys.exit(100)

    sys.exit(0)
