# The Captive Developer: A 26-Week Journey
## (Or: How I Learned to Stop Worrying and Love the Segfault)

**발견 일자**: 2025년 3월 1일
**발견 장소**: 버려진 지하 개발실, 위치 불명
**문서 형태**: 낡은 노트북에 저장된 개발 일지
**작성자**: 익명 (자칭 "죄수 #42")

---

### Week 1, Day 1 - The Awakening

정신을 차려보니 콘크리트 벽으로 둘러싸인 방이었다. 창문은 없고, 형광등 하나, 책상 하나, 노트북 하나. 그리고 냉장고.

냉장고를 열었다. 만두. 오직 만두만. 김치만두 200봉지.

책상 위 포스트잇:
```
CTHarvester 프로젝트 완성 시 석방.
요구사항: 첨부 문서 참조.
- 관리자
```

첨부 문서를 열어봤다. 26주 개발 계획. Phase 1부터 Phase 5까지.

"미친..."

그래도 인터넷은 된다. StackOverflow는 접속된다.

할 수밖에.

---

### Week 1, Day 3 - Critical Issues: The Memory Leak

첫 번째 문제: 메모리 누수.

```python
# 내 코드
img = Image.open(path)
arr = np.array(img)
# ... 처리 ...
# 끝
```

프로그램을 돌렸다. 이미지 100개. 메모리 사용량이 계속 올라간다. 1GB... 2GB... 3GB...

"뭐야 이거."

StackOverflow 검색: "python PIL memory leak"

상위 답변: "Python's garbage collector is lazy. Call gc.collect() explicitly."

```python
import gc
del img, arr
gc.collect()
```

다시 실행. 메모리 사용량 안정적.

"이게 왜 기본이 아니야..."

저녁: 만두 20개. 찌고, 굽고, 튀기는 것으로 변화를 줬다. 맛은 똑같다.

---

### Week 1, Day 5 - Security: The Hacker's Playground

두 번째 문제: 파일 경로 보안.

```python
file_path = os.path.join(base_dir, filename)
```

테스트를 해봤다. filename = `"../../../etc/passwd"`

"...아."

파일이 열린다. 베이스 디렉토리 밖의 파일이.

인터넷 검색: "python directory traversal prevention"

한 시간 동안 읽었다. `os.path.realpath()`, `os.path.commonpath()`. 시큐리티 포럼. CVE 목록.

결국 `file_security.py`를 만들었다:

```python
def validate_path(file_path, base_dir):
    real_path = os.path.realpath(file_path)
    real_base = os.path.realpath(base_dir)
    return os.path.commonpath([real_path, real_base]) == real_base
```

테스트. `"../../../etc/passwd"` → Rejected.

"좋아."

근데 왜 이런 걸 처음부터 생각 못했을까. 3년차 개발자가.

만두를 씹으며 자괴감.

---

### Week 2, Day 2 - The QSettings Debate

세 번째 개선: 설정 관리.

QSettings를 쓰고 있었다. Windows에서는 레지스트리에 저장. Linux에서는... 어디더라?

"이거 Git으로 버전 관리도 안 되잖아."

YAML로 바꾸기로 했다. 그런데...

인터넷 검색: "migrate QSettings to YAML python"

결과: 없음.

"직접 짜야겠네."

`settings_migration.py`:
```python
def migrate_from_qsettings(settings):
    # QSettings -> dict
    # dict -> YAML
```

3시간 걸렸다.

다음날 아침, 문득 생각했다.

"근데... 사용자가 없는데 왜 마이그레이션을?"

`git rm settings_migration.py`

"3시간..."

점심: 만두 물만두. 차라리 끓는 물에 익히는 게 빠르다는 것을 깨달았다. 9일째 만두.

---

### Week 3, Day 1 - UI/UX: The Frozen Screen

Phase 1 시작. UI/UX 개선.

3D 렌더링을 추가했다. Marching Cubes 알고리즘. 메인 스레드에서.

