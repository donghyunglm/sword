"""외부 PNG/스프라이트 시트 선택 로더. 설정이 없으면 코드형 임시 스프라이트 사용."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class SpriteBank:
    def __init__(self, pico):
        self.pico = pico
        self.entries = {}
        self.warnings = []
        try:
            manifest = json.loads((ROOT / "assets" / "sprites.json").read_text(encoding="utf-8"))
            if not isinstance(manifest, dict):
                raise ValueError("최상위 설정은 객체여야 합니다.")
            for name, settings in manifest.items():
                try:
                    image_path = ROOT / "assets" / settings["file"]
                    img = pico.load_image(str(image_path))
                    fw, fh = int(settings.get("frame_width", img.w)), int(settings.get("frame_height", img.h))
                    frames = int(settings.get("frames", 1))
                    if fw <= 0 or fh <= 0 or frames <= 0 or frames * fw > img.w or fh > img.h:
                        raise ValueError("프레임 크기가 이미지 범위를 벗어났습니다.")
                    self.entries[name] = img, settings, fw, fh, frames
                except (OSError, ValueError, TypeError, KeyError) as error:
                    self.warnings.append(f"{name}: {error}")
        except (OSError, ValueError) as error:
            self.warnings.append(str(error))

    def draw(self, name, pos, time, direction=None, state="idle", alpha=1, scale=1):
        if name not in self.entries:
            return False
        image, config, fw, fh, frames = self.entries[name]
        row = 0
        rows = config.get("direction_rows", {})
        if rows and direction:
            facing = ("right" if direction.x > 0 else "left") if abs(direction.x) > abs(direction.y) else ("up" if direction.y > 0 else "down")
            row = int(rows.get(facing, 0))
        row = int(config.get("state_rows", {}).get(state, row))
        if row < 0 or (row + 1) * fh > image.h:
            row = 0
        fps = max(0, float(config.get("fps", 8)))
        frame = int(time * fps) % frames
        bottom = image.h - (row + 1) * fh
        width = float(config.get("draw_width", fw * 2)) * scale
        height = float(config.get("draw_height", fh * 2)) * scale
        image.opacify(alpha)
        image.clip_draw(frame * fw, bottom, fw, fh, pos.x,
                        pos.y + float(config.get("offset_y", 8)), width, height)
        image.opacify(1)
        return True
