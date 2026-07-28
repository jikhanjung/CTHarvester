"""Tests for utils.paths — the single owner of the user-data layout.

What matters here is that every consumer resolves to the *same* directory. Three
modules used to compute this independently and disagreed (preferences went to
%APPDATA%, logs to ~/PaleoBytes), so the agreement is the thing worth pinning,
not the individual strings.
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


class TestLayout:
    """The paths themselves."""

    def test_default_is_under_the_paleobytes_profile(self, monkeypatch, tmp_path):
        monkeypatch.delenv(paths.DATA_DIR_ENV_VAR, raising=False)
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

        assert paths.get_data_dir() == tmp_path / "PaleoBytes" / "CTHarvester"

    def test_env_var_overrides_the_default(self, data_dir):
        assert paths.get_data_dir() == data_dir

    def test_logs_and_preferences_share_one_directory(self, data_dir):
        assert paths.get_log_directory() == data_dir / "logs"
        assert paths.get_config_path() == data_dir / "preferences.json"

    def test_log_dir_env_var_wins_over_data_dir(self, data_dir, tmp_path, monkeypatch):
        """CTHARVESTER_LOG_DIR names the log directory outright, so it is more
        specific than CTHARVESTER_DATA_DIR and takes precedence."""
        elsewhere = tmp_path / "elsewhere"
        monkeypatch.setenv("CTHARVESTER_LOG_DIR", str(elsewhere))

        assert paths.get_log_directory() == elsewhere
        # Preferences are unaffected: it overrides logs only.
        assert paths.get_config_path() == data_dir / "preferences.json"

    def test_preferences_file_is_json(self):
        assert paths.CONFIG_FILENAME == "preferences.json"

    def test_startup_creates_only_the_two_directories_in_use(self, data_dir):
        """data/ and backups/ came from Modan2's database and are gone."""
        assert paths.user_directories() == [str(data_dir), str(data_dir / "logs")]

    def test_get_data_dir_creates_nothing(self, data_dir):
        paths.get_data_dir()
        paths.get_log_directory()
        assert not data_dir.exists()


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

    def test_settings_manager_writes_to_the_shared_config_path(self, data_dir):
        mgr = SettingsManager()

        assert Path(mgr.get_config_file_path()) == paths.get_config_path()


class TestSettingsFile:
    """Format and failure handling of the preferences file."""

    def test_round_trip_through_json(self, data_dir):
        mgr = SettingsManager()
        mgr.set("application.language", "ko")
        mgr.set("thumbnails.max_size", 1000)
        mgr.save()

        on_disk = json.loads(paths.get_config_path().read_text(encoding="utf-8"))
        assert on_disk["application"]["language"] == "ko"
        assert on_disk["thumbnails"]["max_size"] == 1000
        assert SettingsManager().get("application.language") == "ko"

    def test_non_ascii_values_survive(self, data_dir):
        mgr = SettingsManager()
        mgr.set("paths.last_directory", "/데이터/스캔")
        mgr.save()

        assert SettingsManager().get("paths.last_directory") == "/데이터/스캔"

    def test_unreadable_file_is_kept_as_bak_not_overwritten(self, data_dir):
        data_dir.mkdir(parents=True)
        config = paths.get_config_path()
        config.write_text("{ this is not json", encoding="utf-8")

        mgr = SettingsManager()

        # Defaults are in force, but the file that caused it is still recoverable.
        assert mgr.get("application.language") == "auto"
        backup = config.with_suffix(config.suffix + ".bak")
        assert backup.read_text(encoding="utf-8") == "{ this is not json"

    def test_missing_file_is_created_with_defaults(self, data_dir):
        mgr = SettingsManager()

        assert paths.get_config_path().exists()
        assert mgr.get("processing.use_rust_module") is True

    def test_defaults_have_a_single_definition(self, data_dir):
        """config/settings.yaml is gone; the dict is the only source.

        It was a second hand-kept copy that had already drifted, and it was never
        bundled into the frozen build, so releases never read it anyway.
        """
        assert not (Path(__file__).parent.parent / "config" / "settings.yaml").exists()
        assert SettingsManager().default_settings == SettingsManager()._get_default_settings()
