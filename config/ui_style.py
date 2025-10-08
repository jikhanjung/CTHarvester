"""
UI Style Constants

Defines consistent styling constants for the application UI.
Created during Phase 2.2 (UI Polish & Accessibility).
"""

from dataclasses import dataclass


@dataclass
class Spacing:
    """Spacing constants following 8px grid system"""

    # Base unit (8px grid)
    BASE = 8

    # Common spacing values
    TINY = BASE // 2  # 4px
    SMALL = BASE  # 8px
    MEDIUM = BASE * 2  # 16px
    LARGE = BASE * 3  # 24px
    XLARGE = BASE * 4  # 32px

    # Layout margins
    MARGIN_SMALL = SMALL
    MARGIN_MEDIUM = MEDIUM
    MARGIN_LARGE = LARGE

    # Widget spacing
    WIDGET_SPACING = SMALL
    BUTTON_SPACING = SMALL


@dataclass
class ButtonSize:
    """Standard button sizes"""

    # Text button minimum width
    TEXT_BUTTON_MIN_WIDTH = 80

    # Icon button size (square)
    ICON_BUTTON_SIZE = 32

    # Standard button height
    BUTTON_HEIGHT = 32

    # Large button height (for prominent actions)
    LARGE_BUTTON_HEIGHT = 40


@dataclass
class Colors:
    """UI color scheme"""

    # Primary actions (blue)
    PRIMARY = "#0078D4"
    PRIMARY_HOVER = "#106EBE"
    PRIMARY_PRESSED = "#005A9E"

    # Danger/destructive actions (red)
    DANGER = "#D13438"
    DANGER_HOVER = "#A72C2F"
    DANGER_PRESSED = "#7D2124"

    # Success/confirmation (green)
    SUCCESS = "#107C10"
    SUCCESS_HOVER = "#0E6B0E"
    SUCCESS_PRESSED = "#0B5A0B"

    # Warning/caution (orange)
    WARNING = "#FF8C00"
    WARNING_HOVER = "#E67E00"
    WARNING_PRESSED = "#CC7000"

    # Neutral/secondary actions (gray)
    NEUTRAL = "#5A5A5A"
    NEUTRAL_HOVER = "#4A4A4A"
    NEUTRAL_PRESSED = "#3A3A3A"

    # Background colors
    BACKGROUND = "#FFFFFF"
    BACKGROUND_ALT = "#F5F5F5"
    BACKGROUND_DISABLED = "#E0E0E0"

    # Text colors
    TEXT = "#202020"
    TEXT_SECONDARY = "#5A5A5A"
    TEXT_DISABLED = "#A0A0A0"

    # Border colors
    BORDER = "#D0D0D0"
    BORDER_FOCUS = "#0078D4"


class UIStyle:
    """Centralized UI style manager"""

    spacing = Spacing()
    button_size = ButtonSize()
    colors = Colors()

    @classmethod
    def get_button_style(cls, button_type: str = "default") -> str:
        """
        Get button stylesheet

        Args:
            button_type: Type of button ("primary", "danger", "success", "default")

        Returns:
            CSS stylesheet string
        """
        base_style = f"""
            QPushButton {{
                min-height: {cls.button_size.BUTTON_HEIGHT}px;
                padding: 4px {cls.spacing.SMALL}px;
                border: 1px solid {cls.colors.BORDER};
                border-radius: 4px;
                background-color: {cls.colors.BACKGROUND};
            }}
            QPushButton:hover {{
                background-color: {cls.colors.BACKGROUND_ALT};
            }}
            QPushButton:pressed {{
                background-color: {cls.colors.BORDER};
            }}
            QPushButton:disabled {{
                background-color: {cls.colors.BACKGROUND_DISABLED};
                color: {cls.colors.TEXT_DISABLED};
            }}
        """

        if button_type == "primary":
            return f"""
                QPushButton {{
                    min-height: {cls.button_size.BUTTON_HEIGHT}px;
                    padding: 4px {cls.spacing.SMALL}px;
                    border: 1px solid {cls.colors.PRIMARY};
                    border-radius: 4px;
                    background-color: {cls.colors.PRIMARY};
                    color: white;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {cls.colors.PRIMARY_HOVER};
                    border-color: {cls.colors.PRIMARY_HOVER};
                }}
                QPushButton:pressed {{
                    background-color: {cls.colors.PRIMARY_PRESSED};
                    border-color: {cls.colors.PRIMARY_PRESSED};
                }}
                QPushButton:disabled {{
                    background-color: {cls.colors.BACKGROUND_DISABLED};
                    color: {cls.colors.TEXT_DISABLED};
                    border-color: {cls.colors.BORDER};
                }}
            """
        elif button_type == "danger":
            return f"""
                QPushButton {{
                    min-height: {cls.button_size.BUTTON_HEIGHT}px;
                    padding: 4px {cls.spacing.SMALL}px;
                    border: 1px solid {cls.colors.DANGER};
                    border-radius: 4px;
                    background-color: {cls.colors.DANGER};
                    color: white;
                }}
                QPushButton:hover {{
                    background-color: {cls.colors.DANGER_HOVER};
                }}
                QPushButton:pressed {{
                    background-color: {cls.colors.DANGER_PRESSED};
                }}
            """

        return base_style

    @classmethod
    def get_icon_button_style(cls) -> str:
        """Get icon button stylesheet"""
        return f"""
            QPushButton {{
                min-width: {cls.button_size.ICON_BUTTON_SIZE}px;
                min-height: {cls.button_size.ICON_BUTTON_SIZE}px;
                max-width: {cls.button_size.ICON_BUTTON_SIZE}px;
                max-height: {cls.button_size.ICON_BUTTON_SIZE}px;
                padding: 4px;
                border: 1px solid {cls.colors.BORDER};
                border-radius: 4px;
                background-color: {cls.colors.BACKGROUND};
            }}
            QPushButton:hover {{
                background-color: {cls.colors.BACKGROUND_ALT};
            }}
            QPushButton:pressed {{
                background-color: {cls.colors.BORDER};
            }}
        """

    @classmethod
    def apply_spacing_to_layout(cls, layout, margins=None, spacing=None):
        """
        Apply consistent spacing to layout

        Args:
            layout: QLayout object
            margins: Tuple of (left, top, right, bottom) or single int for all sides
            spacing: Spacing between widgets
        """
        if margins is not None:
            if isinstance(margins, int):
                layout.setContentsMargins(margins, margins, margins, margins)
            elif isinstance(margins, (tuple, list)) and len(margins) == 4:
                layout.setContentsMargins(*margins)

        if spacing is not None:
            layout.setSpacing(spacing)