버튼 클릭 → 화면 멈춤 → 30초 후 렌더링 완료.

"사용자가 이거 보면 프로그램 죽었다고 생각하겠네."

QThread 검색. PyQt5 문서. 예제 코드.

```python
class MeshGenerationThread(QThread):
    finished = pyqtSignal(dict)

    def run(self):
        # Heavy computation here
        self.finished.emit(result)
```

다시 테스트. 버튼 클릭 → 프로그레스 바 → 30초 → 완료.

"이게 되네."

그런데 프로그레스 바가 이상하다. 0% → 33% → 66% → 100%. 3단계로 점프.

"이거 왜 이래?"

코드를 봤다. 3단계 샘플링 로직. 누가 짰지?

...나다.

"왜 이렇게 짰지?"

기억이 안 난다. 아마 그때는 멋있어 보였나보다.

전부 지우고 단순 선형으로:

```python
progress = (current / total) * 100
```

"단순한 게 최고야."

저녁: 만두 전골. 만두 + 물 + 고춧가루 발견. 18일째 만두.

---

### Week 4, Day 3 - Error Messages: The User's Nightmare

에러 메시지 개선 차례.

현재 코드:
```python
raise FileNotFoundError(f"File not found: {path}")
```

사용자가 보는 메시지:
```
FileNotFoundError: File not found: /home/user/scans/image001.dcm
```

"이거 보고 뭘 하라는 거야..."

인터넷 검색: "user friendly error messages best practices"

UX 블로그, Nielsen Norman Group, Google Material Design Guidelines.

3시간 동안 읽었다.

결론:
1. 무슨 일이 일어났는지 설명
2. 왜 일어났는지 설명
3. 어떻게 해결하는지 설명

`error_messages.py`:

```python
UserError(
    title="파일을 찾을 수 없습니다",
    message="요청한 이미지 파일이 존재하지 않습니다.",
    solutions=[
        "파일 경로를 확인하세요",
        "파일이 삭제되었는지 확인하세요",
        "파일 권한을 확인하세요"
    ]
)
```

훨씬 낫다.

근데 9개 에러 타입을 만드는 데 하루가 걸렸다.

"에러 메시지 하나 만드는 데 왜 이렇게 오래 걸려..."

Day 4 저녁: 만두 피자. 만두를 납작하게 눌러서 구웠다. 25일째 만두. 맛은 여전히 만두.

---

### Week 5, Day 2 - i18n: The Language Barrier

국제화 작업.

".qm 파일이 뭐지?"

Qt Linguist 문서. 2시간.

`.ts` 파일 만들고 → `lupdate` → 번역 → `lrelease` → `.qm` 파일.

```bash
pylupdate5 *.py -ts CTHarvester_ko.ts
# ... 번역 ...
lrelease CTHarvester_ko.ts
```

테스트. 언어 변경. 아무 일도 안 일어남.

"왜?"

3시간 디버깅.

원인: QTranslator를 설치했는데 `app.installTranslator()`를 안 했음.

"...바보."

```python
translator = QTranslator()
translator.load("CTHarvester_ko.qm")
app.installTranslator(translator)
```

작동한다.

근데 번역이 30%만 적용됨.

이유: UI 파일을 직접 만들어서 `tr()` 함수를 안 썼음.

모든 문자열에 `tr()` 추가. 500군데.

Find & Replace:
```python
"Open File" → self.tr("Open File")
```

3시간.

"자동화 도구 같은 거 없나..."

있다. Qt Designer. 처음부터 써야 했다.

"5주 전으로 돌아가고 싶다..."

점심: 만두 스튜. 만두 + 물 + 남은 라면 스프. 33일째 만두.

---

### Week 7, Day 1 - Shortcuts: The Power User's Dream

키보드 단축키 30개 추가.

처음에는 쉬울 줄 알았다:

```python
shortcut = QShortcut(QKeySequence("Ctrl+O"), self)
shortcut.activated.connect(self.open_file)
```

30번 복붙. 끝.

