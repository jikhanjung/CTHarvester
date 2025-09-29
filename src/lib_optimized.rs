use image::{DynamicImage, ImageBuffer, ImageReader, Luma};
use natord::compare as natord_compare;
use parking_lot::Mutex;
use pyo3::prelude::*;
use pyo3::types::PyModule;
use pyo3::{wrap_pyfunction, Bound};
use rayon::prelude::*;
use std::cmp::min;
use std::collections::HashSet;
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::Arc;
use thiserror::Error;
use walkdir::WalkDir;

#[derive(Error, Debug)]
enum ThumbError {
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
    #[error("Image error: {0}")]
    Img(#[from] image::ImageError),
    #[error("Empty input folder")]
    Empty,
    #[error("Dimension mismatch: expected {0}x{1}, got {2}x{3}")]
    Dim(usize, usize, usize, usize),
}

fn to_pyerr(e: ThumbError) -> PyErr {
    pyo3::exceptions::PyRuntimeError::new_err(e.to_string())
}

// Enum to handle different bit depths
enum ImageDepth {
    Luma8(Vec<u8>),
    Luma16(Vec<u16>),
}

#[inline]
fn to_luma_preserve_depth(img: DynamicImage) -> (ImageDepth, u32, u32) {
    match img {
        // 8-bit images
        DynamicImage::ImageLuma8(gray) => {
            let (w, h) = gray.dimensions();
            (ImageDepth::Luma8(gray.into_raw()), w, h)
        },
        DynamicImage::ImageRgb8(_) => {
            let gray = img.to_luma8();
            let (w, h) = gray.dimensions();
            (ImageDepth::Luma8(gray.into_raw()), w, h)
        },
        DynamicImage::ImageRgba8(_) => {
            let gray = img.to_luma8();
            let (w, h) = gray.dimensions();
            (ImageDepth::Luma8(gray.into_raw()), w, h)
        },
        // 16-bit images
        DynamicImage::ImageLuma16(gray) => {
            let (w, h) = gray.dimensions();
            (ImageDepth::Luma16(gray.into_raw()), w, h)
        },
        DynamicImage::ImageRgb16(_) => {
            let gray = img.to_luma16();
            let (w, h) = gray.dimensions();
            (ImageDepth::Luma16(gray.into_raw()), w, h)
        },
        DynamicImage::ImageRgba16(_) => {
            let gray = img.to_luma16();
            let (w, h) = gray.dimensions();
            (ImageDepth::Luma16(gray.into_raw()), w, h)
        },
        // 32-bit float images - convert to 16-bit
        DynamicImage::ImageRgb32F(_) => {
            let gray = img.to_luma16();
            let (w, h) = gray.dimensions();
            (ImageDepth::Luma16(gray.into_raw()), w, h)
        },
        DynamicImage::ImageRgba32F(_) => {
            let gray = img.to_luma16();
            let (w, h) = gray.dimensions();
            (ImageDepth::Luma16(gray.into_raw()), w, h)
        },
        _ => {
            // Default fallback to 8-bit
            let gray = img.to_luma8();
            let (w, h) = gray.dimensions();
            (ImageDepth::Luma8(gray.into_raw()), w, h)
        }
    }
}

#[inline]
fn downscale_half_u8(src: &[u8], sw: usize, _sh: usize, dst: &mut [u8]) {
    let dw = sw >> 1;
    dst.par_chunks_mut(dw).enumerate().for_each(|(y, row)| {
        let sy0 = y << 1;
        let sy1 = sy0 + 1;
        let base0 = sy0 * sw;
        let base1 = sy1 * sw;
        for x in 0..dw {
            let sx0 = x << 1;
            let sx1 = sx0 + 1;
            let a = src[base0 + sx0] as u32;
            let b = src[base0 + sx1] as u32;
            let c = src[base1 + sx0] as u32;
            let d = src[base1 + sx1] as u32;
            row[x] = ((a + b + c + d + 2) >> 2) as u8;
        }
    });
}

#[inline]
fn downscale_half_u16(src: &[u16], sw: usize, _sh: usize, dst: &mut [u16]) {
    let dw = sw >> 1;
    dst.par_chunks_mut(dw).enumerate().for_each(|(y, row)| {
        let sy0 = y << 1;
        let sy1 = sy0 + 1;
        let base0 = sy0 * sw;
        let base1 = sy1 * sw;
        for x in 0..dw {
            let sx0 = x << 1;
            let sx1 = sx0 + 1;
            let a = src[base0 + sx0] as u32;
            let b = src[base0 + sx1] as u32;
            let c = src[base1 + sx0] as u32;
            let d = src[base1 + sx1] as u32;
            row[x] = ((a + b + c + d + 2) >> 2) as u16;
        }
    });
}

#[inline]
fn avg_slices_u8(slices: &[&[u8]], dst: &mut [u8]) {
    let count = slices.len() as u32;
    dst.par_iter_mut().enumerate().for_each(|(i, d)| {
        let sum: u32 = slices.iter().map(|s| s[i] as u32).sum();
        *d = ((sum + count / 2) / count) as u8;
    });
}

#[inline]
fn avg_slices_u16(slices: &[&[u16]], dst: &mut [u16]) {
    let count = slices.len() as u64;
    dst.par_iter_mut().enumerate().for_each(|(i, d)| {
        let sum: u64 = slices.iter().map(|s| s[i] as u64).sum();
        *d = ((sum + count / 2) / count) as u16;
    });
}

// Calculate how many levels needed based on image size
fn calc_levels_needed(mut w: usize, mut h: usize) -> usize {
    let mut levels = 0;
    while w > 500 || h > 500 {
        w >>= 1;
        h >>= 1;
        levels += 1;
    }
    levels
}

// Get group size based on levels (2^levels)
fn get_group_size(levels: usize) -> usize {
    1 << levels
}

fn list_slices_sorted(input_dir: &Path) -> Result<Vec<PathBuf>, ThumbError> {
    let mut files: Vec<_> = WalkDir::new(input_dir)
        .min_depth(1)
        .max_depth(1)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| e.file_type().is_file())
        .map(|e| e.path().to_path_buf())
        .filter(|p| {
            if let Some(ext) = p.extension() {
                let ext_lower = ext.to_string_lossy().to_lowercase();
                matches!(ext_lower.as_str(), "tif" | "tiff" | "bmp" | "jpg" | "jpeg" | "png")
            } else {
                false
            }
        })
        .collect();

