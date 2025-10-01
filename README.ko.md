# CTHarvester

[![Build](https://github.com/jikhanjung/CTHarvester/actions/workflows/build.yml/badge.svg)](https://github.com/jikhanjung/CTHarvester/actions/workflows/build.yml)
[![Tests](https://github.com/jikhanjung/CTHarvester/actions/workflows/test.yml/badge.svg)](https://github.com/jikhanjung/CTHarvester/actions/workflows/test.yml)
[![Release Status](https://github.com/jikhanjung/CTHarvester/actions/workflows/release.yml/badge.svg)](https://github.com/jikhanjung/CTHarvester/actions/workflows/release.yml)
[![codecov](https://codecov.io/gh/jikhanjung/CTHarvester/branch/main/graph/badge.svg)](https://codecov.io/gh/jikhanjung/CTHarvester)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Tests: 195 passing](https://img.shields.io/badge/tests-195%20passing-brightgreen.svg)](https://github.com/jikhanjung/CTHarvester/tree/main/tests)

*다른 언어로 읽기: [English](README.md), [한국어](README.ko.md)*

메모리 자원이 제한적인 사용자를 위해 설계된 CT(Computed Tomography) 이미지 스택 전처리 도구입니다. CTHarvester는 전체 볼륨을 메모리에 로드하지 않고도 대용량 CT 데이터셋을 효율적으로 크롭하고 리샘플링할 수 있으며, LoD(Level of Detail) 기술을 사용하여 빠른 미리보기와 탐색을 제공합니다.

## 주요 기능

### 메모리 효율적인 처리
- **스마트 크롭핑**: 전체 볼륨을 로드하지 않고 대용량 CT 데이터셋에서 관심 영역만 추출
- **상세 수준(LoD)**: 빠른 미리보기와 탐색을 위한 다중 해상도 피라미드
- **스트리밍 처리**: 메모리 사용을 최소화하기 위해 슬라이스 단위로 CT 스택 처리
- **효율적인 리샘플링**: 저사양 컴퓨터에서 빠른 시각화를 위한 다운샘플링 버전 생성

### 핵심 기능
- **대화형 영역 선택**: 처리 전 시각적으로 크롭 경계 정의
- **실시간 미리보기**: LoD 기술을 사용한 빠른 3D 미리보기
- **다중 레벨 출력**: 여러 해상도 레벨 생성 (1/2, 1/4, 1/8 등)
- **배치 처리**: 멀티스레딩을 통한 효율적인 다중 CT 스택 처리
- **스마트 메모리 관리**: 제한된 RAM 시스템에 최적화

### 시각화 기능
- **3D 렌더링**: LoD 지원 OpenGL 기반 시각화
- **마칭 큐브**: 크롭된 영역에서 3D 메시 모델 생성
- **임계값 제어**: 최적의 시각화를 위한 대화형 임계값 조정
- **역전 모드**: 역밀도 시각화 지원

### 사용자 인터페이스
- **직관적인 GUI**: 네이티브 데스크톱 경험을 위한 PyQt5 기반
- **실시간 피드백**: 조정 및 처리에 대한 즉각적인 피드백
- **다국어 지원**: 한국어 및 영어 지원
- **사용자 설정**: 창 위치 및 작업 디렉토리 기억

## 설치

### Windows 설치 프로그램
[릴리스](https://github.com/jikhanjung/CTHarvester/releases) 페이지에서 최신 설치 프로그램을 다운로드하세요.

### 소스에서 설치

#### 사전 요구사항
- Python 3.12 이상
- pip 패키지 관리자

#### 설치 단계
1. 저장소 클론:
```bash
git clone https://github.com/jikhanjung/CTHarvester.git
cd CTHarvester
```

2. 의존성 설치:
```bash
pip install -r requirements.txt
```

3. 애플리케이션 실행:
```bash
python CTHarvester.py
```

## 사용법

### 기본 작업 흐름

1. **디렉토리 열기**: "Open dir." 클릭하여 CT 이미지 파일이 있는 디렉토리 선택
   - 도구가 자동으로 빠른 탐색을 위한 저해상도 미리보기 생성
2. **LoD로 탐색**: 다중 레벨 미리보기를 사용하여 데이터셋을 빠르게 탐색
3. **크롭 영역 설정**: 
   - "Set Bottom"을 클릭하여 하단 경계 정의
   - "Set Top"을 클릭하여 상단 경계 정의
   - "Reset"을 사용하여 선택 초기화
4. **임계값 조정**: 수직 슬라이더를 사용하여 시각화 미세 조정
5. **처리**: "Resample"을 클릭하여 여러 해상도 레벨 생성
   - 원본 해상도 (크롭된 영역만)
   - 다양한 용도를 위한 1/2, 1/4, 1/8 해상도
6. **저장/내보내기**: 
   - "Save cropped image stack"으로 관심 영역만 저장
   - "Export 3D Model"로 크롭된 데이터에서 메시 생성

### 지원 파일 형식
- **입력**: BMP, JPG, PNG, TIF, TIFF
- **출력**: 입력 형식과 동일
- **3D 내보내기**: STL, PLY, OBJ

### 로그 파일 지원
CTHarvester는 CT 스캐닝 소프트웨어에서 생성된 로그 파일에서 재구성 설정을 자동으로 읽을 수 있습니다.

## 개발

### 소스에서 빌드

#### Windows
```bash
python build.py
```
실행 파일과 설치 프로그램이 모두 생성됩니다.

#### macOS/Linux
```bash
python build.py
```
해당 플랫폼용 실행 파일이 생성됩니다.

### 버전 관리
```bash
# 패치 버전 증가 (0.2.0 -> 0.2.1)
python manage_version.py bump patch

# 마이너 버전 증가 (0.2.0 -> 0.3.0)
python manage_version.py bump minor

# 메이저 버전 증가 (0.2.0 -> 1.0.0)
python manage_version.py bump major
```

### 테스트

CTHarvester는 단위 및 통합 테스트에 걸쳐 포괄적인 테스트 커버리지를 갖추고 있습니다.

#### 테스트 실행
```bash
# 모든 테스트 실행
pytest tests/ -v

# 커버리지 리포트와 함께 실행
pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=html

# 특정 테스트 카테고리 실행
pytest tests/ -v -m unit              # 단위 테스트만
pytest tests/ -v -m integration       # 통합 테스트만
pytest tests/ -v -m "not slow"        # 느린 테스트 제외
```

#### 테스트 구조
- **단위 테스트** (186개): 핵심 유틸리티, 워커, 이미지 처리, 보안
  - `test_common.py` - 유틸리티 함수 (29개 테스트, 100% 커버리지)
  - `test_worker.py` - 워커 스레드 (22개 테스트, 100% 커버리지)
  - `test_image_utils.py` - 이미지 처리 (31개 테스트, 100% 커버리지)
  - `test_progress_manager.py` - 진행률 추적 (28개 테스트, 99% 커버리지)
  - `test_file_utils.py` - 파일 작업 (41개 테스트, 94% 커버리지)
  - `test_security.py` - 보안 검증 (36개 테스트, 90% 커버리지)

- **통합 테스트** (9개): 엔드투엔드 워크플로우
  - `test_integration_thumbnail.py` - 썸네일 생성 파이프라인

#### 커버리지
- **전체**: 핵심 유틸리티 모듈 ~95%
- **100% 모듈**: utils/common, utils/worker, utils/image_utils
- **총계**: 195개 테스트, 모두 통과 ✅

### CI/CD
프로젝트는 지속적 통합 및 배포를 위해 GitHub Actions를 사용합니다:
- **test.yml**: 모든 푸시 및 PR에서 테스트 실행
  - Python 3.12 및 3.13에서 실행
  - 커버리지 리포트 생성
  - Codecov에 업로드
- **build.yml**: main 브랜치에서 개발 빌드 생성
- **release.yml**: 버전 태그에서 릴리스 빌드 생성

## 프로젝트 구조

```
CTHarvester/
├── CTHarvester.py          # 메인 애플리케이션 진입점
├── version.py              # 버전 관리
├── build.py                # 패키징용 빌드 스크립트
├── manage_version.py       # 버전 업데이트 유틸리티
├── requirements.txt        # Python 의존성
├── pytest.ini              # 테스트 설정
│
├── core/                   # 핵심 모듈 (Phase 4 리팩토링에서 추출)
│   ├── progress_manager.py    # 진행률 추적 및 ETA 계산
│   ├── thumbnail_manager.py   # 썸네일 생성 코디네이터
│   └── thumbnail_worker.py    # 썸네일 처리용 워커 스레드
│
├── utils/                  # 유틸리티 모듈
│   ├── common.py              # 공통 유틸리티 함수
│   ├── file_utils.py          # 파일 시스템 작업
│   ├── image_utils.py         # 이미지 처리 유틸리티
│   └── worker.py              # 범용 워커 스레드 베이스
│
├── security/               # 보안 검증
│   └── file_validator.py     # 파일 경로 및 보안 검사
│
├── ui/                     # 사용자 인터페이스 모듈
│   ├── main_window.py         # 메인 애플리케이션 창
│   └── widgets/               # 커스텀 Qt 위젯
│
├── config/                 # 설정
│   └── constants.py           # 애플리케이션 상수
│
├── .github/
│   └── workflows/         # GitHub Actions CI/CD
│       ├── test.yml           # 커버리지를 포함한 테스트 자동화
│       ├── build.yml          # 개발 빌드
│       └── release.yml        # 릴리스 빌드
│
├── tests/                 # 포괄적인 테스트 스위트 (195개 테스트)
│   ├── test_common.py         # 유틸리티 함수 테스트
│   ├── test_worker.py         # 워커 스레드 테스트
│   ├── test_image_utils.py    # 이미지 처리 테스트
│   ├── test_progress_manager.py  # 진행률 추적 테스트
│   ├── test_file_utils.py     # 파일 작업 테스트
│   ├── test_security.py       # 보안 검증 테스트
│   └── test_integration_thumbnail.py  # 통합 테스트
│
├── InnoSetup/             # Windows 설치 프로그램 설정
└── devlog/                # 개발 로그 및 문서
    ├── 20250930_020-025_*.md  # 리팩토링 문서
    ├── 20250930_026-028_*.md  # 테스트 커버리지 문서
    └── ...
```

## 의존성

- **PyQt5**: GUI 프레임워크
- **PyOpenGL**: 3D 렌더링
- **NumPy**: 수치 계산
- **SciPy**: 과학 컴퓨팅
- **Pillow**: 이미지 처리
- **PyMCubes**: 마칭 큐브 구현
- **SuperQt**: 향상된 Qt 위젯

## 기여하기

기여는 언제나 환영합니다! Pull Request를 자유롭게 제출해 주세요.

### 개발 환경 설정

1. 저장소 포크
2. 포크 클론:
   ```bash
   git clone https://github.com/YOUR_USERNAME/CTHarvester.git
   cd CTHarvester
   ```

3. 의존성 설치:
   ```bash
   pip install -r requirements.txt
   pip install pytest pytest-cov pytest-qt  # 테스트용
   ```

4. 기능 브랜치 생성:
   ```bash
   git checkout -b feature/AmazingFeature
   ```

### 개발 워크플로우

1. **변경사항 작성**
   - 기존 코드 스타일과 패턴을 따르세요
   - 새 함수/클래스에 docstring 추가
   - 필요시 테스트 업데이트

2. **테스트 실행**
   ```bash
   pytest tests/ -v
   ```

3. **커버리지 확인**
   ```bash
   pytest tests/ --cov=. --cov-report=term-missing
   ```

4. **변경사항 커밋**
   ```bash
   git commit -m 'Add some AmazingFeature'
   ```

5. **포크에 푸시**
   ```bash
   git push origin feature/AmazingFeature
   ```

6. **Pull Request 열기**
   - 변경사항을 명확하게 설명하세요
   - 관련 이슈를 참조하세요
   - CI 검사가 통과하는지 확인하세요

### 코드 품질 가이드라인

- **테스트**: 새 기능에 대한 테스트 추가
- **커버리지**: 새 모듈에 대해 90% 이상 커버리지 유지
- **문서화**: README 및 docstring 업데이트
- **스타일**: PEP 8 규칙 준수
- **보안**: 파일 작업에 security/file_validator 사용

### 프로젝트 아키텍처

CTHarvester는 Phase 4 리팩토링 이후 모듈식 아키텍처를 따릅니다:
- **core/**: 핵심 비즈니스 로직 (진행률, 썸네일 생성)
- **utils/**: 재사용 가능한 유틸리티 함수
- **security/**: 보안 검증 레이어
- **ui/**: 사용자 인터페이스 컴포넌트
- **tests/**: 포괄적인 테스트 스위트

자세한 리팩토링 및 개발 노트는 `devlog/`를 참조하세요.

## 라이선스

이 프로젝트는 MIT 라이선스 하에 있습니다 - 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 개발자

**정직한**
- GitHub: [@jikhanjung](https://github.com/jikhanjung)

## CTHarvester를 사용해야 하는 이유

기존 CT 처리 소프트웨어는 종종 전체 데이터셋을 메모리에 로드해야 하는데, 이는 다음과 같은 경우에 문제가 됩니다:
- 대용량 CT 스캔 (수 GB 크기)
- 제한된 RAM을 가진 컴퓨터 (8GB 이하)
- 빠른 미리보기 및 영역 선택 작업
- 여러 데이터셋의 배치 처리

CTHarvester는 다음과 같은 방법으로 이러한 문제를 해결합니다:
- 빠르고 메모리 효율적인 미리보기를 위한 상세 수준(LoD) 사용
- 선택된 관심 영역만 처리
- 모든 것을 한 번에 로드하는 대신 슬라이스 단위로 데이터 스트리밍
- 다양한 분석 요구에 맞는 다중 해상도 출력 생성

## 감사의 말

- PaleoBytes 소프트웨어 제품군의 일부
- 3D 메시 생성을 위한 마칭 큐브 알고리즘 사용
- 크로스 플랫폼 호환성을 위해 Qt로 구축
- 메모리 제약 환경을 위해 특별히 설계됨

## 지원

문제, 질문 또는 제안사항은 GitHub에서 [이슈를 열어](https://github.com/jikhanjung/CTHarvester/issues) 주세요.
