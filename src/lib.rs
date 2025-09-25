use image::{DynamicImage, ImageBuffer, ImageReader, Luma};
use natord::compare as natord_compare;
use parking_lot::Mutex;
use pyo3::prelude::*;
use pyo3::types::PyModule;
use pyo3::{prepare_freethreaded_python, wrap_pyfunction, Bound};
use rayon::prelude::*;
use std::cmp::min;
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::{
    atomic::{AtomicBool, Ordering},
    Arc,
};
use std::thread;
use std::time::Duration;
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
    // (W,H) -> (W/2,H/2) —— 2x2 박스 평균(반올림)
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
    // dst = (dst + src) / 2 (반올림)
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
    println!("Reading image: {:?}", path);
    let img = ImageReader::open(path)?.with_guessed_format()?.decode()?;
    let img16 = to_luma16(img);
    let (w, h) = img16.dimensions();
    println!("Image loaded: {}x{}", w, h);
    Ok((w as usize, h as usize, img16.into_raw()))
}

fn write_tiff_luma16(path: &Path, w: u32, h: u32, buf: &[u16]) -> Result<(), ThumbError> {
    // 무압축 TIF 저장
    let img = ImageBuffer::<Luma<u16>, _>::from_raw(w, h, buf.to_vec())
        .ok_or_else(|| ThumbError::Dim(w as usize, h as usize, 0, 0))?;
    img.save(path)?;
    Ok(())
}

fn ensure_dir(p: &Path) -> Result<(), ThumbError> {
    println!("Creating directory: {:?}", p);
    fs::create_dir_all(p)?;
    println!("Directory created or already exists: {:?}", p);
    Ok(())
}

fn level_dir(base: &Path, level: usize) -> PathBuf {
    base.join(level.to_string())
}

