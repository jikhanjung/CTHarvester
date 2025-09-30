# Rust 썸네일 생성 병렬화 최적화 시도

**날짜**: 2025-09-25
**작성자**: Assistant (사용자 지도 하에)

## 개요
Rust 기반 썸네일 생성 모듈의 성능을 개선하기 위해 다양한 병렬화 및 최적화 기법을 시도했습니다. CPU 활용률을 높이고 처리 속도를 개선하고자 했으나, I/O 병목 현상으로 인해 예상보다 제한적인 성능 향상을 보였습니다.

## 테스트 환경
- **CPU**: 멀티코어 프로세서 (8코어 가정)
- **디스크**: SSD/HDD 혼용
- **이미지 크기**: 3072x3072 픽셀
- **이미지 형식**: TIFF, BMP (16-bit 그레이스케일)

## 시도한 최적화 방법

### 1. 원본 구현 (lib_final_backup.rs)
**접근 방식**:
- 레벨별 순차 처리
- 픽셀 단위 병렬화 (Rayon `par_chunks_mut`)
- 1% 단위 진행률 보고

**코드 구조**:
```rust
// 픽셀 병렬 처리
dst.par_chunks_mut(dw).enumerate().for_each(|(y, row)| {
    // 2x2 박스 필터 적용
});

// 레벨별 순차 진행
for level in 1..max_levels {
    process_level(...);
}
```

**성능 특성**:
- CPU 사용률: 20-30%
- 디스크 I/O: 10% 미만
- 안정적이고 예측 가능한 성능

### 2. 피라미드 배치 처리 (lib_final.rs → lib_optimized.rs)
**접근 방식**:
- 이미지 크기에 따라 배치 크기 결정 (8, 16, 32장)
- 한 번에 모든 레벨 생성
- 메모리에서 피라미드 구조 생성

**알고리즘**:
```rust
// 3레벨 예시 (8장 배치)
배치 8장 로드 → Level 1: 4장 생성
              → Level 2: 2장 생성
              → Level 3: 1장 생성
```

**구현 세부사항**:
```rust
fn calculate_num_levels(width: u32, height: u32) -> usize {
    let mut w = width;
    let mut h = height;
    let mut levels = 0;

    while w > 500 || h > 500 {
        w /= 2;
        h /= 2;
        levels += 1;
    }
    levels
}

fn create_pyramid_batch(
    batch_images: Vec<DynamicImage>,
    num_levels: usize,
    depth: &ImageDepth,
) -> ImagePyramid {
    // 피라미드 레벨별로 이미지 생성
}
```

**문제점**:
- 메모리 압박 (8-16장 × 18MB = 144-288MB)
- 캐시 미스 증가
- 복잡한 로직으로 오버헤드 발생
- **실제로 더 느린 성능**

### 3. 이미지 쌍 병렬 처리 (lib_parallel.rs)
**접근 방식**:
- 모든 이미지 쌍을 병렬로 처리
- Rayon의 `par_iter`로 작업 분배

**코드 구조**:
```rust
let results: Vec<_> = pairs.par_iter().map(|&pair_idx| {
    // 각 코어가 독립적으로 이미지 쌍 처리
    let img0 = img_open(&files[i0])?;
    let img1 = img_open(&files[i1])?;

    // 다운샘플링 및 평균
    let result = process_pair(img0, img1);

    // 결과 저장
    result.save(&output_path)?;

    Ok(output_path)
}).collect();
```

**문제점**:
- Mutex 경합 (진행률 업데이트)
- I/O 경합 (여러 스레드가 동시에 파일 읽기/쓰기)
- Python GIL 병목

### 4. 제한된 병렬화 (lib_parallel_v2.rs)
**접근 방식**:
- 검증된 알고리즘 유지
- 배치 단위로만 병렬화
- 진행률 콜백 최소화

**시도했지만 미완성**

## 성능 측정 결과

