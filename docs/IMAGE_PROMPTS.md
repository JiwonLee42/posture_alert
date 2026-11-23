# 픽셀 이미지 생성 프롬프트

레퍼런스 느낌: **Windows 95/XP 오류 창 + 픽셀 경고 아이콘**. 그 창 안에 들어갈 **자세 그림**을 같은 픽셀 스타일로 만듭니다.

ChatGPT(이미지 생성), Gemini, Midjourney 어디서든 쓸 수 있게 영어 프롬프트로 정리했어요. (이미지 생성 모델은 영어 프롬프트에서 스타일이 더 안정적이에요.)

---

## 1. 앱에 넣는 방법

- 파일 위치: `src/posture_alert/assets/img/`
- 파일 이름: `{동작 id}_bad.png` (✕ 지금), `{동작 id}_good.png` (○ 이렇게)
- 파일이 있으면 앱이 자동으로 그 그림을 쓰고, 없으면 지금의 임시 막대 인형을 보여줘요.
- 권장 크기: **128×128 px, 배경 투명 PNG**
  - 생성 이미지는 보통 1024px로 나오니, 줄일 때 **"최근접 이웃(Nearest Neighbor)"** 방식으로 줄여야 픽셀이 뭉개지지 않아요.
  - 예: `magick in.png -filter point -resize 128x128 out.png` (ImageMagick)

---

## 2. 공통 스타일 프롬프트 (모든 이미지 앞에 붙이기)

같은 캐릭터가 계속 나와야 하니, 아래 문장을 **매번 그대로** 앞에 붙이세요.

```
16-bit pixel art, retro Windows 95 era aesthetic, chunky pixels on a 64x64 grid,
limited palette (max 16 colors), clean 1px black outline, flat shading with one highlight tone,
no anti-aliasing, no gradients, transparent background, centered, side view.
Character: a cute gender-neutral office worker with short dark brown hair,
round peach skin face, simple dot eye, blue sweater, dark gray pants,
sitting on a simple gray office chair in front of a small beige CRT-style monitor.
Same character design in every image.
```

> 첫 이미지가 마음에 들면, 다음 이미지부터는 그 이미지를 **레퍼런스로 첨부**하고 "same character, same style"을 붙이면 일관성이 훨씬 좋아져요.

**피할 것 (네거티브)** — Midjourney는 `--no`, 다른 도구는 문장 끝에 "Avoid: ..."로:
```
Avoid: realistic, 3D render, smooth gradients, blurry, anti-aliased edges, text, watermark, extra limbs
```

---

## 3. 동작별 프롬프트

각 동작마다 `_bad`(✕ 지금)와 `_good`(○ 이렇게) 두 장을 만듭니다.
스트레칭처럼 "나쁜 자세"가 없는 동작은 `_bad` = **하기 전**, `_good` = **동작 중**으로 만들어요.

### 자세 체크

| 파일 | 프롬프트 (공통 스타일 뒤에 붙이기) |
|---|---|
| `chin_tuck_bad.png` | `The character slouches with forward head posture: head and neck jutting far forward toward the monitor, ears clearly in front of the shoulders, rounded upper back. A small red pixel "X" mark floats near the neck.` |
| `chin_tuck_good.png` | `The character sits upright doing a chin tuck: chin gently pulled back making a slight double chin, ear aligned directly above the shoulder, straight back. A small green pixel check mark floats near the head. A faint dotted vertical line passes through ear and shoulder.` |
| `shoulder_open_bad.png` | `The character sits with rounded shoulders rolled forward and inward, chest closed, shoulders raised toward the ears, looking tense.` |
| `shoulder_open_good.png` | `The character sits with shoulders rolled back and down, chest open, shoulders relaxed and far from the ears, calm smile.` |

### 스트레칭