/// 각 레벨 l:
///  - 출력 슬라이스 수 ≈ floor(N0 / 2^l)
///  - 시간 가중치 = (1/8)^(l-1)
///  - (W/2,H/2) ≤ 500이 되는 "그 레벨까지" 포함
fn plan_levels(n0: usize, mut w: usize, mut h: usize) -> (usize, Vec<(usize, f64)>) {
    let mut level = 1usize;
    let mut units: Vec<(usize, f64)> = Vec::new();
    let mut remaining_n = n0;
    let mut weight = 1.0f64; // level1=1.0, 이후 *1/8

    println!("Planning levels: n0={}, w={}, h={}", n0, w, h);

    loop {
        let pairs = remaining_n / 2;
        if pairs == 0 {
            println!("No more pairs to process, stopping at level {}", level);
            break;
        }
        units.push((pairs, weight));
        println!("Level {}: {} pairs, weight={}", level, pairs, weight);

        w >>= 1;
        h >>= 1;
        remaining_n = pairs;

        if w <= 500 && h <= 500 {
            println!("Size limit reached ({}x{}), stopping at level {}", w, h, level);
            break; // 이 레벨까지 수행
        }
        weight *= 0.125;
        level += 1;
    }
    println!("Total levels planned: {}, units: {:?}", level, units);
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

/// 한 레벨 처리 (재개 지원 + 진행률 누적만; 파이썬 콜백 호출은 별도 펌프 스레드)
fn process_level(
    input_files: &[PathBuf],
    input_w: usize,
    input_h: usize,
    out_dir: &Path,
    start_pair_idx: usize,
    progress: &Arc<Mutex<(f64, f64)>>, // (done_units, total_units)
    weight: f64,
) -> Result<usize, ThumbError> {
    println!("process_level: {} files, {}x{}, start_idx={}",
             input_files.len(), input_w, input_h, start_pair_idx);
    ensure_dir(out_dir)?;
    let total_pairs = input_files.len() / 2;
    if total_pairs == 0 {
        println!("No pairs to process");
        return Ok(0);
    }
    let dw = input_w >> 1;
    let dh = input_h >> 1;
    let unit_per_pair = weight;

    let from = min(start_pair_idx, total_pairs);
    let to = total_pairs;

    println!("Processing pairs from {} to {} (total: {})", from, to, total_pairs);

    // 일단 순차 처리로 변경하여 테스트
    for pair_i in from..to {
        println!("Processing pair {}", pair_i);
        let i0 = pair_i * 2;
        let i1 = i0 + 1;

        println!("About to read first image at index {}: {:?}", i0, &input_files[i0]);
        let (w0, h0, buf0) = read_luma16(&input_files[i0])?;
        println!("First image read successfully");
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

        // 진행 단위 누적 (콜백은 펌프 스레드가 담당)
        {
            let mut g = progress.lock();
            g.0 += unit_per_pair;
            println!("Progress updated: {}/{}", g.0, g.1);
        }
    }

    Ok(to - from)
}

#[pyfunction]
#[pyo3(signature = (input_dir, py_progress_cb=None))]
fn build_thumbnails(
    input_dir: String,
    py_progress_cb: Option<PyObject>, // 콜백: cb(percentage: float)
) -> PyResult<()> {
    // Rust가 만든 스레드에서 Python 호출 가능하도록 준비 (중복 호출 OK)
    prepare_freethreaded_python();

    let input_dir = PathBuf::from(&input_dir);
    println!("Input directory: {:?}", input_dir);

    let files = list_slices_sorted(&input_dir).map_err(to_pyerr)?;
    println!("Found {} files", files.len());

    if files.is_empty() {
        println!("No files found, returning");
        if let Some(cb) = &py_progress_cb {
            Python::with_gil(|py| { let _ = cb.bind(py).call1((100.0_f64,)); });
        }
        return Ok(());
    }

    let (w0, h0, _) = read_luma16(&files[0]).map_err(to_pyerr)?;
    println!("First image dimensions: {}x{}", w0, h0);
    let n0 = files.len();

    let base_out = input_dir.join(".thumbnail");
    ensure_dir(&base_out).map_err(to_pyerr)?;

    let (_max_level, units) = plan_levels(n0, w0, h0);
    let total_units: f64 = units.iter().map(|(pairs, w)| *pairs as f64 * *w).sum();

    if total_units == 0.0 {
        if let Some(cb) = &py_progress_cb {
            Python::with_gil(|py| { let _ = cb.bind(py).call1((100.0_f64,)); });
        }
        return Ok(());
    }

    // 진행률 상태 + 콜백 펌프 스레드 준비
    let progress = Arc::new(Mutex::new((0.0_f64, total_units)));
    let stop = Arc::new(AtomicBool::new(false));

    // 시작 시 0% 한 번 보장
    println!("About to call initial callback...");
    if let Some(cb) = &py_progress_cb {
        println!("py_progress_cb is Some, calling with 0%");
        Python::with_gil(|py| {
            let result = cb.bind(py).call1((0.0_f64,));
            match result {
                Ok(_) => println!("Initial callback succeeded"),
                Err(e) => println!("Initial callback failed: {:?}", e),
            }
        });
    } else {
        println!("py_progress_cb is None");
    }

    // 콜백 펌프 스레드 설정
    println!("Setting up pump thread...");
    let pump = if let Some(cb) = py_progress_cb.as_ref() {
        println!("Creating pump thread with callback");
        // Python 객체를 먼저 클론
        Python::with_gil(|py| {
            let cb_clone = cb.clone_ref(py);
            let progress_c = Arc::clone(&progress);
            let stop_c = Arc::clone(&stop);

            Some(thread::spawn(move || {
                println!("Pump thread started");
                let mut iteration = 0;
                let mut last_pct = -1.0;
                loop {
                    iteration += 1;

                    // stop 체크를 loop 시작에서 수행
                    if stop_c.load(Ordering::SeqCst) {
                        println!("Pump thread: stop signal detected at iteration {}", iteration);
                        break;
                    }

                    let (done, total) = {
                        let g = progress_c.lock();
                        (g.0, g.1)
                    };
                    let pct = percent(done, total);

                    // 디버그: 매 iteration마다 상태 출력 (처음 몇 번과 100에 가까울 때)
                    if iteration <= 5 || pct > 95.0 {
                        println!("Pump iteration {}: pct={}, last_pct={}, done={}, total={}, stop={}",
                                 iteration, pct, last_pct, done, total, stop_c.load(Ordering::SeqCst));
                    }

                    // 진행률이 변경되었을 때만 콜백 호출
                    if (pct - last_pct).abs() > 0.01 {
                        Python::with_gil(|py| {
                            let result = cb_clone.bind(py).call1((pct,));
                            if let Err(e) = result {
                                println!("Pump callback error: {:?}", e);
                            } else {
                                println!("Callback called with {}%", pct);
                            }
                        });
                        last_pct = pct;
                    }

                    // 100% 도달 시 종료
                    if pct >= 99.99 {  // 부동소수점 비교를 위해 99.99 사용
                        println!("Pump thread: ~100% reached ({}%), exiting", pct);
                        Python::with_gil(|py| {
                            let _ = cb_clone.bind(py).call1((100.0,));
                        });
                        break;
                    }

                    thread::sleep(Duration::from_millis(50));
                }
                println!("Pump thread exiting (stop signal received)...");
                // 종료 직전 최종 1회
                let (done, total) = {
                    let g = progress_c.lock();
                    (g.0, g.1)
                };
                let pct = percent(done, total);
                Python::with_gil(|py| {
                    let _ = cb_clone.bind(py).call1((pct,));
                });
            }))
        })
    } else {
        println!("No callback provided, skipping pump thread");
        None
    };

    // 레벨별 처리
    let mut cur_files = files.clone();
    let mut cur_w = w0;
    let mut cur_h = h0;

    println!("Starting level processing: {} levels to process", units.len());
    for (level_idx, (pairs_expected, weight)) in units.iter().enumerate() {
        println!("Processing level {} (pairs: {}, weight: {})", level_idx + 1, pairs_expected, weight);
        let level_no = level_idx + 1;
        let out_dir = level_dir(&base_out, level_no);
        ensure_dir(&out_dir).map_err(to_pyerr)?;

        // 재개: 이미 출력된 파일 수만큼 진행률 선반영
        let already = completed_outputs_in_level(&out_dir);
        let already_clamped = min(already, *pairs_expected);
        if already_clamped > 0 {
            let mut g = progress.lock();
            g.0 += (already_clamped as f64) * *weight;
        }

        let remaining = *pairs_expected as isize - already_clamped as isize;
        if remaining <= 0 {
            // 이미 완료된 레벨 → 다음 레벨 입력으로 전환
            let next_files = list_slices_sorted(&out_dir).map_err(to_pyerr)?;
            cur_files = next_files;
            cur_w >>= 1;
            cur_h >>= 1;

            // '그 단계까지' 처리되었으면 종료
            if cur_w <= 500 && cur_h <= 500 {
                break;
            }
            continue;
        }

        // 이번 레벨 처리
        println!("Calling process_level with {} files", cur_files.len());
        let produced = process_level(
            &cur_files,
            cur_w,
            cur_h,
            &out_dir,
            already_clamped,
            &progress,
            *weight,
        );

        match produced {
            Ok(count) => println!("process_level produced {} outputs", count),
            Err(e) => {
                println!("process_level error: {:?}", e);
                return Err(to_pyerr(e));
            }
        }

        // 다음 레벨 입력으로 전환
        let next_files = list_slices_sorted(&out_dir).map_err(to_pyerr)?;
        cur_files = next_files;
        cur_w >>= 1;
        cur_h >>= 1;

        // 방금 레벨을 끝냈으니 종료 체크
        if cur_w <= 500 && cur_h <= 500 {
            break;
        }
    }

    // 펌프 종료 및 동기화
    println!("Signaling pump thread to stop...");
    stop.store(true, Ordering::SeqCst);

    if let Some(h) = pump {
        println!("Waiting for pump thread to join...");
        match h.join() {
            Ok(_) => println!("Pump thread joined successfully"),
            Err(_) => println!("Pump thread join failed"),
        }
    }

    // 최종 100% 보고 보장
    println!("Sending final 100% callback...");
    if let Some(cb) = py_progress_cb {
        Python::with_gil(|py| {
            let _ = cb.bind(py).call1((100.0_f64,));
        });
    }

    println!("build_thumbnails completed");
    Ok(())
}

#[pymodule]
fn ct_thumbnail(_py: Python<'_>, m: &Bound<PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(build_thumbnails, m)?)?;
    Ok(())
}