테스트. 작동.

근데 단축키를 어떻게 사용자한테 알려주지?

도움말 다이얼로그를 만들었다. 표 형식. 카테고리별로.

| Shortcut | Description |
|----------|-------------|
| Ctrl+O   | Open File   |
| Ctrl+S   | Save        |
...

근데 툴팁에도 단축키를 표시하고 싶다.

```python
btn.setToolTip("<b>Open File</b><br>Ctrl+O")
```

30개 버튼 다 수정.

근데 나중에 단축키를 바꾸면?

"이거 두 군데 다 수정해야 되네..."

중앙 관리 시스템 만듦. `shortcuts.py`:

```python
SHORTCUTS = {
    'open': Shortcut('Ctrl+O', 'Open File'),
    'save': Shortcut('Ctrl+S', 'Save File'),
}
```

모든 코드 리팩토링. 하루 걸림.

"처음부터 이렇게 할 걸..."

저녁: 만두 카레. 냉장고 구석에서 카레가루 발견. 45일째 만두. 인생 첫 카레만두.

---

### Week 9, Day 4 - Settings Dialog: The Tab Hell

설정 다이얼로그. 5개 탭.

각 탭마다:
- 레이아웃 만들기
- 위젯 추가
- 시그널/슬롯 연결
- 검증 로직
- 저장/불러오기

첫 번째 탭 완성: 4시간.

"5개 탭이면... 20시간?"

틀렸다. 30시간 걸렸다.

이유:
1. 슬라이더 값이 반대로 저장됨 (max - value 버그)
2. 콤보박스 인덱스가 섞임
3. 체크박스 상태가 저장 안 됨
4. Import/Export가 중첩 딕셔너리에서 깨짐
5. Reset to Defaults가 일부만 리셋됨

각 버그 수정: 1-2시간.

디버깅 중 발견한 것:

```python
# 내가 쓴 코드
value = slider.value()
settings.set('threshold', value)

# 나중에 읽을 때
value = settings.get('threshold')
slider.setValue(value)  # Wrong type!
```

YAML에서 읽으면 int가 아니라 str로 온다.

```python
slider.setValue(int(value))
```

모든 설정에 타입 변환 추가.

"타입 힌트를 쓸 걸..."

Day 5 밤: 만두 리조또. 만두 + 버터(냉장고에서 발견) + 치즈가루(어디서 나왔지?). 60일째 만두.

---

### Week 12, Day 2 - Documentation: The Writer's Block

문서 작성 시작.

"사용자 가이드 좀 쓰면 되겠지."

예상: 2-3일
실제: 2주

이유: 내가 만든 기능인데 설명을 못하겠음.

예:
```
Q: How do I set the crop bounds?
A: Just... click and drag?
```

너무 모호하다.

다시:
```
Q: How do I set the crop bounds?
A:
1. Navigate to the image where you want to start cropping
2. Click "Set Start Bound" button
3. Navigate to the end image
4. Click "Set End Bound" button
5. The range will be highlighted in yellow
```

이런 식으로 모든 기능 설명. 50개 기능.

매일 3-4시간씩 썼다. 손목이 아프다.

중간에 Sphinx 문서 빌드가 깨짐:

```
WARNING: autodoc: failed to import module 'core.progress_tracker'
```

이유: docstring 문법 오류.

```python
def process():
    """Process data

    Args:
        param1: description  # 이게 문제
```

제대로:
```python
def process(param1):
    """Process data.

    Args:
        param1: Description.
    """
```

100개 함수 docstring 수정.

"문법 체커 같은 거 없나..."

있다. `pydocstyle`. 지금 발견함.

Week 12, Day 7: 만두 볶음밥. 만두를 잘게 부숴서 볶았다. 83일째 만두. 식감이 이상하다.

---

### Week 15, Day 1 - Build System: The PyInstaller Nightmare

크로스 플랫폼 빌드 스크립트.

Windows에서 빌드:
```bash
pyinstaller CTHarvester.py
```