    files.sort_by(|a, b| natord_compare(&a.to_string_lossy(), &b.to_string_lossy()));
    if files.is_empty() {
        return Err(ThumbError::Empty);
    }
    Ok(files)
}

fn read_luma_preserve_depth(path: &Path) -> Result<(usize, usize, ImageDepth), ThumbError> {
    let img = ImageReader::open(path)?.with_guessed_format()?.decode()?;
    let (depth, w, h) = to_luma_preserve_depth(img);
    Ok((w as usize, h as usize, depth))
}

fn write_tiff_preserve_depth(path: &Path, w: u32, h: u32, depth: &ImageDepth) -> Result<(), ThumbError> {
    match depth {
        ImageDepth::Luma8(buf) => {
            let img = ImageBuffer::<Luma<u8>, _>::from_raw(w, h, buf.to_vec())
                .ok_or_else(|| ThumbError::Dim(w as usize, h as usize, 0, 0))?;
            img.save(path)?;
        },
        ImageDepth::Luma16(buf) => {
            let img = ImageBuffer::<Luma<u16>, _>::from_raw(w, h, buf.to_vec())
                .ok_or_else(|| ThumbError::Dim(w as usize, h as usize, 0, 0))?;
            img.save(path)?;
        }
    }
    Ok(())
}

fn ensure_dir(p: &Path) -> Result<(), ThumbError> {
    fs::create_dir_all(p)?;
    Ok(())
}

