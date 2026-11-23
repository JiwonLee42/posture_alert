# 픽셀 이미지 생성 프롬프트

기준 그림: **"기억하자 척추수술 3000만원"** (여성·남성 캐릭터의 ✕ 거북목 / ○ 바른 자세 두 장).
스트레칭·일어나기 동작 그림도 **같은 캐릭터, 같은 구도, 같은 배경**으로 만들어야 알림 창 안에서 자연스럽게 이어집니다.

ChatGPT(이미지 생성), Gemini, Midjourney 어디서든 쓸 수 있게 영어 프롬프트로 정리했어요. 이미지 생성 모델은 영어 프롬프트에서 스타일이 더 안정적이에요.

---

## 1. 만드는 순서 (요약)

1. 이미지 생성 도구에 **이미 만든 목 옆 늘리기 그림을 첨부**해요 (여성이면 여성 그림, 남성이면 남성 그림).
2. 아래 **3장의 [A] 공통 + [B] 캐릭터 + [C] 동작** 프롬프트를 붙여서 요청해요.
   → 기준 그림처럼 **왼쪽 (X) / 오른쪽 (O) 두 칸**짜리 그림이 나와요.
3. 받은 그림을 자르기 스크립트로 잘라 앱에 넣어요:
   ```bash
   uv run --with pillow python tools/crop_pair.py 받은그림.png neck_side f
   ```
   → `assets/img/neck_side_f_bad.png`, `assets/img/neck_side_f_good.png` 가 생겨요.
4. 배경 체크무늬를 진짜 투명으로 바꿔요 (생성 도구는 "투명 배경"을 체크무늬 그림으로 그려 넣는 경우가 많아요):
   ```bash
   uv run --with pillow --with numpy python tools/transparent.py src/posture_alert/assets/img/neck_side_f_*.png
   ```
   가장자리와 이어진 배경 + 책상 밑처럼 갇혀 있어도 체크무늬 두 색이 섞인 넓은 영역만 지워요. 옷·신발의 밝은 색은 남아요.
5. `uv run posture-alert --demo 4`로 확인해요.

### 앱이 그림을 고르는 순서
1. `assets/img/{동작id}_{f|m}_{bad|good}.png` — 동작 + 캐릭터별 그림
2. `assets/img/{동작id}_{bad|good}.png` — 동작별 그림 (캐릭터 공통)
3. `assets/img/default/{f|m}_{bad|good}.png` — 기본 거북목 그림 (지금 들어 있는 것)
4. 임시 픽셀 막대 인형

---

## 2. 그림 현황

| 단계 | 동작 id | 동작 | 여성(f) | 남성(m) |
|---|---|---|---|---|
| 1 | `eye_far` | 먼 곳 보기 | ✅ | ⬜ |
| 2 | `chin_tuck` | 턱 당기기 | ✅ 새 메인 그림 | ✅ 기본 그림 |
| 3 | `shoulder_open` | 어깨 펴기 | ✅ | ⬜ |
| 4 | `neck_side` | 목 옆 늘리기 | ✅ | ✅ |
| 5 | `scapula_squeeze` | 날개뼈 모으기 | ✅ | ✅ |
| 6 | `seat_back` | 의자 위 허리 세우기 | ✅ | ⬜ |
| 7 | `ankle_pump` | 발목 펌프 | ✅ | ⬜ |
| 8 | `stand_water` | 일어나서 물 마시기 | ✅ | ⬜ |
| 대체 | `glute_squeeze` | 엉덩이 힘주기 ("지금 못 일어나요") | ✅ | ⬜ |

---

## 3. 프롬프트 (복사해서 쓰기)

요청 한 번에 **[A] 공통 + [B] 캐릭터 + [C] 동작** 세 덩어리를 순서대로 붙여 넣으세요.
그리고 **이미 만든 목 옆 늘리기 그림(같은 캐릭터)을 첨부**하세요. 구도가 같아야 자르기 상자가 그대로 맞아요.

### [A] 공통 (매번 그대로)

```
Use the attached image as the exact reference for art style, character, layout and framing.
Make a new image in the same format: one wide image split into two panels side by side.
Left panel has "(X)" in red at the upper-left, right panel has "(O)" in green at the upper-left,
exactly where they are in the reference.
Same pixel art style with crisp square pixels, same cream checkered background,
same beige desk with a thin beige monitor and keyboard on the left, same beige office chair,
character in side view facing left, same size and same position as in the reference.
Keep the character's head in the same height area as the reference and the feet near the bottom.
No other text, no title, no speech bubbles, no logo, no watermark, no sparkle mark.
```

### [B] 캐릭터 (하나만 고르기)

| 캐릭터 | 붙일 문장 |
|---|---|
| 여성 (f) | `Character: the same young woman — brown hair in a messy top bun, round glasses, gray-blue hoodie, dark blue jeans, white sneakers.` |
| 남성 (m) | `Character: the same young man — short brown hair, gray-blue suit jacket, white shirt, dark red tie, navy pants, brown shoes.` |

### [C] 동작

#### 1단계 `eye_far` — 먼 곳 보기
```
Left (X): leaning close to the monitor, squinting with tired dry eyes, small red lines in the eyes,
face only a short distance from the screen.
Right (O): sitting upright in the chair, head turned away from the monitor toward the right side,
looking far into the distance, relaxed open eyes, a small pixel window frame
with a green tree and blue sky at the right edge of the panel.
```

