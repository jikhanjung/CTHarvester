# GitHub Pages 설정 가이드

CTHarvester 프로젝트의 Sphinx 문서를 GitHub Pages에 자동으로 배포하는 방법입니다.

## 1. GitHub Repository 설정

### Step 1: GitHub Pages 활성화

1. GitHub 저장소 페이지로 이동
2. **Settings** 탭 클릭
3. 왼쪽 메뉴에서 **Pages** 클릭
4. **Source** 섹션에서:
   - Source: **GitHub Actions** 선택

   ![GitHub Pages Settings](https://docs.github.com/assets/cb-47267/mw-1440/images/help/pages/publishing-source-drop-down.webp)

### Step 2: Workflow 권한 설정

1. **Settings** → **Actions** → **General**
2. **Workflow permissions** 섹션에서:
   - ✅ **Read and write permissions** 선택
   - ✅ **Allow GitHub Actions to create and approve pull requests** 체크

## 2. 자동 배포 Workflow

`.github/workflows/docs.yml` 파일이 이미 생성되어 있습니다. 이 workflow는:

- `main` 브랜치에 `docs/` 폴더가 변경되면 자동 실행
- Sphinx 문서를 빌드
- GitHub Pages에 자동 배포

### Workflow 트리거 조건

```yaml
on:
  push:
    branches:
      - main
    paths:
      - 'docs/**'              # docs 폴더 변경 시
      - '.github/workflows/docs.yml'  # workflow 자체 변경 시
  workflow_dispatch:           # 수동 실행 가능
```

## 3. 문서 업데이트 워크플로우

### 자동 배포 (권장)

```bash
# 1. 문서 수정
vim docs/user_guide.rst

# 2. 로컬에서 빌드 테스트
cd docs
make clean
make html

# 3. 브라우저에서 확인
open _build/html/index.html

# 4. Git에 커밋 & 푸시
git add docs/
git commit -m "docs: Update user guide"
git push origin main

# → GitHub Actions가 자동으로 빌드 & 배포
```

### 수동 배포

GitHub 웹사이트에서:
1. **Actions** 탭 이동
2. **Build and Deploy Documentation** workflow 선택
3. **Run workflow** 버튼 클릭
4. **main** 브랜치 선택
5. **Run workflow** 클릭

## 4. 배포 확인

### 배포 URL

문서가 배포되면 다음 URL에서 접근 가능:

```
https://<username>.github.io/<repository>/
```

예시:
```
https://jikhanjung.github.io/CTHarvester/
```

### 배포 상태 확인

1. **Actions** 탭에서 workflow 실행 상태 확인
2. 녹색 체크마크: 성공 ✅
3. 빨간 X: 실패 ❌ (로그 확인 필요)

### 배포 시간

- 일반적으로 1-2분 소요
- 첫 배포는 5-10분 소요 가능

## 5. 로컬 문서 빌드

GitHub Pages에 푸시하기 전에 로컬에서 테스트:

```bash
# 의존성 설치 (최초 1회)
pip install sphinx sphinx-rtd-theme

# 문서 빌드
cd docs
make clean
make html

# 브라우저에서 열기
# Linux/Mac:
open _build/html/index.html

# Windows:
start _build/html/index.html
```

## 6. 문서 구조

```
docs/
├── conf.py              # Sphinx 설정
├── index.rst            # 메인 페이지
├── installation.rst     # 설치 가이드
├── user_guide.rst       # 사용자 가이드
├── developer_guide.rst  # 개발자 가이드
├── changelog.rst        # 변경 이력
└── api/                 # API 문서
    ├── index.rst
    ├── core.rst
    ├── ui.rst
    └── utils.rst
```

## 7. 버전 관리

문서 버전은 `docs/conf.py`에서 관리:

```python
# docs/conf.py
release = '0.2.3'  # 현재 버전
```

버전 업데이트 시:
1. `docs/conf.py`의 `release` 변수 수정
2. `docs/changelog.rst`에 변경 사항 추가
3. 커밋 & 푸시

## 8. 커스텀 도메인 (선택사항)

커스텀 도메인 사용 시:

1. GitHub Pages 설정에서 **Custom domain** 입력
2. `docs/` 폴더에 `CNAME` 파일 생성:
   ```bash
   echo "docs.ctharvester.com" > docs/CNAME
   ```
3. DNS 설정에서 CNAME 레코드 추가:
   ```
   docs.ctharvester.com → <username>.github.io
   ```

## 9. 트러블슈팅

### 문서가 업데이트되지 않는 경우

1. **캐시 문제**: 브라우저 캐시 삭제 (Ctrl+Shift+R)
2. **Workflow 실패**: Actions 탭에서 로그 확인
3. **권한 문제**: Settings → Actions → Workflow permissions 확인

### 빌드 에러

```bash
# 로컬에서 에러 확인
cd docs
make clean
make html

# 의존성 문제 시
pip install --upgrade sphinx sphinx-rtd-theme
```

### 404 에러

1. GitHub Pages Source가 "GitHub Actions"로 설정되었는지 확인
2. Workflow가 성공적으로 실행되었는지 확인
3. 5-10분 대기 후 재시도

## 10. 고급 설정

### 다국어 문서

```bash
# locale 폴더 생성
sphinx-build -b gettext docs docs/_build/gettext
sphinx-intl update -p docs/_build/gettext -l ko

# conf.py에 언어 설정 추가
locale_dirs = ['locale/']
gettext_compact = False
```

### 테마 커스터마이징

`docs/conf.py`에서 테마 옵션 수정:

```python
html_theme_options = {
    'navigation_depth': 4,
    'collapse_navigation': False,
    'sticky_navigation': True,
}
```

### 자동 API 문서 생성

```bash
# apidoc으로 자동 생성
sphinx-apidoc -o docs/api/ . --force --separate
```

## 참고 자료

- [GitHub Pages 공식 문서](https://docs.github.com/en/pages)
- [Sphinx 공식 문서](https://www.sphinx-doc.org/)
- [Read the Docs 테마](https://sphinx-rtd-theme.readthedocs.io/)
