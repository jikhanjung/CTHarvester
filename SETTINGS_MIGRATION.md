# Settings Migration Strategy

## QSettings → YAML 마이그레이션

### 배경

CTHarvester는 원래 Qt의 QSettings를 사용했지만, Phase 2에서 YAML 기반 설정 시스템으로 전환했습니다.

### 마이그레이션 전략

#### 1. 자동 일회성 마이그레이션

프로그램 시작 시 `utils/settings_migration.py`가 자동으로 실행됩니다:

```python
# main_window.py __init__에서
migrate_qsettings_to_yaml(self.m_app.settings, self.settings_manager)
```

**마이그레이션 대상 설정**:
- `Remember geometry` → `window.remember_position`
- `Remember directory` → `window.remember_size`
- `Language` → `application.language`
- `Log Level` → `logging.level`
- `Use Rust Thumbnail` → `processing.use_rust_module`

#### 2. 마이그레이션 플래그

한 번 마이그레이션되면 `settings.yaml`에 플래그가 저장됩니다:

```yaml
_migration:
  qsettings_migrated: true
  migrated_at: "2025-09-30T15:30:00"
```

이후 실행 시에는 마이그레이션을 건너뜁니다.

### 설정 시스템 공존 전략

현재 **하이브리드 접근**을 사용합니다:

#### YAML Settings (SettingsManager)
**용도**: 애플리케이션 동작 설정
- Thumbnails 생성 옵션
- Processing 옵션 (스레드, 메모리)
- Rendering 옵션 (임계값, 안티앨리어싱)
- Export 형식
- Logging 레벨

**장점**:
- 사용자가 텍스트 에디터로 수정 가능
- 버전 관리 가능 (Git)
- 플랫폼 독립적
- 가져오기/내보내기 쉬움

#### QSettings (계속 사용)
**용도**: Qt 위젯 상태 (UI 전용)
- 창 위치 (geometry)
- 창 크기
- 스플리터 위치
- 최근 열린 파일 목록
- 탭 상태

**장점**:
- Qt 위젯과 네이티브 통합
- `saveGeometry()` / `restoreGeometry()` 직접 사용
- 바이너리 데이터 저장 가능

### 코드에서 설정 읽기

```python
# YAML 설정 읽기 (애플리케이션 동작)
max_size = self.settings_manager.get('thumbnails.max_size', 500)
use_rust = self.settings_manager.get('processing.use_rust_module', True)

# QSettings 읽기 (UI 상태)
geometry = self.m_app.settings.value("MainWindow geometry")
if geometry:
    self.restoreGeometry(geometry)
```

### 코드에서 설정 쓰기

```python
# YAML 설정 쓰기
self.settings_manager.set('thumbnails.max_size', 600)
self.settings_manager.save()

# QSettings 쓰기 (UI 상태)
self.m_app.settings.setValue("MainWindow geometry", self.saveGeometry())
```

### 마이그레이션 타임라인

1. **Phase 2.1** (완료)
   - YAML 설정 시스템 추가
   - SettingsManager 구현

2. **Phase 2.2** (완료)
   - Settings GUI 다이얼로그
   - 메인 윈도우 통합

3. **Phase 2.3** (현재)
   - QSettings → YAML 마이그레이션
   - 하이브리드 접근 문서화

4. **Future** (선택적)
   - QSettings 완전 제거 (UI 상태도 YAML로)
   - 또는 하이브리드 유지 (권장)

### 기존 사용자 경험

**첫 실행** (기존 QSettings가 있는 경우):
1. 프로그램 시작
2. 자동 마이그레이션 실행
3. 로그: "QSettings migrated to YAML successfully"
4. 기존 설정이 그대로 유지됨
5. `settings.yaml` 파일 생성

**이후 실행**:
1. `settings.yaml` 로딩
2. 마이그레이션 건너뜀
3. 정상 동작

### 개발자 가이드

#### 새 설정 추가 시

**애플리케이션 동작 설정** → YAML 사용
```python
# 1. config/settings.yaml에 기본값 추가
thumbnails:
  new_option: true

# 2. 코드에서 읽기
value = self.settings_manager.get('thumbnails.new_option', True)
```

**UI 상태** → QSettings 사용
```python
# Qt 위젯 상태 저장/복원
self.m_app.settings.setValue("splitter_state", self.splitter.saveState())
self.splitter.restoreState(self.m_app.settings.value("splitter_state"))
```

### 문제 해결

#### 마이그레이션 다시 실행하기
```python
# settings.yaml에서 플래그 제거
_migration:
  qsettings_migrated: false  # true → false로 변경

# 또는 _migration 섹션 전체 삭제
```

#### 설정 충돌 시
1. 프로그램 종료
2. QSettings 삭제:
   - Windows: 레지스트리에서 `HKEY_CURRENT_USER\Software\{COMPANY}\CTHarvester` 제거
   - Linux: `~/.config/{COMPANY}/CTHarvester.conf` 삭제
3. `settings.yaml` 삭제
4. 프로그램 재시작 (기본값으로 시작)

### 모범 사례

✅ **DO**:
- 애플리케이션 로직 설정은 YAML 사용
- UI 상태는 QSettings 사용
- 설정 변경 시 settings_manager.save() 호출

❌ **DON'T**:
- 같은 설정을 QSettings와 YAML에 중복 저장
- UI 상태를 YAML에 저장 (geometry, splitter 등)
- QSettings에 복잡한 구조 저장