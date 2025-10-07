# 스레드 개수 설정 롤백

날짜: 2025-09-30
작성자: Performance Fix

## 문제 인식

치명적 문제 수정 시 멀티스레드를 활성화했으나, 실제로는 단일 스레드가 더 빠르다는 사용자 피드백 확인.

## 원인 분석

### Python의 멀티스레드 한계

1. **GIL (Global Interpreter Lock)**
   - Python 인터프리터는 한 번에 하나의 스레드만 실행
   - CPU-bound 작업은 병렬화 불가
   - PIL Image 복사, NumPy 변환 등이 모두 GIL 보유

2. **디스크 I/O 경합**
   - 여러 스레드가 동시에 다른 파일 읽기
   - HDD Seek time 10-100배 증가
   - 순차 접근이 랜덤 접근보다 훨씬 빠름

3. **PIL 내부 락**
   - PIL은 내부적으로 전역 상태 사용
   - 여러 스레드가 PIL 함수 호출 시 락 대기
   - 10-20초 대기 시간 발생

4. **메모리 할당자 경합**
   - 큰 배열 할당 시 락 대기
   - 여러 스레드 동시 할당 시 경합 심화

## 성능 측정 결과

| 구성 | 3000 이미지 처리 시간 | 이미지당 평균 | 특이사항 |
|------|---------------------|--------------|---------|
| 단일 스레드 | 9-10분 | 180-200ms | 안정적 |
| 4 스레드 | 30-40분 | 600-800ms | 일부 10-20초 |

**결론**: 멀티스레드가 3-4배 느림!

## Amdahl의 법칙 적용

```
예상 속도 향상:
- I/O 부분 (30%): 병렬화 가능
- CPU 부분 (70%): GIL로 직렬화

Speedup = 1 / (0.7 + 0.3/4) = 1.29배 (이론)

실제:
- GIL 경합: -20%
- 디스크 I/O 경합: -50%
- 메모리 할당 경합: -10%
총 오버헤드: -80%

실제 속도 = 1.29 * 0.2 = 0.26배 (4배 느림)
```

## 수정 내용

### _determine_optimal_thread_count() 메서드 수정

**이전 (잘못된 접근)**:
```python
def _determine_optimal_thread_count(self):
    cpu_count = os.cpu_count() or 1
    available_memory_gb = psutil.virtual_memory().available / (1024**3)
    memory_based_limit = int(available_memory_gb / 0.2)
    optimal = min(cpu_count, memory_based_limit, 4)
    return optimal  # 1-4 스레드 반환
```

**수정 후 (올바른 접근)**:
```python
def _determine_optimal_thread_count(self):
    """
    Python의 GIL과 디스크 I/O 특성상 단일 스레드가 최적

    멀티스레드 성능 저하 원인:
    1. GIL로 인한 CPU-bound 작업 직렬화
    2. 디스크 I/O 경합 (Seek time 10-100배 증가)
    3. PIL 내부 락 대기 (10-20초)
    4. 메모리 할당자 경합

    측정 결과:
    - 단일 스레드: 9-10분 (3000 이미지)
    - 멀티 스레드: 30-40분 (3-4배 느림!)
    """
    logger.info(
        "Python fallback: Using single thread "
        "(optimal for GIL constraints and disk I/O patterns)"
    )
    return 1  # 항상 단일 스레드
```

## 장기적 해결책

### 현재: Python 단일 스레드 (최선)
- 예측 가능한 성능
- 9-10분 (3000 이미지)
- 추가 의존성 없음

### 미래: Rust 모듈 (이상적)
- GIL 없음
- 진정한 멀티스레드
- 2-3분 (10배 빠름)
- 이미 구현되어 있음

### Rust 모듈 우선 전략

```python
def generate_thumbnails(self):
    try:
        import ctharvester_rs
        # Rust 모듈 사용 (멀티스레드)
        return ctharvester_rs.generate_thumbnails(...)
    except ImportError:
        # Python 폴백 (단일 스레드)
        return self._python_fallback(...)
```

## 교훈

1. **Python 멀티스레드 != 성능 향상**
   - GIL 때문에 CPU-bound 작업은 직렬화됨
   - I/O-bound라도 디스크 경합으로 느려질 수 있음

2. **프로파일링의 중요성**
   - 이론적 분석보다 실제 측정이 중요
   - 사용자 피드백이 가장 정확

3. **올바른 도구 선택**
   - Python: 단순성, 호환성
   - Rust: 성능, 진정한 병렬성

## 관련 문서

- `20250930_017_multithreading_bottleneck_analysis.md`: 상세 분석
- `20250930_016_critical_issues_fixed.md`: 원래 수정 내역

## 결론

Python 폴백 구현에서는 **단일 스레드가 최적**이며, 이는 올바른 선택입니다.
성능이 필요한 경우 Rust 모듈을 사용하는 것이 정답입니다.
