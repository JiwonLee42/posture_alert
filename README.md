# posture_alert

Windows용 바른자세 알림 앱. 정해진 간격마다 Windows 95 스타일 창으로 그림 가이드를 띄워 "이 자세가 되었나요?"라고 안내합니다.

- [PRD.md](PRD.md) — 기획 문서
- [DEV_GUIDE.md](DEV_GUIDE.md) — 개발 가이드 (Python + PySide6 + PyInstaller)
- [docs/IMAGE_PROMPTS.md](docs/IMAGE_PROMPTS.md) — 픽셀 이미지 생성 프롬프트

## 실행 (Mac / Windows 공통)

```bash
uv sync
```
```bash
uv run posture-alert
```

| 명령 | 설명 |
|---|---|
| `POSTURE_DEBUG=1 uv run posture-alert` | 1분이 1초로 줄어든 빠른 모드 (20초마다 눈 알림, 30초마다 자세 체크 …) |
| `uv run posture-alert --demo posture` | 알림 창을 바로 띄우기 (`eye` / `posture` / `stretch` / `stand`) |
| `uv run pytest` | 테스트 |

Mac에서는 자리 비움·전체 화면·회의 감지가 가짜 구현(`platform/fake.py`)으로 동작합니다. 실제 감지는 Windows에서만 됩니다.

## Windows exe

`main`에 push하면 GitHub Actions가 Windows에서 exe를 빌드합니다. Actions 탭 → 최신 실행 → **posture-alert-windows** 내려받기 → 압축 풀고 `posture-alert.exe` 실행.

## 구조

```
src/posture_alert/
├── engine/     # 순수 로직: 스케줄러, 문구, 동작 데이터 (Qt·Windows 모름)
├── platform/   # 자리 비움·전체 화면·마이크 감지 (windows.py / fake.py)
├── storage/    # SQLite 기록
├── ui/         # Win95 스타일 창 (retro.py, popup.py)
└── assets/     # exercises.json, img/(픽셀 그림), fonts/(픽셀 폰트)
```

## 픽셀 폰트 (선택)

`src/posture_alert/assets/fonts/`에 한글 픽셀 폰트 `Galmuri11.ttf`(OFL 라이선스)를 넣으면 자동으로 적용됩니다. 없으면 맑은 고딕 / Apple SD 고딕으로 표시됩니다.