#### 3단계 `shoulder_open` — 어깨 펴기
```
Left (X): typing with shoulders rolled forward and hunched up toward the ears,
upper back rounded, chest closed, tense face with small stress lines.
Right (O): sitting upright with hands resting on the keyboard, shoulders rolled back and down,
chest open, shoulders clearly lower and away from the ears, two small curved arrows
showing the shoulders rolling backward, relaxed smile.
```

#### 6단계 `seat_back` — 의자 위 허리 세우기
```
Left (X): sliding forward on the chair, sitting only on the front edge of the seat,
lower back rounded, a clear empty gap between the back and the backrest, slouching.
Right (O): hips pushed all the way to the back of the seat, back touching the backrest,
spine upright with a gentle natural curve in the lower back, one small arrow pointing
from the hips toward the backrest.
```

#### 7단계 `ankle_pump` — 발목 펌프
```
Left (X): sitting still with feet flat on the floor, legs stiff, a few small gray "zzz" pixels
next to the calves, bored face.
Right (O): sitting upright, toes lifted up with heels on the floor, small up-and-down arrows
next to the feet, small motion lines around the ankles, alert face.
```

#### 8단계 `stand_water` — 일어나서 물 마시기
```
Left (X): slumped deep in the chair after sitting too long, a small pixel clock icon
above the head, sleepy tired face.
Right (O): standing next to the chair (the chair is empty), holding a small paper cup of water,
the other hand on the lower back, leaning slightly backward, refreshed smile.
The standing character is the same scale as the sitting one, and the whole body fits in the panel.
```
> 서 있는 그림은 머리가 다른 그림보다 위로 올라가요. 머리가 잘리면 자를 때 `--boxes`의 위쪽 값(420)을 줄이세요 (예: `300`).

#### 대체 `glute_squeeze` — 엉덩이 힘주기
```
Left (X): slumped sleepy in the chair, small "zzz" pixels above the head.
Right (O): sitting upright with a determined face, fists lightly clenched on the thighs,
small yellow pixel spark lines around the hips showing the muscles engaging.
```

### 완성 예시 (6단계, 여성)

```
Use the attached image as the exact reference for art style, character, layout and framing.
Make a new image in the same format: one wide image split into two panels side by side.
Left panel has "(X)" in red at the upper-left, right panel has "(O)" in green at the upper-left,
exactly where they are in the reference.
Same pixel art style with crisp square pixels, same cream checkered background,
same beige desk with a thin beige monitor and keyboard on the left, same beige office chair,
character in side view facing left, same size and same position as in the reference.
Keep the character's head in the same height area as the reference and the feet near the bottom.
No other text, no title, no speech bubbles, no logo, no watermark, no sparkle mark.
Character: the same young woman — brown hair in a messy top bun, round glasses, gray-blue hoodie, dark blue jeans, white sneakers.
Left (X): sliding forward on the chair, sitting only on the front edge of the seat,
lower back rounded, a clear empty gap between the back and the backrest, slouching.
Right (O): hips pushed all the way to the back of the seat, back touching the backrest,
spine upright with a gentle natural curve in the lower back, one small arrow pointing
from the hips toward the backrest.
```

### 받은 뒤 넣는 법

`inbox/`에 넣고 알려주시면 제가 넣을게요. 직접 하려면 (2400×1792 그림 기준):
```bash
uv run --with pillow python tools/crop_pair.py inbox/그림.png seat_back f --erase-labels --boxes "110,420,1090,1690;1250,420,2230,1690"
```

---

## 4. 한 번에 여러 동작 만들기 (선택)

캐릭터 일관성을 더 높이고 싶으면 한 장에 여러 줄로 요청할 수 있어요. 단, 칸이 많을수록 칸 하나의 해상도가 떨어져요.

```
[A] 공통 + [B] 캐릭터
Instead of one pair, make a grid with 3 rows and 2 columns, each row is one (X)/(O) pair:
row 1: shoulders rolled forward (X) / shoulders back and down (O)
row 2: sitting on the chair edge (X) / hips to the backrest (O)
row 3: feet flat and still (X) / toes lifted, ankle pump (O)
Thin gray lines between cells.
```
→ 이 경우 자르기 스크립트에 `--rows 3`을 주면 줄마다 잘라줘요 (아래 참고).

---

## 5. 자르기 스크립트 사용법

```bash
uv run --with pillow python tools/crop_pair.py 받은그림.png neck_side f
```
- 그림을 **왼쪽/오른쪽 반**으로 나누고, 위쪽 (X)/(O) 글자 부분을 잘라낸 뒤 저장해요.
- 글자가 남거나 머리가 잘리면 `--top 0.12` (위에서 잘라낼 비율, 기본 0.14)를 조절하세요.
- 여러 줄 그림: `--rows 3 --names shoulder_open,seat_back,ankle_pump`
- `--erase-labels`: 각 칸 왼쪽 위의 (X)/(O) 글자를 240px 위 배경 무늬로 덮어서 지워요 (글자가 머리 높이에 있을 때).
- `--boxes "x0,y0,x1,y1;x0,y0,x1,y1"`: ✕칸·○칸 자를 상자를 직접 지정해요. 2400×1792 그림은 `"110,420,1090,1690;1250,420,2230,1690"`.
- 캐릭터를 빼면(`f`/`m` 생략) 캐릭터 공통 그림(`{동작id}_bad.png`)으로 저장해요.
