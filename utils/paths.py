"""User-data locations for CTHarvester.

The single place that knows where the user's own files live. Three modules used
to work this out independently — ``CTLogger``, ``utils.log_helper`` and
``utils.settings_manager`` — and they did not agree: preferences went to
``%APPDATA%/CTHarvester`` while logs went to ``~/PaleoBytes/CTHarvester/logs``.

Everything the user owns now sits under one directory:

.. code-block:: text

    ~/PaleoBytes/CTHarvester/
        preferences.json
        logs/

That is the layout Modan2 and PaperMeister use, and the reason for it is the
same in all three: backing up or moving a profile is a single directory copy,
which a split between a dot-directory and ``%APPDATA%`` cannot offer.

``CTHARVESTER_DATA_DIR`` overrides the root, which is how the tests pin
resolution without touching a real home directory.
"""

import os
from pathlib import Path

from config.constants import COMPANY_NAME, ENV_LOG_DIR, LOG_DIR_NAME, PROGRAM_NAME

#: Name of the user's preferences file inside the data directory.
CONFIG_FILENAME = "preferences.json"

#: Environment variable that overrides the data directory root.
DATA_DIR_ENV_VAR = "CTHARVESTER_DATA_DIR"


def get_data_dir() -> Path:
    """Return the directory holding everything the user owns.

    ``~/PaleoBytes/CTHarvester`` unless ``CTHARVESTER_DATA_DIR`` says otherwise.
    Nothing is created here — creating directories is
    :func:`utils.common.ensure_directories`' job, and callers that need them pass
    :func:`user_directories` to it.
    """
    override = os.environ.get(DATA_DIR_ENV_VAR)
    if override:
        return Path(override)
    return Path.home() / COMPANY_NAME / PROGRAM_NAME


def get_log_directory() -> Path:
    """Return the log directory, ``<data dir>/logs``.

    ``CTHARVESTER_LOG_DIR`` wins over ``CTHARVESTER_DATA_DIR``: it names the log
    directory outright, which is the more specific instruction. Both overrides are
    resolved here rather than in :mod:`CTLogger` so that the "Open log directory"
    action and the log viewer point at the files the handler actually writes —
    when the two worked it out separately, they disagreed under
    ``CTHARVESTER_LOG_DIR``.
    """
    override = os.environ.get(ENV_LOG_DIR)
    if override:
        return Path(override)
    return get_data_dir() / LOG_DIR_NAME


def get_config_path() -> Path:
    """Return the path of the user's preferences file."""
    return get_data_dir() / CONFIG_FILENAME


def user_directories() -> list[str]:
    """Return the directories the application should create on startup.

    Only two: the data directory and its ``logs``. The startup path used to
    create ``data/`` and ``backups/`` as well — constants inherited from Modan2,
    which has a database. CTHarvester has none, so those two were made empty in
    every user profile and read by nothing.
    """
    return [str(get_data_dir()), str(get_log_directory())]
