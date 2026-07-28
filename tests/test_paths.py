"""Tests for utils.paths — the single owner of the user-file layout.

Two things are worth pinning. First, that every consumer resolves to the *same*
place: three modules used to compute this independently and disagreed. Second,
that settings and data stay in *different* roots — preferences are machine-local
state, the data directory is the user's own, and putting a config file inside a
directory whose location is itself configurable is a bootstrap cycle waiting to
happen (PaleoBytes convention R02).
"""

import json
from pathlib import Path

import pytest

from utils import paths
from utils.log_helper import get_log_directory as log_helper_log_directory
from utils.settings_manager import SettingsManager


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """Point the data directory at a temp dir via the documented override."""
    target = tmp_path / "profile"
    monkeypatch.setenv(paths.DATA_DIR_ENV_VAR, str(target))
    return target


@pytest.fixture
def config_dir(tmp_path, monkeypatch):
    """Point the config directory at a temp dir via the documented override."""
    target = tmp_path / "config"
    monkeypatch.setenv(paths.CONFIG_DIR_ENV_VAR, str(target))
    return target


class TestLayout:
    """The paths themselves."""

    def test_default_is_under_the_paleobytes_profile(self, monkeypatch, tmp_path):
        monkeypatch.delenv(paths.DATA_DIR_ENV_VAR, raising=False)
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

        assert paths.get_data_dir() == tmp_path / "PaleoBytes" / "CTHarvester"

    def test_env_var_overrides_the_default(self, data_dir):
        assert paths.get_data_dir() == data_dir

    def test_logs_live_under_the_data_directory(self, data_dir):
        assert paths.get_log_directory() == data_dir / "logs"

    def test_preferences_live_under_the_config_directory(self, config_dir):
        assert paths.get_config_path() == config_dir / "preferences.json"

    def test_settings_are_not_stored_inside_the_data_directory(self, monkeypatch, tmp_path):
        """The separation R02 asks for, checked against real resolution.

        Not a tautology about the overrides: both env vars are cleared so the
        real platformdirs / home-directory resolution runs.
        """
        monkeypatch.delenv(paths.DATA_DIR_ENV_VAR, raising=False)
        monkeypatch.delenv(paths.CONFIG_DIR_ENV_VAR, raising=False)
        monkeypatch.delenv("CTHARVESTER_LOG_DIR", raising=False)

        config = paths.get_config_path().resolve()
        data = paths.get_data_dir().resolve()

        assert data not in config.parents

    def test_config_directory_carries_the_vendor_segment(self, monkeypatch, tmp_path):
        """platformdirs ignores `appauthor` off Windows, so it is joined by hand."""
        monkeypatch.delenv(paths.CONFIG_DIR_ENV_VAR, raising=False)

        parts = paths.get_config_dir().parts
        assert parts[-2:] == ("PaleoBytes", "CTHarvester")

    def test_log_dir_env_var_wins_over_data_dir(self, data_dir, config_dir, tmp_path, monkeypatch):
        """CTHARVESTER_LOG_DIR names the log directory outright, so it is more
        specific than CTHARVESTER_DATA_DIR and takes precedence."""
        elsewhere = tmp_path / "elsewhere"
        monkeypatch.setenv("CTHARVESTER_LOG_DIR", str(elsewhere))

        assert paths.get_log_directory() == elsewhere
        # Preferences are unaffected: it overrides logs only.
        assert paths.get_config_path() == config_dir / "preferences.json"

    def test_preferences_file_is_json(self):
        assert paths.CONFIG_FILENAME == "preferences.json"

    def test_startup_creates_only_the_two_directories_in_use(self, data_dir, config_dir):
        """data/ and backups/ came from Modan2's database and are gone."""
        assert paths.user_directories() == [str(data_dir / "logs"), str(config_dir)]

    def test_resolving_paths_creates_nothing(self, data_dir, config_dir):
        paths.get_data_dir()
        paths.get_log_directory()
        paths.get_config_dir()
        paths.get_config_path()
        assert not data_dir.exists()
        assert not config_dir.exists()


