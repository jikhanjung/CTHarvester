use image::{DynamicImage, ImageBuffer, ImageReader, Luma};
use natord::compare as natord_compare;
use pyo3::prelude::*;
use pyo3::types::PyModule;
use pyo3::{wrap_pyfunction, Bound};
use rayon::prelude::*;
use std::cmp::min;
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};
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

#[inline]
fn to_luma16(img: DynamicImage) -> ImageBuffer<Luma<u16>, Vec<u16>> {
    img.to_luma16()
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
fn avg_two_u16_inplace(dst: &mut [u16], src: &[u16]) {
    dst.par_iter_mut().zip(src.par_iter()).for_each(|(d, &s)| {
        *d = (((*d as u32 + s as u32) + 1) >> 1) as u16;
    });
}

fn list_slices_sorted(input_dir: &Path) -> Result<Vec<PathBuf>, ThumbError> {
    let mut files: Vec<_> = WalkDir::new(input_dir)
        .min_depth(1)
        .max_depth(1)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| e.file_type().is_file())
        .map(|e| e.path().to_path_buf())
        .collect();

    files.sort_by(|a, b| natord_compare(&a.to_string_lossy(), &b.to_string_lossy()));
    if files.is_empty() {
        return Err(ThumbError::Empty);
    }
    Ok(files)
}

fn read_luma16(path: &Path) -> Result<(usize, usize, Vec<u16>), ThumbError> {
    let img = ImageReader::open(path)?.with_guessed_format()?.decode()?;
    let img16 = to_luma16(img);
    let (w, h) = img16.dimensions();
    Ok((w as usize, h as usize, img16.into_raw()))
}

fn write_tiff_luma16(path: &Path, w: u32, h: u32, buf: &[u16]) -> Result<(), ThumbError> {
    let img = ImageBuffer::<Luma<u16>, _>::from_raw(w, h, buf.to_vec())
        .ok_or_else(|| ThumbError::Dim(w as usize, h as usize, 0, 0))?;
    img.save(path)?;
    Ok(())
}

fn ensure_dir(p: &Path) -> Result<(), ThumbError> {
    fs::create_dir_all(p)?;
    Ok(())
}

fn level_dir(base: &Path, level: usize) -> PathBuf {
    base.join(level.to_string())
}

/// Plan levels for thumbnail generation
/// Returns (max_level, [(pairs_count, weight)...])
fn plan_levels(n0: usize, mut w: usize, mut h: usize) -> (usize, Vec<(usize, f64)>) {
    let mut level = 1usize;
    let mut units: Vec<(usize, f64)> = Vec::new();
    let mut remaining_n = n0;
    let mut weight = 1.0f64;

    loop {
        let pairs = remaining_n / 2;
        if pairs == 0 {
            break;
        }
        units.push((pairs, weight));

        w >>= 1;
        h >>= 1;
        remaining_n = pairs;

        if w <= 500 && h <= 500 {
            break;
        }
        weight *= 0.125;
        level += 1;
    }
    (level, units)
}

fn percent(done_units: f64, total_units: f64) -> f64 {
    if total_units <= 0.0 {
        100.0
    } else {
        (done_units / total_units * 100.0).min(100.0)
    }
}

fn completed_outputs_in_level(dir: &Path) -> usize {
    if !dir.exists() {
        return 0;
    }
    WalkDir::new(dir)
        .min_depth(1)
        .max_depth(1)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| e.file_type().is_file())
        .count()
}

/// Process one level with progress callback
fn process_level_with_callback(
    input_files: &[PathBuf],
    input_w: usize,
    input_h: usize,
    out_dir: &Path,
    start_pair_idx: usize,
    weight: f64,
    total_units: f64,
    done_units: Arc<Mutex<f64>>,
    py_callback: Option<&PyObject>,
) -> Result<usize, ThumbError> {
    ensure_dir(out_dir)?;
    let total_pairs = input_files.len() / 2;
    if total_pairs == 0 {
        return Ok(0);
    }

    let dw = input_w >> 1;
    let dh = input_h >> 1;
    let unit_per_pair = weight;

    let from = min(start_pair_idx, total_pairs);
    let to = total_pairs;

    let mut last_reported_pct = -1.0;

    // Process pairs sequentially for real-time progress updates
    for pair_idx in from..to {
        let pair_i = pair_idx;
        let i0 = pair_i * 2;
        let i1 = i0 + 1;

        let (w0, h0, buf0) = read_luma16(&input_files[i0])?;
        let (w1, h1, buf1) = read_luma16(&input_files[i1])?;

        if w0 != input_w || h0 != input_h || w1 != input_w || h1 != input_h {
            return Err(ThumbError::Dim(input_w, input_h, w0, h0));
        }

        let mut d0 = vec![0u16; dw * dh];
        let mut d1 = vec![0u16; dw * dh];
        downscale_half_u16(&buf0, input_w, input_h, &mut d0);
        downscale_half_u16(&buf1, input_w, input_h, &mut d1);
        avg_two_u16_inplace(&mut d0, &d1);

        let out_name = format!("{:06}.tif", pair_i);
        let out_path = out_dir.join(out_name);
        write_tiff_luma16(&out_path, dw as u32, dh as u32, &d0)?;

        // Update progress after each pair
        let new_done = {
            let mut g = done_units.lock().unwrap();
            *g += unit_per_pair;
            *g
        };

        let pct = percent(new_done, total_units);

        // Call Python callback
        if let Some(cb) = py_callback {
            // Report progress if it changed significantly (> 1%) or is the last item
            // This balances between smooth updates and performance
            if pair_idx == to - 1 || (pct - last_reported_pct).abs() > 1.0 {
                Python::with_gil(|py| {
                    let _ = cb.call1(py, (pct,));
                });
                last_reported_pct = pct;
            }
        }
    }

    Ok(to - from)
}

