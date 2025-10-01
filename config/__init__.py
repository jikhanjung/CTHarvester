"""Configuration constants and view mode definitions.

This package contains application-wide configuration constants, default values,
and view mode definitions used across the CTHarvester application.

Created during Phase 4 refactoring to centralize configuration management.

Modules:
    constants: Global application constants (app info, paths, defaults)
    view_modes: UI view mode and interaction mode constants

Key Features:
    - Application metadata (name, version, organization)
    - Default paths and directories
    - Image processing constants
    - 3D viewer interaction modes
    - ROI (Region of Interest) settings

Example:
    >>> from config.constants import APP_NAME, DEFAULT_THUMBNAIL_LEVELS
    >>> from config.view_modes import ROTATE_MODE, ZOOM_MODE
    >>> print(f"Running {APP_NAME}")
    >>> print(f"Default levels: {DEFAULT_THUMBNAIL_LEVELS}")

Note:
    Constants should be imported directly from their respective modules
    rather than modifying them at runtime to ensure consistent behavior.

See Also:
    config.constants: Application constants and defaults
    config.view_modes: View and interaction mode constants
"""