| 파일 | 프롬프트 |
|---|---|
| `neck_side_bad.png` | `The character sits upright, neutral pose, right hand resting on the desk, before stretching.` |
| `neck_side_good.png` | `The character, front view instead of side view, gently tilts the head to the right with the right hand resting on the left side of the head, left arm relaxed down, eyes closed and relaxed. Small curved motion lines on the left side of the neck.` |
| `scapula_squeeze_bad.png` | `The character sits hunched with arms hanging forward, shoulder blades spread apart, back view.` |
| `scapula_squeeze_good.png` | `Back view: the character squeezes the shoulder blades together, elbows bent in a W shape pulled back beside the torso, chest pushed forward, two small arrows pointing toward the spine.` |

### 일어나기 / 눈

| 파일 | 프롬프트 |
|---|---|
| `stand_water_bad.png` | `The character has been sitting too long, slumped deep in the chair, a small pixel clock icon above the head showing 2 hours.` |
| `stand_water_good.png` | `The character stands up next to the chair holding a small paper cup of water, the other hand on the lower back, leaning slightly backward, refreshed expression.` |
| `eye_far_good.png` | `The character sits turned away from the monitor, looking out a small pixel window with a distant green tree and blue sky, relaxed eyes.` |

### 앉아서 하는 대체 동작 (2시간+ 착석용)

| 파일 | 프롬프트 |
|---|---|
| `ankle_pump_bad.png` | `Close-up of the character's legs under the desk while seated, feet flat on the floor, still.` |
| `ankle_pump_good.png` | `Close-up of the character's legs under the desk while seated, toes lifted up on one frame side and heels lifted on the other, small up-down arrows next to the feet.` |
| `seat_back_bad.png` | `The character slides forward on the chair, sitting on the edge with the lower back rounded and a gap between the back and the backrest.` |
| `seat_back_good.png` | `The character sits with hips pushed all the way to the back of the chair, lower back gently arched, back touching the backrest, upright.` |
| `glute_squeeze_bad.png` | `The character sits slumped and sleepy on the chair, small "zzz" pixels above the head.` |
| `glute_squeeze_good.png` | `The character sits upright with a determined face, small yellow pixel spark lines near the hips showing muscle engagement.` |

---

## 4. 아이콘 (선택)

| 파일 | 용도 | 프롬프트 |
|---|---|---|
| `icon_warning.png` | 알림 창 왼쪽 경고 아이콘 | `16-bit pixel art warning sign: yellow triangle with thick black pixel outline and a black exclamation mark, small light-yellow highlight on the upper-left edge, darker orange shading on the right edge, transparent background, 32x32 grid.` |
| `icon_turtle.png` | 거북목 알림 아이콘 | `16-bit pixel art cute green turtle head sticking far out of its shell, worried face, black 1px outline, transparent background, 32x32 grid, retro Windows 95 icon style.` |
| `icon_app.png` | 트레이·exe 아이콘 | `16-bit pixel art app icon: a beige retro CRT monitor showing a small blue figure with a straight spine and a green check mark, black outline, transparent background, 32x32 grid, Windows 95 desktop icon style.` |

> 아이콘은 아직 코드에서 자동으로 읽지 않아요. 만들어 주시면 연결할게요.

---

## 5. 한 번에 여러 장 뽑는 팁

- **스프라이트 시트**로 요청하면 캐릭터 일관성이 가장 좋아요:
  ```
  [공통 스타일 프롬프트]
  A sprite sheet with 2 columns and 4 rows, each cell 64x64, same character in each cell:
  row 1: forward head posture (bad) | chin tuck upright (good)
  row 2: rounded shoulders (bad) | shoulders back and down (good)
  row 3: slumped on chair edge (bad) | hips to backrest upright (good)
  row 4: sitting still (before) | standing with a cup of water (after)
  Thin 1px gray grid lines between cells.
  ```
- 받은 시트는 잘라서 파일 이름에 맞게 저장하면 돼요. (자르는 스크립트가 필요하면 말씀해 주세요.)
