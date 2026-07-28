"""User-file locations for CTHarvester.

The single place that knows where the user's own files live. Three modules used
to work this out independently — ``CTLogger``, ``utils.log_helper`` and
``utils.settings_manager`` — and they did not agree: preferences went to
``%APPDATA%/CTHarvester`` while logs went to ``~/PaleoBytes/CTHarvester/logs``.

There are two roots, and the split is deliberate (PaleoBytes convention R02):

.. code-block:: text

    <OS config dir>/PaleoBytes/CTHarvester/     preferences.json
    ~/PaleoBytes/CTHarvester/                   logs/

**Settings are not user data.** Preferences are machine-local state that costs
nothing to lose and be set again; the things under the data directory are the
user's own. They differ in whether you back them up, sync them or carry them to
another machine, so they do not belong in one directory. Keeping them apart also
forecloses a bootstrap cycle: the moment the data location becomes configurable,
a preferences file living *inside* the data directory would have to be read to
find out where it is.

**Logs stay with the data, not the settings.** Logging is configured before
preferences are read, so a log location that depended on them would mean either
discarding the early records or initialising twice — and when something goes
wrong it helps that the logs sit beside the data they describe.

The OS config directory comes from ``platformdirs``: ``%LOCALAPPDATA%`` on
Windows, ``~/Library/Application Support`` on macOS, ``~/.config`` on Linux.
Hand-rolling it breaks on ``XDG_CONFIG_HOME`` and on localised Windows folder
names, and ``QStandardPaths`` would pull Qt into a module that command-line
scripts import. The ``PaleoBytes`` segment is joined here rather than passed as
``appauthor``, which ``platformdirs`` honours on Windows only.

``CTHARVESTER_DATA_DIR`` and ``CTHARVESTER_CONFIG_DIR`` override the two roots,
which is how the tests pin resolution without touching a real home directory.
"""

import os
from pathlib import Path

import platformdirs

from config.constants import COMPANY_NAME, ENV_LOG_DIR, LOG_DIR_NAME, PROGRAM_NAME

#: Name of the user's preferences file inside the config directory.
CONFIG_FILENAME = "preferences.json"

#: Environment variable that overrides the data directory root.
DATA_DIR_ENV_VAR = "CTHARVESTER_DATA_DIR"

#: Environment variable that overrides the config directory root.
CONFIG_DIR_ENV_VAR = "CTHARVESTER_CONFIG_DIR"


def get_data_dir() -> Path:
    """Return the directory holding the user's data (currently just logs).

    ``~/PaleoBytes/CTHarvester`` unless ``CTHARVESTER_DATA_DIR`` says otherwise.
    Nothing is created here — creating directories is
    :func:`utils.common.ensure_directories`' job, and callers that need them pass
    :func:`user_directories` to it.
    """
    override = os.environ.get(DATA_DIR_ENV_VAR)
    if override:
        return Path(override)
    return Path.home() / COMPANY_NAME / PROGRAM_NAME


def get_config_dir() -> Path:
    """Return the directory holding the user's preferences.

    The OS configuration location, with a ``PaleoBytes/CTHarvester`` suffix, so
    the suite groups together wherever the platform puts config.
    """
    override = os.environ.get(CONFIG_DIR_ENV_VAR)
    if override:
        return Path(override)
    return Path(platformdirs.user_config_dir()) / COMPANY_NAME / PROGRAM_NAME


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
    return get_config_dir() / CONFIG_FILENAME


def user_directories() -> list[str]:
    """Return the directories the application should create on startup.

    The log directory and the config directory. The startup path used to create
    ``data/`` and ``backups/`` as well — constants inherited from Modan2, which
    has a database. CTHarvester has none, so those two were made empty in every
    user profile and read by nothing.
    """
    return [str(get_log_directory()), str(get_config_dir())]