fn level_dir(base: &Path, level: usize) -> PathBuf {
    base.join(level.to_string())
}

// Collect existing files in each level directory for resume support
fn collect_existing_files(base_out: &Path, max_levels: usize) -> Vec<HashSet<String>> {
    let mut existing = Vec::new();
    for level in 1..=max_levels {
        let dir = level_dir(base_out, level);
        let mut files = HashSet::new();
        if dir.exists() {
            if let Ok(entries) = fs::read_dir(dir) {
                for entry in entries.flatten() {
                    if let Some(name) = entry.file_name().to_str() {
                        if name.ends_with(".tif") || name.ends_with(".tiff") {
                            files.insert(name.to_string());
                        }
                    }
                }
            }
        }
        existing.push(files);
    }
    existing
}

// Process a group of images and generate all levels in memory
fn process_group_all_levels(
    group_files: &[PathBuf],
    group_start_idx: usize,
    input_w: usize,
    input_h: usize,
    levels_needed: usize,
    base_out: &Path,
    existing_files: &[HashSet<String>],
    weight_per_level: &[f64],
    total_units: f64,
    done_units: Arc<Mutex<f64>>,
    py_callback: Option<&PyObject>,
) -> Result<(), ThumbError> {
    if group_files.is_empty() || levels_needed == 0 {
        return Ok(());
    }

    let group_size = group_files.len();

    // Check if all output files for this group already exist
    let mut all_exist = true;
    for level in 1..=levels_needed {
        let pairs_at_level = group_size >> level;
        let has_odd = (group_size >> (level - 1)) & 1 == 1;
        let total_at_level = if has_odd { pairs_at_level + 1 } else { pairs_at_level };

        for pair_idx in 0..total_at_level {
            let global_pair_offset = group_start_idx >> level;
            let global_idx = global_pair_offset + pair_idx;
            let output_name = format!("{:06}.tif", global_idx);

            if !existing_files[level - 1].contains(&output_name) {
                all_exist = false;
                break;
            }
        }

        if !all_exist {
            break;
        }
    }

    // If all thumbnails exist, update progress and skip
    if all_exist {
        // Log that we're skipping this group
        eprintln!("Skipping group starting at index {} - all thumbnails already exist", group_start_idx);

        // Calculate weight for all levels of this group
        let mut group_weight = 0.0;
        for level in 1..=levels_needed {
            group_weight += weight_per_level[level - 1];
        }

        // Update progress
        let mut done = done_units.lock();
        *done += group_weight;
        let pct = (*done / total_units * 100.0).min(100.0);
        drop(done);

        if let Some(cb) = py_callback {
            let should_continue = Python::with_gil(|py| {
                match cb.call1(py, (pct,)) {
                    Ok(result) => {
                        if let Ok(should_continue) = result.extract::<bool>(py) {
                            should_continue
                        } else {
                            true
                        }
                    }
                    Err(_) => true
                }
            });
            if !should_continue {
                return Ok(());  // Early exit on cancellation
            }
        }

        return Ok(()); // Skip this group as all thumbnails exist
    }

    // Read all images in the group
    let mut group_images = Vec::new();
    let mut is_16bit = false;

    for (i, file) in group_files.iter().enumerate() {
        let (w, h, depth) = read_luma_preserve_depth(file)?;
        if w != input_w || h != input_h {
            return Err(ThumbError::Dim(input_w, input_h, w, h));
        }

        // Determine bit depth from first image
        if i == 0 {
            is_16bit = matches!(depth, ImageDepth::Luma16(_));
        }

        // Convert to consistent bit depth if needed
        let converted_depth = match (&depth, is_16bit) {
            (ImageDepth::Luma8(buf), true) => {
                // Convert 8-bit to 16-bit
                let buf16: Vec<u16> = buf.iter().map(|&x| (x as u16) << 8).collect();
                ImageDepth::Luma16(buf16)
            },
            (ImageDepth::Luma16(buf), false) => {
                // Convert 16-bit to 8-bit
                let buf8: Vec<u8> = buf.iter().map(|&x| (x >> 8) as u8).collect();
                ImageDepth::Luma8(buf8)
            },
            _ => depth,
        };

        group_images.push(converted_depth);
    }

    // Process each level
    let mut current_images = group_images;
    let mut current_w = input_w;
    let mut current_h = input_h;
    let mut last_reported_pct = -1.0;

    for level in 1..=levels_needed {
        let level_dir = level_dir(base_out, level);
        ensure_dir(&level_dir)?;

        let pairs_in_level = current_images.len() / 2;
        if pairs_in_level == 0 {
            break;
        }

        let new_w = current_w >> 1;
        let new_h = current_h >> 1;
        let mut next_images = Vec::new();

        // Process pairs in this level

        for pair_idx in 0..pairs_in_level {
            // Check cancellation at the beginning of each pair
            // Report progress frequently to check for cancellation
            if let Some(cb) = py_callback {
                // Calculate current progress
                let current_done = {
                    let g = done_units.lock();
                    *g
                };
                let check_pct = (current_done / total_units * 100.0).min(100.0);
                let should_continue = Python::with_gil(|py| {
                    match cb.call1(py, (check_pct,)) {
                        Ok(result) => {
                            if let Ok(should_continue) = result.extract::<bool>(py) {
                                should_continue
                            } else {
                                true
                            }
                        }
                        Err(_) => true
                    }
                });
                if !should_continue {
                    return Ok(());  // Early exit on cancellation
                }
            }

            // Calculate the actual global pair index for this level
            // At level 1: group starting at image 0 has pairs 0,1,2,3
            //             group starting at image 8 has pairs 4,5,6,7
            // At level 2: group starting at image 0 has pairs 0,1
            //             group starting at image 8 has pairs 2,3
            let global_pair_offset = group_start_idx >> level; // Starting pair index for this group at this level
            let global_idx = global_pair_offset + pair_idx;
            let output_name = format!("{:06}.tif", global_idx);


            // Check if file already exists (resume support)
            if !existing_files[level - 1].contains(&output_name) {
                let i0 = pair_idx * 2;
                let i1 = i0 + 1;

                // Create output buffer and process based on bit depth
                let result = if is_16bit {
                    match (&current_images[i0], &current_images[i1]) {
                        (ImageDepth::Luma16(buf0), ImageDepth::Luma16(buf1)) => {
                            let mut d0 = vec![0u16; new_w * new_h];
                            let mut d1 = vec![0u16; new_w * new_h];
                            downscale_half_u16(buf0, current_w, current_h, &mut d0);
                            downscale_half_u16(buf1, current_w, current_h, &mut d1);

                            // Average the two downscaled images
                            let slices = vec![d0.as_slice(), d1.as_slice()];
                            let mut result = vec![0u16; new_w * new_h];
                            avg_slices_u16(&slices, &mut result);
                            Some(ImageDepth::Luma16(result))
                        },
                        _ => None
                    }
                } else {
                    match (&current_images[i0], &current_images[i1]) {
                        (ImageDepth::Luma8(buf0), ImageDepth::Luma8(buf1)) => {
                            let mut d0 = vec![0u8; new_w * new_h];
                            let mut d1 = vec![0u8; new_w * new_h];
                            downscale_half_u8(buf0, current_w, current_h, &mut d0);
                            downscale_half_u8(buf1, current_w, current_h, &mut d1);

                            // Average the two downscaled images
                            let slices = vec![d0.as_slice(), d1.as_slice()];
                            let mut result = vec![0u8; new_w * new_h];
                            avg_slices_u8(&slices, &mut result);
                            Some(ImageDepth::Luma8(result))
                        },
                        _ => None
                    }
                };

                if let Some(result) = result {
                    // Save the result
                    let output_path = level_dir.join(&output_name);
                    write_tiff_preserve_depth(&output_path, new_w as u32, new_h as u32, &result)?;

                    // Keep for next level processing
                    next_images.push(result);
                }
            } else {
                // File exists, read it for next level processing
                let output_path = level_dir.join(&output_name);
                if output_path.exists() {
                    let (w, h, depth) = read_luma_preserve_depth(&output_path)?;
                    if w == new_w && h == new_h {
                        next_images.push(depth);
                    }
                }
            }

            // Update progress
            let weight = weight_per_level[level - 1];
            let new_done = {
                let mut g = done_units.lock();
                *g += weight;
                *g
            };

            let pct = (new_done / total_units * 100.0).min(100.0);

            // Report progress if significant change
            if let Some(cb) = py_callback {
                if (pct - last_reported_pct).abs() > 1.0 ||
                   (pair_idx == pairs_in_level - 1 && level == levels_needed) {
                    let should_continue = Python::with_gil(|py| {
                        match cb.call1(py, (pct,)) {
                            Ok(result) => {
                                // Check if callback returned False (cancel signal)
                                if let Ok(should_continue) = result.extract::<bool>(py) {
                                    should_continue
                                } else {
                                    // If not a bool, assume continue
                                    true
                                }
                            }
                            Err(_) => true  // Continue on error
                        }
                    });

                    if !should_continue {
                        // User cancelled, exit early
                        return Ok(());
                    }

                    last_reported_pct = pct;
                }
            }
        }

        // Handle odd number of images (remainder)
        if current_images.len() % 2 == 1 {
            // For odd images, just copy the last one to next level with downscaling
            let last_idx = current_images.len() - 1;
            let global_pair_offset = group_start_idx >> level;
            let global_idx = global_pair_offset + pairs_in_level; // Next index after all pairs
            let output_name = format!("{:06}.tif", global_idx);

            if !existing_files[level - 1].contains(&output_name) {
                let result = if is_16bit {
                    match &current_images[last_idx] {
                        ImageDepth::Luma16(buf) => {
                            let mut dst = vec![0u16; new_w * new_h];
                            downscale_half_u16(buf, current_w, current_h, &mut dst);
                            Some(ImageDepth::Luma16(dst))
                        },
                        _ => None
                    }
                } else {
                    match &current_images[last_idx] {
                        ImageDepth::Luma8(buf) => {
                            let mut dst = vec![0u8; new_w * new_h];
                            downscale_half_u8(buf, current_w, current_h, &mut dst);
                            Some(ImageDepth::Luma8(dst))
                        },
                        _ => None
                    }
                };

                if let Some(result) = result {
                    let output_path = level_dir.join(&output_name);
                    write_tiff_preserve_depth(&output_path, new_w as u32, new_h as u32, &result)?;
                    next_images.push(result);
                }
            }
        }

        // Prepare for next level
        current_images = next_images;
        current_w = new_w;
        current_h = new_h;

        // Stop if images are small enough
        if current_w <= 500 && current_h <= 500 {
            break;
        }
    }

    Ok(())
}