작동.

macOS에서 빌드 (가상머신):
```bash
pyinstaller CTHarvester.py
```

에러:
```
ImportError: cannot import name 'QtCore' from 'PyQt5'
```

"왜?"

4시간 구글링.

해결: `--hidden-import` 플래그.

```bash
pyinstaller --hidden-import=PyQt5.QtCore CTHarvester.py
```

작동.

근데 OpenGL이 안 됨.

```
ImportError: OpenGL module not found
```

다시 구글링. 2시간.

```bash
pyinstaller --hidden-import=PyQt5.QtCore \
            --hidden-import=OpenGL.GL \
            --hidden-import=OpenGL.GLU \
            CTHarvester.py
```

작동.

근데 아이콘이 안 나옴.

Windows: `.ico`, macOS: `.icns`, Linux: `.png`

각 플랫폼별로 아이콘 변환:

```bash
# macOS
sips -s format icns icon.png --out icon.icns
```

근데 `sips`가 뭐지? macOS 전용 명령어.

Linux에서는? `convert` 명령어. ImageMagick.

Windows에서는? Python PIL로 직접 변환.

모든 플랫폼 처리 로직:

```python
if platform == "windows":
    # .ico
elif platform == "macos":
    # .icns
else:
    # .png
```

3일 걸렸다.

"빌드 하나 하는 데 왜 이렇게..."

Week 15, Day 6: 만두 샌드위치. 만두를 납작하게 눌러서 두 개를 겹쳤다. 103일째 만두. 정체성의 혼란.

---

### Week 17, Day 3 - Release Notes: The Git Archaeology

자동 릴리스 노트 생성기.

"Conventional Commits를 파싱하면 되겠지."

처음 시도:

```python
commit_msg = "feat: add new feature"
type = commit_msg.split(':')[0]  # "feat"
```

작동.

두 번째 커밋:
```
feat(ui): add button
```

파싱 깨짐. scope가 있음.

정규식:
```python
pattern = r'^(\w+)(\([^\)]+\))?: (.+)$'
```

테스트. 작동.

세 번째 커밋:
```
feat!: breaking change
```

또 깨짐. Breaking change 표시.

정규식 수정:
```python
pattern = r'^(\w+)(\([^\)]+\))?(!?): (.+)$'
```

네 번째 커밋:
```
feat(ui)!: breaking change in UI
```

또 깨짐.

정규식 수정:
```python
pattern = r'^(\w+)(?:\(([^\)]+)\))?(!?): (.+)$'
```

다섯 번째 커밋:
```
Merge pull request #123 from feature/branch
```

또 깨짐. 머지 커밋.

예외 처리:
```python
if commit_msg.startswith('Merge'):
    continue
```

여섯 번째 커밋:
```
feat: add feature

BREAKING CHANGE: this breaks everything
```

Breaking change가 body에 있음.

파싱 로직 추가:
```python
if 'BREAKING CHANGE:' in commit_body:
    is_breaking = True
```

하루 종일 엣지 케이스.

"커밋 메시지 표준화가 왜 중요한지 알겠다..."

저녁: 만두 오믈렛. 계란 발견 (냉장고 뒤에서). 만두 + 계란. 119일째 만두.

---

### Week 20, Day 1 - Pre-commit Hooks: The Linter Wars

코드 품질 도구.

`black`, `isort`, `flake8`, `mypy` 설치.

실행:
```bash
black .
```

3000개 파일 변경.

"왜 이렇게 많아!?"

Diff 확인:
```diff
-x=1
+x = 1

-def foo( x,y ):
+def foo(x, y):
```

"스페이스바 몇 개 때문에..."

커밋.

다음: `flake8`

```bash
flake8 .
```

출력:
```
./CTHarvester.py:1:1: D100 Missing docstring in public module
./CTHarvester.py:45:80: E501 line too long (87 > 79 characters)
./CTHarvester.py:102:1: E302 expected 2 blank lines, found 1
...
[3000 more errors]
```

