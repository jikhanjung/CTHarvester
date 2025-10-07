### 제목: VerticalTimeline 기반 슬라이더 통합 계획

- **날짜:** 2025-09-12
- **작성자:** Claude Code
- **관련 이슈:** 단일 슬라이더(현재 slice)와 범위 슬라이더(하단/상단) → 단일 커스텀 위젯으로 통합

### 1. 개요

`vertical_stack_slider.py`의 `VerticalTimeline` 위젯으로 기존의 `QLabeledSlider`(현재 인덱스)와 `QLabeledRangeSlider`(범위)를 하나의 위젯으로 대체한다. UI 복잡도를 낮추고, 드래그/키보드/스냅 등 상호작용을 일관화하는 것이 목적이다.

### 2. 대체 위젯 요약

- **구조:** 세로 트랙 + 세 개의 썸(하단 lower, 현재 current(다이아), 상단 upper)
- **시그널:** `lowerChanged(int)`, `upperChanged(int)`, `currentChanged(int)`, `rangeChanged(int,int)`
- **조작:**
  - 드래그: 각 썸 개별 이동, `Shift` 드래그 시 폭 유지하며 동시 이동
  - 클릭: 빈 영역 클릭 시 현재(current)로 점프
  - 휠/키보드: 단일/페이지 스텝, Home/End, `L`/`U` 단축키(하단/상단=현재로 설정)
- **유틸:** `setRange(min,max)`, `setStep(single,page)`, `setSnapPoints(points,tol)`, `values()`

### 3. 교체 전략

#### 3.1 얇은 래퍼 메서드 추가 (권장)

코드 전반의 위젯 직접 참조를 최소화하기 위해 다음 메서드를 `CTHarvester.py`에 추가한다. 이후 호출부를 이 메서드들로 통일하고, 마지막 단계에서 실제 위젯 교체를 수행한다.

- `get_curr_idx()`: `return self.timeline.values()[1]`
- `get_range()`: `lo, _, hi = self.timeline.values(); return lo, hi`
- `set_curr_idx(v)`: `self.timeline.setCurrent(v)`
- `set_range(lo, hi)`: `self.timeline.setLower(lo); self.timeline.setUpper(hi)`

#### 3.2 위젯 생성 및 레이아웃 배치

- 생성: `self.timeline = VerticalTimeline(0, image_count - 1)`
- 초기화: `setStep(1, 10)`, `setLower(0)`, `setUpper(image_count-1)`, `setCurrent(0)`
- 배치: `self.image_layout.addWidget(self.timeline)` (기존 `self.slider`, `self.range_slider` 자리 대체)

#### 3.3 시그널 연결 및 핸들러 브리지

- 연결: `currentChanged` → `_onTimelineCurrent(int)`, `rangeChanged` → `_onTimelineRange(int,int)`
- `_onTimelineCurrent(v)`:
  - 현재 인덱스 관련 기존 로직(이미지 경로 계산/로드, `set_curr_idx`, `update_curr_slice`) 수행
- `_onTimelineRange(lo, hi)`:
  - 기존 범위 로직(`set_bottom_idx`, `set_top_idx`, `calculate_resize`, `repaint`, `update_3D_view(True)`, `update_status`) 수행

#### 3.4 호출부 치환 포인트

- `self.slider.value()/min()/max()` → `_, curr, _ = self.timeline.values()` 및 `self.timeline`의 min/max 사용
- `self.range_slider.value()` → `lo, _, hi = self.timeline.values()`
- `reset_crop()` → `self.timeline.setLower(self.timeline._min); self.timeline.setUpper(self.timeline._max)`
- `comboLevelIndexChanged()`의 범위/값 설정 → `self.timeline.setRange(...)`, `setLower/Upper/Current(...)`
- `curr_slice_val` 계산: `curr / (self.timeline._max or 1) * scaled_depth`

#### 3.5 마이그레이션 체크리스트

- 레벨 변경 시 `setRange`/`setLower`/`setUpper`/`setCurrent` 일관 호출 확인
- 초기화/리셋 시 범위 전체로 확장되는지 확인
- 3D 뷰 갱신(슬라이스, 바운딩 박스 스케일링) 정상 동작 확인
- 스냅 포인트/키보드/휠 조작 확인

### 4. 코드 개선(VerticalTimeline)

- **Thumb Enum:** `QtCore.QEnum` 대신 `enum.IntEnum` 사용 권장 (PyQt5 호환성)
- **포커스 정책:** 키 입력 처리를 위해 `setFocusPolicy(Qt.StrongFocus)` 지정
- **편의 메서드:** `setValues(lower=None,current=None,upper=None)`, `getRange()`, `setRangeValues(lower,upper)`, `minimum()`, `maximum()` 추가 검토
- **시그널(옵션):** 드래그 종료 시점 구분을 위한 `interactionFinished` 등 추가 검토
- **표시/크기:** 최소 폭 상향 또는 간단한 눈금/라벨 추가 검토 (기존 `QLabeled*` 대비 가독성 보완)
- **스냅 포인트:** 레벨 경계/마커에 맞춰 `setSnapPoints([...], tol)` 활용

### 5. 사용 예시

```python
# 생성 및 초기 설정
self.timeline = VerticalTimeline(0, image_count - 1)
self.timeline.setStep(1, 10)
self.timeline.setLower(0)
self.timeline.setUpper(image_count - 1)
self.timeline.setCurrent(0)

# 시그널 연결
self.timeline.currentChanged.connect(self._onTimelineCurrent)
self.timeline.rangeChanged.connect(self._onTimelineRange)

# 값 읽기
lo, curr, hi = self.timeline.values()
```

### 6. 다음 단계

- 1) `VerticalTimeline`의 Enum/포커스/편의 메서드 보강 → 2) `CTHarvester.py`에 얇은 래퍼 추가 → 3) 호출부 치환 → 4) 기존 슬라이더 제거 및 `VerticalTimeline` 장착 → 5) 동작 검증(레벨 변경/3D 뷰/스냅/키 입력/휠).
