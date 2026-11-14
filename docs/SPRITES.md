# 최종 스프라이트 교체

현재 캐릭터와 적은 코드로 그리는 임시 픽셀 패턴이다. 게임을 확인하기 위해 별도 이미지가 필요하지 않다.

최종 이미지가 준비되면 `assets/images`에 넣고 `assets/sprites.json`에 설정한다.
`sprites.example.json`은 **구조를 보여주는 예시**다. 이미지가 없는 상태에서 그대로 복사할 필요는 없다.

## 한 장짜리 PNG

```json
{
  "player": {
    "file": "images/hero.png",
    "draw_width": 48,
    "draw_height": 64,
    "offset_y": 8
  }
}
```

## 가로 프레임과 방향별 행

```json
{
  "player": {
    "file": "images/hero_sheet.png",
    "frame_width": 32,
    "frame_height": 32,
    "frames": 4,
    "fps": 10,
    "direction_rows": {"down": 0, "left": 1, "right": 2, "up": 3},
    "draw_width": 48,
    "draw_height": 48
  }
}
```

행 번호는 **이미지 위쪽부터 0**이다. 각 행의 프레임 수와 크기는 동일해야 한다.
상태별 행은 `state_rows`로 지정할 수 있다. `idle`, `walk`, `dash`, `slash`(주인공),
`chase`, `tell`, `charge`, `recover`, `approach`, `weak`(적/보스) 상태를 사용한다.
상태 행을 지정하면 방향 행보다 우선한다. 방향과 상태가 복잡하게 섞인 시트는 실제 시트를 받은 뒤
정확한 행·프레임 규칙에 맞춰 로더를 확장하면 된다.

사용할 수 있는 항목은 `player`, `wolf`, `boar`, `guardian`, `forest`다.
guardian은 기본 캐릭터보다 2배 크기로 표시하므로 예시의 `draw_width` 42는 실제 84px로 표시된다.
설정하지 않은 항목은 임시 픽셀 그래픽을 계속 사용한다.

## 판정과 그래픽은 별도

- 실제 판정은 `player.py`, `enemy.py`, `boss.py`의 `radius`와 `config.py`의 참격 반경을 사용한다.
- 이미지 크기를 바꿔도 판정 반경이 자동으로 바뀌지 않는다. F1을 눌러 실제 판정을 확인한다.
- 잔영은 주인공 이미지의 반투명 복사본이다. 별도 잔영 시트는 필요하지 않다.
- 임시 캐릭터의 스카프·검 연출은 외부 주인공 PNG를 사용하면 생략한다.
- 이미지는 프로젝트 내에서만 읽으며 외부 다운로드나 API 호출을 하지 않는다.