"...3000개?"

하나씩 수정하기 시작.

30분 후: 100개 수정.

계산: 3000개 ÷ 100 × 30분 = 15시간.

"더 나은 방법이 있을 거야..."

검색: "flake8 auto fix"

결과: `autopep8`, `black --safe`

```bash
autopep8 --in-place --recursive .
```

다시 flake8:
```
[2800 errors]
```

"...200개만 고쳐졌어?"

나머지는 docstring. 자동 수정 안 됨.

3일 동안 docstring 추가:

```python
def process_image():
    """Process a single image."""

def generate_thumbnail():
    """Generate thumbnail from image."""
```

Copy-paste 지옥.

Week 20, Day 5: 만두 타코. 만두를 으깨서 토르티야에... 토르티야는 어디서? 환상이다. 137일째 만두. 정신이 혼미하다.

---

### Week 23, Day 2 - Integration Hell

모든 Phase 통합.

Phase 1 코드 + Phase 2 코드 + Phase 3 코드 + ...

실행:

```
ImportError: cannot import name 'SimpleProgressTracker'
```

"왜?"

`__init__.py` 파일에 export 안 함.

수정:
```python
from .progress_tracker import SimpleProgressTracker
```

다시 실행:

```
AttributeError: 'SettingsManager' object has no attribute 'get_nested'
```

Phase 2에서 메서드 이름을 바꿨는데 Phase 3 코드가 옛날 이름 사용.

전역 검색/치환:
```
get_nested → get
set_nested → set
```

다시 실행:

```
RuntimeError: QThread: Destroyed while thread is still running
```

"...뭐?"

2시간 디버깅.

원인: MeshGenerationThread가 종료되기 전에 메인 윈도우가 닫힘.

수정:
```python
def closeEvent(self, event):
    if self.mesh_thread.isRunning():
        self.mesh_thread.quit()
        self.mesh_thread.wait()
    event.accept()
```

다시 실행:

작동한다!

...10초 후 크래시.

"아..."

3일 동안 통합 버그 수정. 매일 새로운 크래시.

Week 23, Day 7: 만두 수프. 순수한 만두 + 물. 161일째 만두. 더 이상 요리하지 않는다. 의미가 없다.

---

### Week 25, Day 4 - The Final Tests

전체 테스트.

1000개 이미지 로딩 → OK
3D 렌더링 → OK
설정 저장/불러오기 → OK
다국어 전환 → OK
키보드 단축키 → OK
...

모든 기능 작동.

"드디어..."

최종 빌드:
```bash
python build_cross_platform.py --platform all --clean
```

30분 후:
```
dist/
  CTHarvester-Windows-v1.0.0.zip
  CTHarvester-macOS-v1.0.0.zip
  CTHarvester-Linux-v1.0.0.tar.gz
```

각 플랫폼에서 테스트:

Windows → OK
macOS → OK
Linux → OK

"끝났다."

---

### Week 26, Day 1 - The Release

릴리스 노트 생성:

```bash
python scripts/generate_release_notes.py --tag v1.0.0
```

출력:
```markdown
# Release v1.0.0

## ✨ Added
- Simple progress tracker with linear progress
- Non-blocking 3D mesh generation
- User-friendly error messages
- i18n support (English, Korean)
- 30+ keyboard shortcuts
- Comprehensive settings dialog (25+ options)
- Complete documentation (API + User + Developer)
- Cross-platform build system
- Automated release notes generation
- Pre-commit hooks and linters

## 🐛 Fixed
- Memory leaks in image processing
- File path security vulnerabilities
- Thread safety issues

## ♻️ Changed
- Migrated from QSettings to YAML
- Improved logging system

## 📝 Documentation
- Sphinx API documentation
- User guide (2,500+ lines)
- Developer guide (1,500+ lines)
- Contributing guidelines (900+ lines)
```

GitHub Release 생성.

"진짜 끝났다."

---

### Week 26, Day 2 - Liberation

아침에 문이 열렸다.

