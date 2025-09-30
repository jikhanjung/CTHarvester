# Settings Dialog 사용 가이드

## 통합 완료

Settings Dialog가 메인 윈도우에 통합되었습니다.

### 접근 방법
메인 윈도우 하단의 **Preferences 버튼** (톱니바퀴 아이콘) 클릭

### Settings Dialog 구성

#### 1. General 탭
- **Language**: Auto (System) / English / 한국어
- **Theme**: Light / Dark (미래 기능)
- **Window**:
  - Remember window position (창 위치 기억)
  - Remember window size (창 크기 기억)

#### 2. Thumbnails 탭
- **Max thumbnail size**: 100-2000 px (기본값: 500)
- **Sample size**: 10-100 (기본값: 20)
  - 썸네일 생성 시 샘플링할 이미지 수
- **Max pyramid level**: 1-20 (기본값: 10)
  - 다단계 썸네일 피라미드 최대 레벨
- **Enable compression**: 썸네일 압축 여부
- **Format**: TIF / PNG

#### 3. Processing 탭
- **Worker threads**: Auto / 1-16
  - Auto는 CPU 코어 수에 맞춰 자동 설정
- **Memory limit**: 1-64 GB (기본값: 4)
  - 이미지 처리 시 사용할 최대 메모리
- **Use high-performance Rust module**:
  - 체크: Rust 모듈 사용 (빠름)
  - 미체크: Python fallback (느리지만 안정적)

#### 4. Rendering 탭
- **Default threshold**: 0-255 (기본값: 128)
  - 3D 메시 생성 시 기본 임계값
- **Enable anti-aliasing**: 3D 뷰 안티앨리어싱
- **Show FPS counter**: 3D 뷰 FPS 표시

#### 5. Advanced 탭
- **Logging**:
  - Log level: DEBUG / INFO / WARNING / ERROR
  - Enable console output: 콘솔 로그 출력 여부
- **Export**:
  - Mesh format: STL / PLY / OBJ
  - Image format: TIF / PNG / JPG
  - Compression level: 0-9

### 주요 기능

#### Import Settings (설정 가져오기)
- YAML 파일로부터 설정 가져오기
- 다른 컴퓨터에서 사용한 설정 복원
- 파일 선택 다이얼로그 → YAML 파일 선택

#### Export Settings (설정 내보내기)
- 현재 설정을 YAML 파일로 저장
- 백업 또는 공유용
- 기본 파일명: `ctharvester_settings.yaml`

#### Reset to Defaults (기본값 복원)
- 모든 설정을 기본값으로 초기화
- 확인 다이얼로그 표시

#### Apply / OK / Cancel
- **Apply**: 설정 저장하고 다이얼로그 유지
- **OK**: 설정 저장하고 다이얼로그 닫기
- **Cancel**: 변경사항 취소하고 닫기

### 설정 파일 위치

#### Windows
```
%APPDATA%\CTHarvester\settings.yaml
```
예: `C:\Users\YourName\AppData\Roaming\CTHarvester\settings.yaml`

#### Linux/Mac
```
~/.config/CTHarvester/settings.yaml
```
예: `/home/yourname/.config/CTHarvester/settings.yaml`

### 기존 PreferencesDialog와의 차이

| 기능 | 기존 Preferences | 새 Settings Dialog |
|------|-----------------|-------------------|
| 항목 수 | 5개 | 25개+ |
| 구성 | 단일 창 | 5개 탭 |
| 저장 방식 | QSettings (플랫폼 의존) | YAML (텍스트) |
| 가져오기/내보내기 | ❌ | ✅ |
| 기본값 복원 | ❌ | ✅ |
| 사용자 편집 | ❌ | ✅ (텍스트 에디터) |
| 버전 관리 | ❌ | ✅ (Git 등) |

### 개발자 노트

#### 설정 추가 방법
1. `config/settings.yaml`에 기본값 추가
2. `ui/dialogs/settings_dialog.py`에 UI 컨트롤 추가
3. `load_settings()` 메서드에 로딩 로직 추가
4. `save_settings()` 메서드에 저장 로직 추가

#### 설정 읽기 (코드)
```python
# 메인 윈도우에서
max_size = self.settings_manager.get('thumbnails.max_size', 500)

# 다른 모듈에서
from utils.settings_manager import SettingsManager
settings = SettingsManager()
use_rust = settings.get('processing.use_rust_module', True)
```

#### 설정 쓰기 (코드)
```python
self.settings_manager.set('thumbnails.max_size', 600)
self.settings_manager.save()
```

### 테스트 방법

1. **기본 동작 테스트**
   - CTHarvester 실행
   - Preferences 버튼 클릭
   - 각 탭의 설정 변경
   - OK 클릭
   - 프로그램 재시작 후 설정 유지 확인

2. **Import/Export 테스트**
   - 설정 변경 후 Export
   - 설정 초기화 (Reset to Defaults)
   - Import로 저장된 설정 복원
   - 설정이 복원되었는지 확인

3. **설정 파일 직접 편집 테스트**
   - 프로그램 종료
   - 설정 파일 위치에서 `settings.yaml` 텍스트 에디터로 열기
   - 값 수정 (예: `thumbnails.max_size: 1000`)
   - 프로그램 실행 후 설정 반영 확인

### 문제 해결

#### 설정이 저장되지 않음
- 설정 파일 경로 확인 (로그 참조)
- 디렉토리 쓰기 권한 확인

#### 설정 파일이 깨짐
- Reset to Defaults로 복구
- 또는 설정 파일 삭제 후 재시작 (자동으로 기본 설정 생성)

#### Import 실패
- YAML 파일 형식 확인
- 필수 키(`application`, `thumbnails`, `processing`) 존재 확인