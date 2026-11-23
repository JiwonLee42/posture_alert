# 픽셀 이미지 생성 프롬프트

기준 그림: **"기억하자 척추수술 3000만원"** (여성·남성 캐릭터의 ✕ 거북목 / ○ 바른 자세 두 장).
스트레칭·일어나기 동작 그림도 **같은 캐릭터, 같은 구도, 같은 배경**으로 만들어야 알림 창 안에서 자연스럽게 이어집니다.

ChatGPT(이미지 생성), Gemini, Midjourney 어디서든 쓸 수 있게 영어 프롬프트로 정리했어요. 이미지 생성 모델은 영어 프롬프트에서 스타일이 더 안정적이에요.

---

## 1. 만드는 순서 (요약)

1. 이미지 생성 도구에 **기준 그림을 첨부**해요 (여성 캐릭터면 여성 그림, 남성이면 남성 그림).
2. 아래 **2장의 공통 프롬프트** + **3장의 동작 프롬프트**를 붙여서 요청해요.
   → 기준 그림처럼 **왼쪽 (X) / 오른쪽 (O) 두 칸**짜리 그림이 나와요.
3. 받은 그림을 자르기 스크립트로 잘라 앱에 넣어요:
   ```bash
   uv run --with pillow python tools/crop_pair.py 받은그림.png neck_side f
   ```
   → `assets/img/neck_side_f_bad.png`, `assets/img/neck_side_f_good.png` 가 생겨요.
4. `uv run posture-alert --demo stretch`로 확인해요.

### 앱이 그림을 고르는 순서
1. `assets/img/{동작id}_{f|m}_{bad|good}.png` — 동작 + 캐릭터별 그림
2. `assets/img/{동작id}_{bad|good}.png` — 동작별 그림 (캐릭터 공통)
3. `assets/img/default/{f|m}_{bad|good}.png` — 기본 거북목 그림 (지금 들어 있는 것)
4. 임시 픽셀 막대 인형

---

## 2. 공통 프롬프트 (매번 맨 앞에 붙이기)

```
Use the attached image as the exact style and character reference.
Same pixel art style, same character (same face, hair, glasses, clothes),
same desk with a thin beige monitor and keyboard, same beige office chair,
same cream checkered background, same side view facing left.

Layout: one image split into two panels side by side, like the reference.
Left panel labeled "(X)" in red at the top, right panel labeled "(O)" in green at the top.
Both panels the same size, the character at the same position and scale in both.
No other text, no title, no speech bubbles, no watermark.
Pixel art with crisp square pixels, no blur, no smooth gradients, no 3D.
```

### 캐릭터 고정 문장 (공통 프롬프트 바로 뒤에 하나 붙이기)

| 캐릭터 | 문장 |
|---|---|
| 여성 (f) | `Character: young woman with brown hair in a messy top bun, round glasses, blue-gray hoodie, dark blue jeans, white sneakers.` |
| 남성 (m) | `Character: young man with short brown hair, light blue-gray suit jacket, white shirt, dark red tie, navy pants, brown shoes.` |

> 첫 결과에서 얼굴이 달라지면 "Keep the face exactly like the reference" 를 덧붙이고 다시 요청하세요.

---

## 3. 동작별 프롬프트

왼쪽 (X) = **하기 전 / 나쁜 자세**, 오른쪽 (O) = **동작 중 / 바른 자세**예요.
`{동작id}`는 자르기 스크립트에 넣을 이름이에요.

### 자세 체크

#### `shoulder_open` — 어깨 펴기
```
Left (X): sitting at the desk typing, shoulders rolled forward and hunched up toward the ears,
upper back rounded, tense face with small stress lines.
Right (O): sitting upright with hands still on the keyboard, shoulders rolled back and down,
chest open, relaxed calm smile.
```

### 스트레칭

#### `neck_side` — 목 옆 늘리기
```
Left (X): sitting at the desk, stiff neck, one hand rubbing the back of the neck, tired face.
Right (O): sitting upright, turned slightly toward the viewer, head gently tilted to the right,
right hand resting on the left side of the head, left arm relaxed down,
eyes closed and relaxed, two small curved motion lines on the left side of the neck.
```

#### `scapula_squeeze` — 날개뼈 모으기
```
Left (X): sitting hunched forward with arms hanging toward the keyboard, back rounded.
Right (O): sitting upright away from the keyboard, elbows bent in a W shape and pulled back
beside the torso, shoulder blades squeezed together, chest pushed forward,
two small arrows on the back pointing toward the spine.
```

#### `neck_back` — 목 뒤 늘리기 (동작 추가 시)
```
Left (X): sitting with the head pushed forward toward the monitor, neck tense.
Right (O): sitting upright, hands clasped behind the head, head gently bowed forward,
elbows pointing forward, relaxed face, small motion lines on the back of the neck.
```

### 일어나기 / 눈

#### `stand_water` — 일어나서 물 마시기
```
Left (X): slumped deep in the chair, a small pixel clock icon above the head showing 2 hours,
sleepy tired face.
Right (O): standing next to the chair holding a small paper cup of water,
the other hand on the lower back, leaning slightly backward, refreshed smile.
```

#### `eye_far` — 먼 곳 보기
```
Left (X): leaning close to the monitor with dry squinting eyes, small red lines in the eyes.
Right (O): sitting upright turned away from the monitor, looking out a small pixel window
with a green tree and blue sky, relaxed eyes, small sparkle near the eyes.
```

### 앉아서 하는 대체 동작 (2시간+ 착석용)

#### `ankle_pump` — 발목 펌프
```
Left (X): sitting still, feet flat on the floor, legs stiff, small gray "zzz" near the legs.
Right (O): sitting upright, toes lifted with heels on the floor, small up-and-down arrows next to the feet,
alert face.
```

#### `seat_back` — 의자 위 허리 세우기
```
Left (X): sliding forward on the chair, sitting on the edge of the seat, lower back rounded,
a gap between the back and the backrest.
Right (O): hips pushed all the way to the back of the chair, back touching the backrest,
spine upright with a gentle curve in the lower back.
```

#### `glute_squeeze` — 엉덩이 힘주기
```
Left (X): slumped sleepy on the chair, small "zzz" above the head.
Right (O): sitting upright with a determined face, small yellow pixel spark lines near the hips.
```

---

## 4. 한 번에 여러 동작 만들기 (선택)

캐릭터 일관성을 더 높이고 싶으면 한 장에 여러 줄로 요청할 수 있어요. 단, 칸이 많을수록 칸 하나의 해상도가 떨어져요.

```
[공통 프롬프트] [캐릭터 문장]
Instead of one pair, make a grid with 3 rows and 2 columns, each row is one (X)/(O) pair:
row 1: neck side stretch
row 2: shoulder blade squeeze
row 3: stand up with a cup of water
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
- 여러 줄 그림: `--rows 3 --names neck_side,scapula_squeeze,stand_water`
- 캐릭터를 빼면(`f`/`m` 생략) 캐릭터 공통 그림(`{동작id}_bad.png`)으로 저장해요.
