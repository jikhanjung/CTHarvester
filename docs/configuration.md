# Configuration Guide

CTHarvester uses YAML-based configuration for flexible, human-readable settings management. This guide documents all available configuration options in `config/settings.yaml`.

## Table of Contents

- [Configuration File Location](#configuration-file-location)
- [Application Settings](#application-settings)
- [Window Settings](#window-settings)
- [Thumbnail Settings](#thumbnail-settings)
- [Processing Settings](#processing-settings)
- [Rendering Settings](#rendering-settings)
- [Export Settings](#export-settings)
- [Logging Settings](#logging-settings)
- [Path Settings](#path-settings)
- [Advanced Configuration](#advanced-configuration)

## Configuration File Location

**Default Location:**
- Linux/macOS: `~/.config/CTHarvester/settings.yaml`
- Windows: `%APPDATA%\CTHarvester\settings.yaml`

**Fallback:** `config/settings.yaml` in the application directory

The settings file is created automatically on first run with default values.

## Application Settings

```yaml
application:
  language: auto
  theme: light
  auto_save_settings: true
```

### `language`
- **Type:** String
- **Default:** `auto`
- **Valid Values:** `auto`, `en`, `ko`
- **Description:** UI language selection
  - `auto`: Detect system language
  - `en`: English
  - `ko`: Korean (한국어)
- **Example:**
  ```yaml
  application:
    language: en
  ```

### `theme`
- **Type:** String
- **Default:** `light`
- **Valid Values:** `light`, `dark`
- **Description:** Application theme (future feature)
- **Note:** Currently only light theme is implemented

### `auto_save_settings`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Automatically save settings on exit
- **Use Case:** Disable for testing or read-only environments

## Window Settings

```yaml
window:
  width: 1200
  height: 800
  remember_position: true
  remember_size: true
```

### `width` / `height`
- **Type:** Integer
- **Default:** 1200 x 800
- **Valid Range:** 800-4096 pixels
- **Description:** Default window dimensions
- **Example:**
  ```yaml
  window:
    width: 1600
    height: 900
  ```

### `remember_position` / `remember_size`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Restore window geometry from last session
- **Use Case:** Disable for kiosk mode or fixed layouts

## Thumbnail Settings

```yaml
thumbnails:
  max_size: 500
  sample_size: 20
  max_level: 10
  compression: true
  format: tif
```

### `max_size`
- **Type:** Integer
- **Default:** `500`
- **Valid Range:** 100-2000 pixels
- **Description:** Maximum dimension for thumbnail images
- **Performance Impact:** Higher values = better quality, slower generation
- **Example:**
  ```yaml
  thumbnails:
    max_size: 256  # Faster preview, lower quality
  ```

### `sample_size`
- **Type:** Integer
- **Default:** `20`
- **Valid Range:** 1-100 images
- **Description:** Number of images to sample for progress estimation
- **Use Case:**
  - Small datasets: 10-20
  - Large datasets: 50-100 for better ETA accuracy
- **Example:**
  ```yaml
  thumbnails:
    sample_size: 50  # More accurate ETA for large datasets
  ```

### `max_level`
- **Type:** Integer
- **Default:** `10`
- **Valid Range:** 1-20 levels
- **Description:** Maximum number of LoD (Level of Detail) pyramid levels
- **Note:** Actual levels depend on image size (each level is 1/2 resolution)
- **Example:**
  ```yaml
  thumbnails:
    max_level: 5  # For smaller datasets
  ```

### `compression`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Enable thumbnail compression
- **Trade-off:**
  - `true`: Slower generation, smaller disk usage
  - `false`: Faster generation, larger disk usage

### `format`
- **Type:** String
- **Default:** `tif`
- **Valid Values:** `tif`, `png`
- **Description:** Thumbnail image format
- **Recommendations:**
  - `tif`: Best for 16-bit CT data
  - `png`: Better compression for 8-bit data

## Processing Settings

```yaml
processing:
  threads: auto
  memory_limit_gb: 4
  use_rust_module: false
```

### `threads`
- **Type:** String or Integer
- **Default:** `auto`
- **Valid Values:** `auto`, 1-16
- **Description:** Worker thread count for thumbnail generation
- **Behavior:**
  - `auto`: Use CPU core count
  - Number: Use specific thread count
- **Performance Notes:**
  - More threads ≠ always faster (I/O bound)
  - Recommended: `auto` or CPU cores / 2
- **Example:**
  ```yaml
  processing:
    threads: 4  # Use 4 threads explicitly
  ```

### `memory_limit_gb`
- **Type:** Integer
- **Default:** `4`
- **Valid Range:** 1-64 GB
- **Description:** Maximum memory usage hint
- **Note:** Currently advisory, not enforced

### `use_rust_module`
- **Type:** Boolean
- **Default:** `false`
- **Description:** Use Rust-based thumbnail generation (if available)
- **Performance:**
  - `true`: ~2-3x faster (if Rust module compiled)
  - `false`: Pure Python (always available)
- **Example:**
  ```yaml
  processing:
    use_rust_module: true  # Use Rust if available
  ```

## Rendering Settings

```yaml
rendering:
  background_color: [0.2, 0.2, 0.2]
  default_threshold: 128
  anti_aliasing: true
  show_fps: false
```

### `background_color`
- **Type:** RGB Array
- **Default:** `[0.2, 0.2, 0.2]` (dark gray)
- **Valid Range:** 0.0-1.0 per channel
- **Description:** 3D viewer background color
- **Example:**
  ```yaml
  rendering:
    background_color: [0.0, 0.0, 0.0]  # Black background
  ```

### `default_threshold`
- **Type:** Integer
- **Default:** `128`
- **Valid Range:** 0-255
- **Description:** Initial threshold for marching cubes
- **Use Case:** Adjust based on typical CT scan density

### `anti_aliasing`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Enable anti-aliasing for 3D rendering
- **Performance:** Minimal impact on modern GPUs

### `show_fps`
- **Type:** Boolean
- **Default:** `false`
- **Description:** Display FPS counter in 3D viewer
- **Use Case:** Performance debugging

## Export Settings

```yaml
export:
  mesh_format: stl
  image_format: tif
  compression_level: 6
```

### `mesh_format`
- **Type:** String
- **Default:** `stl`
- **Valid Values:** `stl`, `ply`, `obj`
- **Description:** Default 3D mesh export format
- **Format Details:**
  - `stl`: Binary, widely supported, no color
  - `ply`: ASCII/Binary, supports color and normals
  - `obj`: ASCII, supports materials, larger files

### `image_format`
- **Type:** String
- **Default:** `tif`
- **Valid Values:** `tif`, `png`, `jpg`
- **Description:** Default image export format
- **Recommendations:**
  - `tif`: Lossless, 16-bit support
  - `png`: Lossless, 8-bit
  - `jpg`: Lossy, smallest files

### `compression_level`
- **Type:** Integer
- **Default:** `6`
- **Valid Range:** 0-9
- **Description:** Compression level for PNG/TIF exports
- **Trade-off:**
  - 0: No compression, fastest
  - 9: Maximum compression, slowest
  - 6: Balanced (recommended)

## Logging Settings

```yaml
logging:
  level: INFO
  max_file_size_mb: 10
  backup_count: 5
  console_output: true
```

### `level`
- **Type:** String
- **Default:** `INFO`
- **Valid Values:** `DEBUG`, `INFO`, `WARNING`, `ERROR`
- **Description:** Minimum log level to record
- **Use Cases:**
  - `DEBUG`: Development and troubleshooting
  - `INFO`: Normal operation
  - `WARNING`: Production environments
  - `ERROR`: Minimal logging

### `max_file_size_mb`
- **Type:** Integer
- **Default:** `10`
- **Valid Range:** 1-100 MB
- **Description:** Maximum log file size before rotation

### `backup_count`
- **Type:** Integer
- **Default:** `5`
- **Valid Range:** 1-20
- **Description:** Number of rotated log files to keep

### `console_output`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Print logs to console/terminal
- **Use Case:** Disable for GUI-only operation

## Path Settings

```yaml
paths:
  last_directory: ""
  export_directory: ""
```

### `last_directory`
- **Type:** String
- **Default:** `""` (empty)
- **Description:** Last opened CT scan directory
- **Note:** Automatically updated by application

### `export_directory`
- **Type:** String
- **Default:** `""` (empty)
- **Description:** Default export directory
- **Note:** Automatically updated on export

## Advanced Configuration

### Configuration Priority

1. Command-line arguments (future feature)
2. User settings file (`~/.config/CTHarvester/settings.yaml`)
3. Default settings file (`config/settings.yaml`)

### Resetting to Defaults

To reset all settings:
1. Delete the user settings file
2. Restart CTHarvester
3. New settings file will be created with defaults

**Linux/macOS:**
```bash
rm ~/.config/CTHarvester/settings.yaml
```

**Windows:**
```powershell
del %APPDATA%\CTHarvester\settings.yaml
```

### Environment-Specific Configuration

For different workflows, maintain multiple configuration files:

```bash
# Development configuration
cp config/settings.yaml config/settings.dev.yaml

# Production configuration
cp config/settings.yaml config/settings.prod.yaml

# Copy desired config to user location
cp config/settings.dev.yaml ~/.config/CTHarvester/settings.yaml
```

### Validation

Settings are validated on load:
- Invalid values → fallback to defaults
- Missing keys → use defaults
- Type mismatches → logged as warnings

## Performance Tuning

### For Large Datasets (>1000 images)

```yaml
thumbnails:
  max_size: 256  # Reduce for faster previews
  sample_size: 50  # Increase for better ETA
  max_level: 8

processing:
  threads: auto
  use_rust_module: true  # If available
```

### For High-Quality Previews

```yaml
thumbnails:
  max_size: 1024  # Higher quality
  compression: true
  format: tif

rendering:
  anti_aliasing: true
  default_threshold: 100  # Adjust per dataset
```

### For Low-Memory Systems

```yaml
thumbnails:
  max_size: 256
  max_level: 6

processing:
  threads: 2  # Reduce parallelism
  memory_limit_gb: 2
```

## Troubleshooting

### Settings Not Persisting

- Check `auto_save_settings: true`
- Verify write permissions on settings directory
- Check logs for I/O errors

### Poor Performance

- Increase `sample_size` for better ETA
- Try `use_rust_module: true`
- Reduce `threads` if I/O bound
- Decrease `max_size` for faster previews

### High Memory Usage

- Reduce `max_size`
- Decrease `max_level`
- Lower `threads` count

## See Also

- [Installation Guide](installation.rst) - Setup and dependencies
- [User Guide](usage.rst) - Application usage
- [API Documentation](https://jikhanjung.github.io/CTHarvester/) - Developer reference
