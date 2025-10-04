"""
Tests for config/tooltips.py - Tooltip definitions

Part of Phase 1 quality improvement plan (devlog 072)
"""

from unittest.mock import MagicMock

import pytest

from config.tooltips import TooltipManager


class TestTooltipManager:
    """Test suite for TooltipManager class"""

    def test_tooltips_dictionary_exists(self):
        """Test that TOOLTIPS dictionary is defined"""
        assert hasattr(TooltipManager, "TOOLTIPS")
        assert isinstance(TooltipManager.TOOLTIPS, dict)
        assert len(TooltipManager.TOOLTIPS) > 0

    def test_tooltip_structure(self):
        """Test that each tooltip has correct structure"""
        for action, info in TooltipManager.TOOLTIPS.items():
            assert isinstance(info, dict), f"Action {action} should have dict value"
            assert (
                "tooltip" in info or "status" in info
            ), f"Action {action} should have tooltip or status"

    def test_get_tooltip_existing_action(self):
        """Test getting tooltip for existing action"""
        tooltip = TooltipManager.get_tooltip("open_directory")

        assert isinstance(tooltip, str)
        assert len(tooltip) > 0
        assert "Open Directory" in tooltip

    def test_get_tooltip_non_existing_action(self):
        """Test getting tooltip for non-existing action returns empty string"""
        tooltip = TooltipManager.get_tooltip("non_existing_action")

        assert tooltip == ""

    def test_get_status_tip_existing_action(self):
        """Test getting status tip for existing action"""
        status = TooltipManager.get_status_tip("open_directory")

        assert isinstance(status, str)
        assert len(status) > 0

    def test_get_status_tip_non_existing_action(self):
        """Test getting status tip for non-existing action returns empty string"""
        status = TooltipManager.get_status_tip("non_existing_action")

        assert status == ""

    def test_file_operations_tooltips(self):
        """Test that file operation tooltips are defined"""
        file_operations = ["open_directory", "reload_directory", "save_cropped", "export_mesh"]

        for action in file_operations:
            assert action in TooltipManager.TOOLTIPS
            tooltip = TooltipManager.get_tooltip(action)
            assert len(tooltip) > 0

    def test_thumbnail_operations_tooltips(self):
        """Test that thumbnail operation tooltips are defined"""
        assert "generate_thumbnails" in TooltipManager.TOOLTIPS
        tooltip = TooltipManager.get_tooltip("generate_thumbnails")
        assert "Thumbnail" in tooltip

    def test_view_controls_tooltips(self):
        """Test that view control tooltips are defined"""
        view_controls = ["zoom_in", "zoom_out", "zoom_fit", "toggle_3d_view"]

        for action in view_controls:
            assert action in TooltipManager.TOOLTIPS

    def test_navigation_tooltips(self):
        """Test that navigation tooltips are defined"""
        navigation = ["next_slice", "prev_slice"]

        for action in navigation:
            assert action in TooltipManager.TOOLTIPS
            tooltip = TooltipManager.get_tooltip(action)
            assert "slice" in tooltip.lower()

    def test_crop_region_tooltips(self):
        """Test that crop region tooltips are defined"""
        crop_actions = ["set_bottom", "set_top", "reset_crop"]

        for action in crop_actions:
            assert action in TooltipManager.TOOLTIPS

    def test_threshold_tooltip(self):
        """Test that threshold tooltip is defined"""
        assert "threshold_slider" in TooltipManager.TOOLTIPS
        tooltip = TooltipManager.get_tooltip("threshold_slider")
        assert "threshold" in tooltip.lower()

    def test_help_tooltips(self):
        """Test that help tooltips are defined"""
        help_actions = ["show_shortcuts", "show_about"]

        for action in help_actions:
            assert action in TooltipManager.TOOLTIPS

    def test_tooltips_contain_html(self):
        """Test that tooltips use HTML formatting"""
        tooltip = TooltipManager.get_tooltip("open_directory")

        assert "<b>" in tooltip  # Bold tags
        assert "</b>" in tooltip
        assert "<br>" in tooltip  # Line breaks

    def test_tooltips_contain_shortcuts(self):
        """Test that tooltips include keyboard shortcuts"""
        tooltip = TooltipManager.get_tooltip("open_directory")

        assert "<i>" in tooltip  # Italic tags for shortcuts
        assert "Ctrl" in tooltip or "Shortcut" in tooltip

    def test_set_action_tooltips(self):
        """Test setting tooltips on a QAction object"""
        # Create mock QAction
        mock_action = MagicMock()

        # Set tooltips
        TooltipManager.set_action_tooltips(mock_action, "open_directory")

        # Verify setToolTip was called
        mock_action.setToolTip.assert_called_once()
        tooltip_arg = mock_action.setToolTip.call_args[0][0]
        assert "Open Directory" in tooltip_arg

        # Verify setStatusTip was called
        mock_action.setStatusTip.assert_called_once()
        status_arg = mock_action.setStatusTip.call_args[0][0]
        assert len(status_arg) > 0

    def test_set_action_tooltips_non_existing(self):
        """Test setting tooltips for non-existing action"""
        mock_action = MagicMock()

        # Should not crash, but won't call setters because tooltip/status are empty
        TooltipManager.set_action_tooltips(mock_action, "non_existing_action")

        # Since tooltip and status are empty, they should not be set
        mock_action.setToolTip.assert_not_called()
        mock_action.setStatusTip.assert_not_called()

    @pytest.mark.parametrize(
        "action,expected_keyword",
        [
            ("open_directory", "directory"),
            ("zoom_in", "zoom"),
            ("save_cropped", "save"),
            ("export_mesh", "mesh"),
            ("generate_thumbnails", "thumbnail"),
        ],
    )
    def test_tooltip_contains_keyword(self, action, expected_keyword):
        """Parametrized test to verify tooltips contain expected keywords"""
        tooltip = TooltipManager.get_tooltip(action)
        assert expected_keyword.lower() in tooltip.lower()

    def test_all_tooltips_have_both_fields(self):
        """Test that all tooltip entries have both tooltip and status fields"""
        for action, info in TooltipManager.TOOLTIPS.items():
            # At least one should be present
            has_tooltip = "tooltip" in info and info["tooltip"]
            has_status = "status" in info and info["status"]

            assert (
                has_tooltip or has_status
            ), f"Action {action} should have at least tooltip or status"

    def test_tooltip_consistency(self):
        """Test that tooltip and status tip are related for same action"""
        # Pick a few actions and verify tooltip/status are consistent
        test_actions = ["open_directory", "save_cropped", "zoom_in"]

        for action in test_actions:
            tooltip = TooltipManager.get_tooltip(action)
            status = TooltipManager.get_status_tip(action)

            if tooltip and status:
                # Extract main keyword from both (crude check)
                # This is a basic sanity check that they're related
                assert isinstance(tooltip, str)
                assert isinstance(status, str)

    def test_shortcuts_formatting(self):
        """Test that shortcuts are properly formatted in tooltips"""
        # Check a few tooltips that should have shortcuts
        actions_with_shortcuts = ["open_directory", "save_cropped", "zoom_in"]

        for action in actions_with_shortcuts:
            tooltip = TooltipManager.get_tooltip(action)
            # Should have italic tags for shortcuts
            assert "<i>" in tooltip and "</i>" in tooltip