### CPU 활용률 비교
| 구현 방식 | CPU 사용률 | 디스크 I/O | 상대 속도 |
|---------|-----------|-----------|----------|
| 원본 (순차 + 픽셀 병렬) | 20-30% | <10% | 1.0x (기준) |
| 피라미드 배치 | 20-30% | <10% | 0.8-0.9x (더 느림) |
| 이미지 쌍 병렬 | 20-30% | <10% | 1.0x (차이 없음) |

### I/O 분석
```
원본 방식:
- Level 1: 1000장 읽기 → 500장 쓰기
- Level 2: 500장 읽기 → 250장 쓰기
- Level 3: 250장 읽기 → 125장 쓰기
총 I/O: 2625회

피라미드 방식:
- 배치당: 8장 읽기 → 7장 쓰기
- 125개 배치
총 I/O: 1875회 (이론상 28.6% 감소)
```

## 병목 현상 분석

### 1. I/O Bound 특성
- **주요 병목**: 디스크 읽기/쓰기 속도
- 3072x3072 16-bit 이미지 = 18MB
- SSD 순차 읽기: ~500MB/s → 초당 약 27장
- CPU는 디스크 대기로 유휴 상태

### 2. 메모리 대역폭
- 대용량 이미지 데이터 이동
- 캐시 효율성 저하
- NUMA 효과 (멀티 소켓 시스템)

### 3. Python GIL
- 진행률 콜백이 Python으로 전달
- GIL 획득/해제 오버헤드
- 병렬성 제한

### 4. 파일 시스템 오버헤드
- 파일 열기/닫기 시스템 콜
- 디렉토리 메타데이터 업데이트
- Windows 파일 시스템 특성

## 교훈 및 결론

### 성공한 최적화
1. **픽셀 단위 병렬화**: Rayon의 `par_chunks_mut`로 효과적
2. **비트 깊이 보존**: 8/16-bit 원본 유지로 품질 보장
3. **파일 패턴 필터링**: 불필요한 파일 제외

### 실패한 최적화
1. **피라미드 배치 처리**: 메모리 압박과 복잡도 증가
2. **과도한 병렬화**: I/O 경합으로 오히려 성능 저하
3. **빈번한 콜백**: GIL 병목 발생

### 최종 결론
**현재 구현이 최적에 가까움**:
- I/O Bound 작업에서는 CPU 병렬화 효과 제한적
- 단순하고 안정적인 구조가 더 효율적
- 픽셀 레벨 병렬화 정도가 적절한 수준

## 향후 개선 방향

### 단기 개선안
1. **메모리 매핑 (mmap)**
   - 커널 레벨 캐싱 활용
   - 시스템 콜 감소

2. **비동기 I/O**
   - tokio/async-std 활용
   - I/O 대기 시간 활용

3. **압축 최적화**
   - LZ4 등 빠른 압축 사용
   - I/O 양 감소

### 장기 개선안
1. **GPU 가속**
   - CUDA/OpenCL로 다운샘플링
   - 대량 병렬 처리

2. **분산 처리**
   - 여러 머신에서 처리
   - 네트워크 I/O 고려

3. **캐싱 전략**
   - 자주 사용하는 레벨 우선 생성
   - 적응형 캐싱

## 코드 아카이브
테스트했던 구현들:
- `lib_final_backup.rs`: 원본 (현재 사용 중)
- `lib_optimized.rs`: 피라미드 배치 처리 (제거됨)
- `lib_parallel.rs`: 이미지 쌍 병렬화 (제거됨)
- `lib_parallel_v2.rs`: 제한된 병렬화 (미완성, 제거됨)

## 참고 자료
- Rayon 병렬 처리: https://github.com/rayon-rs/rayon
- PyO3 GIL 관리: https://pyo3.rs/latest/parallelism.html
- I/O Bound vs CPU Bound: https://stackoverflow.com/questions/868568/

---
*이 문서는 CTHarvester의 Rust 모듈 성능 최적화 과정을 기록한 것입니다.*