/// Build thumbnails with optimized group-based processing
#[pyfunction]
#[pyo3(signature = (input_dir, py_progress_cb=None, prefix=None, file_type=None, seq_begin=None, seq_end=None, index_length=None))]
fn build_thumbnails_optimized(
    input_dir: String,
    py_progress_cb: Option<PyObject>,
    prefix: Option<String>,
    file_type: Option<String>,
    seq_begin: Option<usize>,
    seq_end: Option<usize>,
    index_length: Option<usize>,
) -> PyResult<()> {

    let input_dir = PathBuf::from(&input_dir);

    // Get all image files
    let files = if let (Some(prefix), Some(file_type), Some(seq_begin), Some(seq_end), Some(index_length)) =
        (prefix.as_ref(), file_type.as_ref(), seq_begin, seq_end, index_length) {
        let mut file_list = Vec::new();
        for seq in seq_begin..=seq_end {
            let filename = format!("{}{:0width$}.{}", prefix, seq, file_type, width = index_length);
            let filepath = input_dir.join(&filename);
            if filepath.exists() {
                file_list.push(filepath);
            }
        }
        file_list
    } else {
        list_slices_sorted(&input_dir).map_err(to_pyerr)?
    };

    if files.is_empty() {
        if let Some(cb) = &py_progress_cb {
            Python::with_gil(|py| { let _ = cb.call1(py, (100.0_f64,)); });
        }
        return Ok(());
    }

    // Analyze first image to determine dimensions and levels
    let (w0, h0, _) = read_luma_preserve_depth(&files[0]).map_err(to_pyerr)?;

    let n_files = files.len();

    let levels_needed = calc_levels_needed(w0, h0);

    if levels_needed == 0 {
        if let Some(cb) = &py_progress_cb {
            Python::with_gil(|py| { let _ = cb.call1(py, (100.0_f64,)); });
        }
        return Ok(());
    }

    let group_size = get_group_size(levels_needed);

    let base_out = input_dir.join(".thumbnail");
    ensure_dir(&base_out).map_err(to_pyerr)?;

    // Collect existing files for resume support
    let existing_files = collect_existing_files(&base_out, levels_needed);

    // Calculate weights for progress reporting
    let mut weight_per_level = Vec::new();
    let mut total_units = 0.0;
    let mut weight = 1.0;

    for level in 1..=levels_needed {
        let outputs_in_level = (n_files + (1 << level) - 1) >> level; // ceil(n/2^level)
        let level_weight = weight / outputs_in_level as f64;
        weight_per_level.push(level_weight);
        total_units += outputs_in_level as f64 * level_weight;
        weight *= 0.125;
    }

    let done_units = Arc::new(Mutex::new(0.0));

    // Initial callback
    if let Some(cb) = &py_progress_cb {
        Python::with_gil(|py| { let _ = cb.call1(py, (0.0_f64,)); });
    }

    // Process groups
    let n_groups = (n_files + group_size - 1) / group_size;

    // Process groups sequentially to avoid Python GIL deadlock issues
    // Parallel processing within groups is still enabled

    // Process groups sequentially to avoid Python GIL issues
    // But still use parallelism within each group's processing
    for group_idx in 0..n_groups {
        let group_start = group_idx * group_size;
        let group_end = min(group_start + group_size, n_files);
        let group_files = &files[group_start..group_end];


        process_group_all_levels(
            group_files,
            group_start,
            w0,
            h0,
            levels_needed,
            &base_out,
            &existing_files,
            &weight_per_level,
            total_units,
            done_units.clone(),
            py_progress_cb.as_ref(),
        ).map_err(to_pyerr)?;
    }

    // Final callback
    if let Some(cb) = py_progress_cb {
        Python::with_gil(|py| {
            let _ = cb.call1(py, (100.0_f64,));
        });
    }

    Ok(())
}

// Keep original function for compatibility
#[pyfunction]
#[pyo3(signature = (input_dir, py_progress_cb=None, prefix=None, file_type=None, seq_begin=None, seq_end=None, index_length=None))]
fn build_thumbnails(
    input_dir: String,
    py_progress_cb: Option<PyObject>,
    prefix: Option<String>,
    file_type: Option<String>,
    seq_begin: Option<usize>,
    seq_end: Option<usize>,
    index_length: Option<usize>,
) -> PyResult<()> {
    // Use optimized version by default
    build_thumbnails_optimized(
        input_dir,
        py_progress_cb,
        prefix,
        file_type,
        seq_begin,
        seq_end,
        index_length,
    )
}

#[pymodule]
fn ct_thumbnail(_py: Python<'_>, m: &Bound<PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(build_thumbnails, m)?)?;
    m.add_function(wrap_pyfunction!(build_thumbnails_optimized, m)?)?;
    Ok(())
}