class TestConsumersAgree:
    """The reason the module exists."""

    def test_log_helper_resolves_to_the_shared_log_directory(self, data_dir):
        assert log_helper_log_directory() == paths.get_log_directory()

    def test_log_helper_follows_the_log_dir_override(self, data_dir, tmp_path, monkeypatch):
        """The regression this module exists to prevent: CTHARVESTER_LOG_DIR used
        to move where logs were written without moving where the UI looked."""
        elsewhere = tmp_path / "elsewhere"
        monkeypatch.setenv("CTHARVESTER_LOG_DIR", str(elsewhere))

        assert log_helper_log_directory() == elsewhere

    def test_ctlogger_follows_the_log_dir_override(self, data_dir, tmp_path, monkeypatch):
        import CTLogger

        elsewhere = tmp_path / "elsewhere"
        monkeypatch.setenv("CTHARVESTER_LOG_DIR", str(elsewhere))

        logger, _session = CTLogger.setup_logger("CTHarvester")
        try:
            written = {
                Path(h.baseFilename).parent for h in logger.handlers if hasattr(h, "baseFilename")
            }
        finally:
            for handler in list(logger.handlers):
                handler.close()
                logger.removeHandler(handler)

        assert written == {elsewhere} == {log_helper_log_directory()}

    def test_ctlogger_resolves_to_the_shared_log_directory(self, data_dir, tmp_path):
        import CTLogger

        logger, _session = CTLogger.setup_logger("CTHarvester")
        try:
            written = {
                Path(h.baseFilename).parent for h in logger.handlers if hasattr(h, "baseFilename")
            }
        finally:
            for handler in list(logger.handlers):
                handler.close()
                logger.removeHandler(handler)

        assert written == {paths.get_log_directory()}

    def test_settings_manager_writes_to_the_shared_config_path(self, config_dir):
        mgr = SettingsManager()

        assert Path(mgr.get_config_file_path()) == paths.get_config_path()


class TestSettingsFile:
    """Format and failure handling of the preferences file."""

    def test_round_trip_through_json(self, config_dir):
        mgr = SettingsManager()
        mgr.set("application.language", "ko")
        mgr.set("thumbnails.max_size", 1000)
        mgr.save()

        on_disk = json.loads(paths.get_config_path().read_text(encoding="utf-8"))
        assert on_disk["application"]["language"] == "ko"
        assert on_disk["thumbnails"]["max_size"] == 1000
        assert SettingsManager().get("application.language") == "ko"

    def test_non_ascii_values_survive(self, config_dir):
        mgr = SettingsManager()
        mgr.set("paths.last_directory", "/데이터/스캔")
        mgr.save()

        assert SettingsManager().get("paths.last_directory") == "/데이터/스캔"

    def test_unreadable_file_is_kept_as_bak_not_overwritten(self, config_dir):
        config_dir.mkdir(parents=True)
        config = paths.get_config_path()
        config.write_text("{ this is not json", encoding="utf-8")

        mgr = SettingsManager()

        # Defaults are in force, but the file that caused it is still recoverable.
        assert mgr.get("application.language") == "auto"
        backup = config.with_suffix(config.suffix + ".bak")
        assert backup.read_text(encoding="utf-8") == "{ this is not json"

    def test_missing_file_is_created_with_defaults(self, config_dir):
        mgr = SettingsManager()

        assert paths.get_config_path().exists()
        assert mgr.get("processing.use_rust_module") is True

    def test_defaults_have_a_single_definition(self, config_dir):
        """config/settings.yaml is gone; the dict is the only source.

        It was a second hand-kept copy that had already drifted, and it was never
        bundled into the frozen build, so releases never read it anyway.
        """
        assert not (Path(__file__).parent.parent / "config" / "settings.yaml").exists()
        assert SettingsManager().default_settings == SettingsManager()._get_default_settings()