/// Build thumbnails with multi-level LoD generation
///
/// # Arguments
/// * `input_dir` - Directory containing input images
/// * `py_progress_cb` - Optional Python callback function(percentage: float)
#[pyfunction]
#[pyo3(signature = (input_dir, py_progress_cb=None))]
fn build_thumbnails(
    input_dir: String,
    py_progress_cb: Option<PyObject>,
) -> PyResult<()> {
    let input_dir = PathBuf::from(&input_dir);
    let files = list_slices_sorted(&input_dir).map_err(to_pyerr)?;

    if files.is_empty() {
        if let Some(cb) = &py_progress_cb {
            Python::with_gil(|py| { let _ = cb.call1(py, (100.0_f64,)); });
        }
        return Ok(());
    }

    let (w0, h0, _) = read_luma16(&files[0]).map_err(to_pyerr)?;
    let n0 = files.len();

    let base_out = input_dir.join(".thumbnail");
    ensure_dir(&base_out).map_err(to_pyerr)?;

    let (_max_level, units) = plan_levels(n0, w0, h0);
    let total_units: f64 = units.iter().map(|(pairs, w)| *pairs as f64 * *w).sum();

    if total_units == 0.0 {
        if let Some(cb) = &py_progress_cb {
            Python::with_gil(|py| { let _ = cb.call1(py, (100.0_f64,)); });
        }
        return Ok(());
    }

    let done_units = Arc::new(Mutex::new(0.0_f64));

    // Initial 0% callback
    if let Some(cb) = &py_progress_cb {
        Python::with_gil(|py| { let _ = cb.call1(py, (0.0_f64,)); });
    }

    let mut cur_files = files;
    let mut cur_w = w0;
    let mut cur_h = h0;

    for (level_idx, (pairs_expected, weight)) in units.iter().enumerate() {
        let level_no = level_idx + 1;
        let out_dir = level_dir(&base_out, level_no);
        ensure_dir(&out_dir).map_err(to_pyerr)?;

        // Check for already completed work (resume support)
        let already = completed_outputs_in_level(&out_dir);
        let already_clamped = min(already, *pairs_expected);

        if already_clamped > 0 {
            let mut g = done_units.lock().unwrap();
            *g += (already_clamped as f64) * *weight;
        }

        let remaining = *pairs_expected as isize - already_clamped as isize;
        if remaining <= 0 {
            // Level already complete, move to next
            let next_files = list_slices_sorted(&out_dir).map_err(to_pyerr)?;
            cur_files = next_files;
            cur_w >>= 1;
            cur_h >>= 1;

            if cur_w <= 500 && cur_h <= 500 {
                break;
            }
            continue;
        }

        // Process this level
        process_level_with_callback(
            &cur_files,
            cur_w,
            cur_h,
            &out_dir,
            already_clamped,
            *weight,
            total_units,
            done_units.clone(),
            py_progress_cb.as_ref(),
        )
        .map_err(to_pyerr)?;

        // Prepare for next level
        let next_files = list_slices_sorted(&out_dir).map_err(to_pyerr)?;
        cur_files = next_files;
        cur_w >>= 1;
        cur_h >>= 1;

        if cur_w <= 500 && cur_h <= 500 {
            break;
        }
    }

    // Final 100% callback
    if let Some(cb) = py_progress_cb {
        Python::with_gil(|py| {
            let _ = cb.call1(py, (100.0_f64,));
        });
    }

    Ok(())
}

#[pymodule]
fn ct_thumbnail(_py: Python<'_>, m: &Bound<PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(build_thumbnails, m)?)?;
    Ok(())
}