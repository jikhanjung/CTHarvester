"""Tests for config/ui_style.py"""

import pytest

from config.ui_style import ButtonSize, Colors, Spacing, UIStyle


class TestSpacing:
    """Test Spacing constants"""

    def test_base_unit(self):
        """Test base unit is 8px"""
        assert Spacing.BASE == 8

    def test_spacing_multiples(self):
        """Test spacing values are multiples of base unit"""
        assert Spacing.TINY == 4  # BASE / 2
        assert Spacing.SMALL == 8  # BASE
        assert Spacing.MEDIUM == 16  # BASE * 2
        assert Spacing.LARGE == 24  # BASE * 3
        assert Spacing.XLARGE == 32  # BASE * 4

    def test_margin_values(self):
        """Test margin values are defined"""
        assert Spacing.MARGIN_SMALL == Spacing.SMALL
        assert Spacing.MARGIN_MEDIUM == Spacing.MEDIUM
        assert Spacing.MARGIN_LARGE == Spacing.LARGE

    def test_widget_spacing(self):
        """Test widget spacing values"""
        assert Spacing.WIDGET_SPACING == Spacing.SMALL
        assert Spacing.BUTTON_SPACING == Spacing.SMALL


class TestButtonSize:
    """Test ButtonSize constants"""

    def test_button_heights(self):
        """Test button heights are defined"""
        assert ButtonSize.BUTTON_HEIGHT == 32
        assert ButtonSize.LARGE_BUTTON_HEIGHT == 40

    def test_icon_button_size(self):
        """Test icon button is square"""
        assert ButtonSize.ICON_BUTTON_SIZE == 32

    def test_text_button_min_width(self):
        """Test text button minimum width"""
        assert ButtonSize.TEXT_BUTTON_MIN_WIDTH == 80


class TestColors:
    """Test Colors constants"""

    def test_primary_colors(self):
        """Test primary color set"""
        assert Colors.PRIMARY.startswith("#")
        assert Colors.PRIMARY_HOVER.startswith("#")
        assert Colors.PRIMARY_PRESSED.startswith("#")

    def test_danger_colors(self):
        """Test danger color set"""
        assert Colors.DANGER.startswith("#")
        assert Colors.DANGER_HOVER.startswith("#")
        assert Colors.DANGER_PRESSED.startswith("#")

    def test_success_colors(self):
        """Test success color set"""
        assert Colors.SUCCESS.startswith("#")
        assert Colors.SUCCESS_HOVER.startswith("#")
        assert Colors.SUCCESS_PRESSED.startswith("#")

    def test_neutral_colors(self):
        """Test neutral color set"""
        assert Colors.NEUTRAL.startswith("#")
        assert Colors.NEUTRAL_HOVER.startswith("#")
        assert Colors.NEUTRAL_PRESSED.startswith("#")

    def test_background_colors(self):
        """Test background color set"""
        assert Colors.BACKGROUND.startswith("#")
        assert Colors.BACKGROUND_ALT.startswith("#")
        assert Colors.BACKGROUND_DISABLED.startswith("#")

    def test_text_colors(self):
        """Test text color set"""
        assert Colors.TEXT.startswith("#")
        assert Colors.TEXT_SECONDARY.startswith("#")
        assert Colors.TEXT_DISABLED.startswith("#")

    def test_border_colors(self):
        """Test border color set"""
        assert Colors.BORDER.startswith("#")
        assert Colors.BORDER_FOCUS.startswith("#")


class TestUIStyle:
    """Test UIStyle manager"""

    def test_class_attributes(self):
        """Test UIStyle has spacing, button_size, colors"""
        assert hasattr(UIStyle, "spacing")
        assert hasattr(UIStyle, "button_size")
        assert hasattr(UIStyle, "colors")

    def test_get_button_style_default(self):
        """Test default button style"""
        style = UIStyle.get_button_style()
        assert isinstance(style, str)
        assert "QPushButton" in style
        assert "min-height" in style
        assert str(UIStyle.button_size.BUTTON_HEIGHT) in style

    def test_get_button_style_primary(self):
        """Test primary button style"""
        style = UIStyle.get_button_style("primary")
        assert isinstance(style, str)
        assert "QPushButton" in style
        assert UIStyle.colors.PRIMARY in style
        assert "font-weight: bold" in style

    def test_get_button_style_danger(self):
        """Test danger button style"""
        style = UIStyle.get_button_style("danger")
        assert isinstance(style, str)
        assert "QPushButton" in style
        assert UIStyle.colors.DANGER in style

    def test_get_icon_button_style(self):
        """Test icon button style"""
        style = UIStyle.get_icon_button_style()
        assert isinstance(style, str)
        assert "QPushButton" in style
        assert "min-width" in style
        assert "min-height" in style
        assert str(UIStyle.button_size.ICON_BUTTON_SIZE) in style

    def test_button_style_contains_states(self):
        """Test button styles include hover/pressed/disabled states"""
        style = UIStyle.get_button_style()
        assert ":hover" in style
        assert ":pressed" in style
        assert ":disabled" in style

    def test_apply_spacing_to_layout_single_margin(self):
        """Test apply_spacing_to_layout with single margin value"""
        from PyQt5.QtWidgets import QVBoxLayout

        layout = QVBoxLayout()
        UIStyle.apply_spacing_to_layout(layout, margins=16, spacing=8)

        margins = layout.contentsMargins()
        assert margins.left() == 16
        assert margins.top() == 16
        assert margins.right() == 16
        assert margins.bottom() == 16
        assert layout.spacing() == 8

    def test_apply_spacing_to_layout_tuple_margin(self):
        """Test apply_spacing_to_layout with tuple margins"""
        from PyQt5.QtWidgets import QHBoxLayout

        layout = QHBoxLayout()
        UIStyle.apply_spacing_to_layout(layout, margins=(8, 16, 24, 32), spacing=4)

        margins = layout.contentsMargins()
        assert margins.left() == 8
        assert margins.top() == 16
        assert margins.right() == 24
        assert margins.bottom() == 32
        assert layout.spacing() == 4

    def test_apply_spacing_none_values(self):
        """Test apply_spacing_to_layout with None values"""
        from PyQt5.QtWidgets import QVBoxLayout

        layout = QVBoxLayout()
        original_spacing = layout.spacing()

        # Should not crash with None values
        UIStyle.apply_spacing_to_layout(layout, margins=None, spacing=None)

        # Spacing should remain unchanged
        assert layout.spacing() == original_spacing


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