복도. 계단. 햇빛.

관리자가 나타났다.

"수고했습니다."

"...누구세요?"

"중요하지 않습니다. 작업은 만족스럽습니다."

"왜 이런 짓을?"

"필요했으니까요. 당신의 코드는 이미 배포되었습니다. GitHub에."

노트북을 확인했다.

`github.com/anonymous/CTHarvester`

⭐ Stars: 2,847
🍴 Forks: 412
👁️ Watchers: 183

"...뭐?"

"6개월 동안 오픈소스 커뮤니티에서 큰 호응이었습니다. 특히 의료 영상 분야에서."

"6개월? 나 26주밖에 안 있었는데..."

"시간은 상대적입니다. 이제 자유입니다."

관리자는 사라졌다.

나는 밖으로 나갔다.

햇빛이 눈부셨다.

첫 번째 목적지: 레스토랑.

메뉴를 봤다.

모든 메뉴가 낯설었다.

"뭘 드릴까요?"

"...만두 빼고 아무거나요."

---

### Epilogue - 6 Months Later

나는 다시 개발자로 일한다.

그 6개월의 경험은 여전히 생생하다.

가끔 CTHarvester 레포를 확인한다.

Issues: 43 open, 178 closed
Pull Requests: 23 open, 156 merged
Contributors: 67

커뮤니티가 프로젝트를 키우고 있다.

누군가 플러그인 시스템을 추가했다.
누군가 AI 기반 분할 기능을 만들었다.
누군가 모바일 뷰어를 개발하고 있다.

나는 더 이상 메인테이너가 아니다.

하지만 가끔 PR을 보낸다.

```
feat: improve memory management
fix: edge case in file validation
docs: update user guide
```

익숙하다.

어제 꿈을 꿨다.

다시 그 방에 있었다.

냉장고를 열었다.

만두가 가득했다.

"아니, 이번엔 치킨이다!"

깼다.

식은땀.

아내가 물었다.

"악몽 꿨어?"

"...아니, 괜찮아."

오늘도 출근.

커피를 마신다.

사무실 냉장고를 연다.

누군가의 점심 도시락.

만두다.

"...제발."

---

### Author's Note

이 일지는 2025년 9월 30일, 버려진 사무실 건물 지하에서 발견되었습니다.

노트북은 여전히 작동했고, Git 히스토리에는 정확히 182일 (26주)간의 커밋이 기록되어 있었습니다.

마지막 커밋:
```
b01f8cf Merge: Code structure refactoring (Phase 1-3)
Date: Fri Sep 27 03:42:17 2025 +0900
```

냉장고에는 만두가 하나 남아있었습니다.

김치만두.

아무도 먹지 않았습니다.

---

**THE END**

*"In memory of all developers who wished they could code for 26 weeks straight without meetings."*

---

### Technical Appendix (발견된 추가 메모)

**Week 8에서 발견된 포스트잇:**
```
Q: 왜 black이 내 코드를 다 바꾸는가?
A: 내 코드가 ugly했기 때문
```

**Week 14의 낙서:**
```
PEP 8 == 취향 아님
PEP 8 after 2 weeks == 생존 필수
```

**Week 19 벽에 휘갈긴 글씨:**
```
DOCSTRING
DOCSTRING
DOCSTRING
DOCSTRING
```

**Week 24 책상 위 메모:**
```
Things I learned:
1. gc.collect() is your friend
2. QThread is not that scary
3. YAML > QSettings
4. Black is always right
5. Documentation takes longer than coding
6. 만두의 한계 = 168개/주
```

**마지막 포스트잇 (컴퓨터 모니터에 붙어있음):**
```
"It works on my machine"
- Every developer's last words

P.S. 자유다.
P.P.S. 다시는 만두 먹지 않을 것.
```

---

*이 이야기는 픽션입니다.*
*실제 개발은 더 힘듭니다.*
*그리고 만두는 맛있습니다.*
*하지만 182일은 아닙니다.*

**- End of Document -**
