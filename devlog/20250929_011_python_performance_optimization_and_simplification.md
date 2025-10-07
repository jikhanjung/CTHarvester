# Python 썸네일 생성 성능 최적화 및 코드 단순화

날짜: 2025-09-29
작성자: Jikhan Jung

## 문제 상황

Python fallback 썸네일 생성이 예상보다 훨씬 느린 성능을 보이는 문제가 발생했다.

### 초기 측정 결과
- **지난주**: 5분 (4스레드)
- **리부팅 후**: 14분 (4스레드)
- **문제 발생 시**: 25-30분 (성능이 계속 변동)
- **Rust 모듈**: 2-3분 (일관되게 빠름)

## 병목 지점 발견

### 1. 핵심 문제: np.array() 변환
devlog 분석 및 테스트를 통해 병목 지점을 정확히 파악했다:

```python
# PIL의 lazy loading 때문에 발생하는 문제
img = Image.open(filepath)  # 1-2ms (헤더만 읽음)
arr = np.array(img)         # 2000-4000ms! (실제 데이터 로드 + 변환)
```

- **정상 상황**: np.array() 변환이 30-60ms
- **CTHarvester 실행 중**: 2000-4000ms (60-100배 느림!)
- **단독 테스트**: 445ms (전체 썸네일 생성)
- **실제 실행**: 10,000-13,000ms (25-30배 느림)

### 2. 스레드 경쟁 문제
- 4개 스레드가 동시에 8개 파일을 읽으면서 I/O 경쟁 발생
- Python GIL로 인한 진정한 병렬 처리 불가
- 메모리 할당 경쟁 (4스레드 × 30MB = 120MB 동시 할당)

## 해결 과정

### 1단계: 스레드 수 조정 실험
```python
# 여러 스레드 수로 테스트
optimal_thread_count = 1  # 1, 2, 4 테스트
```

결과:
- 1스레드: 25분+ (순차 처리의 한계)
- 2스레드: 18-20분
- 4스레드: 14분 (하지만 불안정)

### 2단계: tifffile 라이브러리 도입
TIFF 파일에 대해 PIL의 lazy loading을 우회:

```python
# 이전: PIL + np.array()
img = Image.open(file_path)      # lazy loading
arr = np.array(img)               # 느린 변환

# 개선: tifffile
arr = tifffile.imread(file_path)  # 직접 NumPy 배열로 읽기
```

**성능 개선**:
- tifffile 로딩: 30-50ms (PIL np.array: 2000-4000ms)
- 전체 시간: 14분 → 9-10분

### 3단계: OpenCV 시도 (BMP/PNG용)
```python
# BMP/PNG 파일용 최적화 시도
if OPENCV_AVAILABLE:
    arr = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)
```

### 4단계: 최종 단순화
복잡한 최적화보다 코드의 단순성과 유지보수성을 선택:

```python
# 최종: PIL + NumPy만 사용
# - 범용성: 모든 이미지 형식 지원
# - 간결성: 외부 라이브러리 최소화
# - 안정성: 단일 스레드, 예측 가능한 동작
```

## 성능 불일치 원인 분석

### 관찰된 현상
동일한 코드가 실행할 때마다 다른 성능을 보임:
- 때로는 5분, 때로는 14분, 때로는 25분+
- np.array() 변환 시간이 30ms에서 4000ms까지 변동

### 가능한 원인들
1. **Windows 파일 시스템 캐싱**
   - 첫 실행: 캐시 없음 → 느림
   - 두 번째 실행: 캐시 활용 → 빠름

2. **시스템 상태**
   - 메모리 파편화
   - Windows Defender 실시간 검사
   - 백그라운드 프로세스 간섭

3. **Python/NumPy 특정 이슈**
   - 특정 환경에서만 발생하는 문제
   - GIL과 Windows I/O의 상호작용

## 최종 구현

### Python Fallback 설계 원칙
1. **단순성 우선**: PIL + NumPy만 사용
2. **단일 스레드**: 예측 가능한 성능
3. **범용성**: 모든 이미지 형식 지원
4. **유지보수성**: 읽기 쉬운 코드

### 코드 구조
```python
# 싱글 스레드 설정
self.threadpool.setMaxThreadCount(1)

# 단순한 이미지 처리
img = Image.open(filepath)
if 16비트:
    arr = np.array(img, dtype=np.uint16)  # NumPy 처리
else:
    ImageChops.add()  # PIL 내장 함수
```

## 결과

### 최종 성능
- **Rust 모듈** (주력): 2-3분
- **Python fallback**: 9-10분 (tifffile 사용 시)
- **Python 순수 PIL**: 25-30분 (하지만 안정적)

### 교훈
1. **과도한 최적화 피하기**: 백업 코드는 단순하게
2. **병목 지점 정확히 파악**: np.array()가 진짜 문제
3. **환경 특수성 인정**: 모든 환경에서 완벽할 수 없음
4. **역할 분담 명확히**: Rust는 빠르게, Python은 읽기 쉽게

## 추가 개선 가능성

### 단기
- PNG 대신 JPEG 저장 (압축 시간 단축)
- 이미지 프리로딩 파이프라인

### 장기
- multiprocessing 사용 (진정한 병렬 처리)
- 메모리 매핑 파일 활용

## 결론

Python fallback은 백업 역할에 충실하도록 단순하게 유지하는 것이 최선이다.
- Rust 모듈이 주력으로 빠른 성능 제공
- Python은 호환성과 디버깅 용이성 제공
- "Perfect is the enemy of good" - 충분히 실용적인 수준 달성

### 핵심 통찰
np.array() 변환이 특정 상황에서 비정상적으로 느려지는 것은 Python/Windows 환경의 특수한 문제로 보인다.
이런 엣지 케이스에 과도하게 대응하기보다는, 코드의 단순성과 유지보수성을 지키는 것이 더 중요하다.
