# Rust vs Python: I/O 전략 비교

날짜: 2025-09-30
작성자: Performance Analysis

## 핵심 발견

Rust 버전이 빠른 이유는 **멀티스레딩 자체가 아니라 I/O와 CPU 작업의 분리**에 있음.

## Rust의 전략: 순차 I/O + 병렬 CPU ✅

### 코드 구조 (src/lib_final.rs:277-353)

```rust
// 파일 읽기/쓰기는 순차적으로
for pair_idx in from..to {
    // 디스크 I/O: 순차 (1개씩)
    let depth0 = read_luma_preserve_depth(&file0)?;
    let depth1 = read_luma_preserve_depth(&file1)?;

    // CPU 작업: 병렬 (Rayon의 par_chunks_mut)
    downscale_half_u16(&buf0, sw, sh, &mut d0);
    avg_two_u16_inplace(&mut d0, &d1);

    // 디스크 I/O: 순차 (1개씩)
    write_tiff_preserve_depth(&out_path, ...)?;
}
```

### 세밀한 병렬화 (라인 93, 113)

```rust
fn downscale_half_u16(src: &[u16], sw: usize, sh: usize, dst: &mut [u16]) {
    dst.par_chunks_mut(dw).enumerate().for_each(|(y, row)| {
        // ↑ 이미지의 각 행(row)을 병렬 처리
        // 파일 I/O는 이미 완료된 상태
    });
}
```

### 병렬화 레벨

```
파일 읽기:     순차 (디스크 경합 없음)
이미지 처리:   병렬 (행 단위 멀티스레드, GIL 없음)
파일 쓰기:     순차 (디스크 경합 없음)
```

### 디스크 접근 패턴

```
파일1 → 파일2 → [CPU 병렬] → 저장 → 파일3 → 파일4 → [CPU 병렬] → 저장
순차 ─────────────────────────── 순차 ───────────────────────────
```

**결과**:
- Seek time 최소
- OS 캐시 prefetch 효과적
- 2-3분 (3000 이미지)

## Python 멀티스레드의 문제: 병렬 I/O 시도 ❌

### 코드 구조 (CTHarvester.py)

```python
# 여러 워커가 동시에 시작
for idx in range(num_images):
    worker = ThumbnailWorker(idx, ...)
    threadpool.start(worker)  # 여러 스레드 동시 실행

# 각 워커 내부
def run(self):
    img1 = Image.open(file1)  # 여러 스레드가 동시 실행
    img2 = Image.open(file2)  # 디스크 경합 발생!
    # CPU 작업도 GIL 때문에 직렬화됨
```

### 디스크 접근 패턴

```
Thread 1: [파일1] ──────────
Thread 2:      [파일3] ──────────  ← 디스크 헤드 점프 (HDD)
Thread 3:           [파일5] ──────────  ← 디스크 헤드 점프
Thread 4:                [파일7] ──────────  ← 디스크 헤드 점프
          랜덤 액세스 → Seek time 폭증
```

**결과**:
- 랜덤 액세스로 Seek time 10-100배 증가
- GIL 때문에 CPU 작업도 병렬화 안 됨
- PIL 내부 락 경합
- 평균 6-7분, 최악 30-40분 (예측 불가능)

## Python 단일 스레드: 안정적 ✅

### 접근 방식

```python
# 순차적으로 하나씩 처리
for idx in range(num_images):
    img1 = Image.open(file1)  # 순차
    img2 = Image.open(file2)  # 순차
    # CPU 작업 (GIL로 인해 어차피 단일 코어)
    # 저장 (순차)
```

**결과**:
- 순차 접근으로 Seek time 최소
- 락 경합 없음
- 안정적으로 9-10분

## 성능 비교

| 구현 | 디스크 I/O | CPU 작업 | 시간 | 안정성 |
|------|----------|---------|------|--------|
| Rust | 순차 | 병렬 (GIL 없음) | 2-3분 | ⭐⭐⭐ |
| Python 단일 | 순차 | 순차 (GIL) | 9-10분 | ⭐⭐⭐ |
| Python 멀티 | 병렬 시도 | 순차 (GIL) | 6-40분 | ⭐ |

## 핵심 교훈

### Rust의 성공 비결

1. **I/O는 순차**: 디스크 경합 회피
2. **연산은 병렬**: Rayon으로 행 단위 병렬화
3. **세밀한 제어**: 정확히 어디를 병렬화할지 선택
4. **GIL 없음**: 진정한 CPU 병렬 처리

### Python의 한계

1. **GIL**: CPU 작업 병렬화 불가
2. **조잡한 병렬화**: 작업 단위가 너무 큼 (파일 쌍 전체)
3. **I/O 병렬화 시도**: 디스크 경합으로 역효과

### 올바른 전략

```
Rust:
├─ 디스크 I/O: 순차 처리
└─ 이미지 연산: 행 단위 병렬 처리 ✅

Python 멀티스레드 (잘못된 접근):
├─ 디스크 I/O: 병렬 시도 → 경합 발생 ❌
└─ 이미지 연산: 병렬 시도 → GIL로 실패 ❌

Python 단일스레드 (올바른 접근):
├─ 디스크 I/O: 순차 처리 ✅
└─ 이미지 연산: 순차 처리 (GIL 때문에 어차피 순차) ✅
```

## 결론

**Rust가 빠른 이유는 멀티스레딩이 아니라**:
- 디스크 I/O는 순차로 유지 (경합 없음)
- 이미지 처리만 세밀하게 병렬화 (GIL 없음)

**Python 멀티스레드가 느린 이유**:
- I/O를 병렬화해서 디스크 경합 발생
- CPU는 GIL 때문에 병렬화 안 됨
- "최악의 조합"

**Python 단일스레드가 최선인 이유**:
- I/O 순차 처리로 디스크 최적화
- GIL 때문에 CPU는 어차피 순차
- 락 경합 없어 안정적
- "가능한 최선"

이것이 Python 폴백에서 단일 스레드를 선택한 진짜 이유입니다.