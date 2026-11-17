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
                    animations = settings.get("animations", {})
                    if not isinstance(animations, dict):
                        raise ValueError("animations는 객체여야 합니다.")
                    directions = settings.get("direction_order", ["down", "left", "right", "up"])
                    if not isinstance(directions, list) or not directions or len(set(directions)) != len(directions):
                        raise ValueError("direction_order가 올바르지 않습니다.")
                    for state, animation in animations.items():
                        if not isinstance(animation, dict):
                            raise ValueError(f"{state}: 애니메이션 설정이 올바르지 않습니다.")
                        row = int(animation["row"])
                        count = int(animation["frames"])
                        fps = float(animation.get("fps", settings.get("fps", 8)))
                        row_count = len(directions) if animation.get("directions", True) else 1
                        if row < 0 or count < 1 or count * fw > img.w or (row + row_count) * fh > img.h or fps < 0:
                            raise ValueError(f"{state}: 시트 범위를 벗어났습니다.")
                    self.entries[name] = img, settings, fw, fh, frames
                except (OSError, ValueError, TypeError, KeyError) as error:
                    self.warnings.append(f"{name}: {error}")
        except (OSError, ValueError) as error:
            self.warnings.append(str(error))

    def draw(self, name, pos, time, direction=None, state="idle", alpha=1, scale=1, glow=False):
        if name not in self.entries:
            return False
        image, config, fw, fh, frames = self.entries[name]
        facing = None
        if direction:
            facing = ("right" if direction.x > 0 else "left") if abs(direction.x) > abs(direction.y) else ("up" if direction.y > 0 else "down")
        mirror_source = config.get("mirror_directions", {}).get(facing)
        mirrored = mirror_source is not None
        if mirrored:
            facing = mirror_source
        animation = config.get("animations", {}).get(state)
        if animation is None:
            animation = config.get("animations", {}).get("idle")
        row = 0
        rows = config.get("direction_rows", {})
        if rows and facing:
            row = int(rows.get(facing, 0))
        if animation is not None:
            row = int(animation["row"])
            if animation.get("directions", True) and facing:
                directions = config.get("direction_order", ["down", "left", "right", "up"])
                row += directions.index(facing) if facing in directions else 0
            frames = int(animation["frames"])
            fps = float(animation.get("fps", config.get("fps", 8)))
        else:
            row = int(config.get("state_rows", {}).get(state, row))
            fps = max(0, float(config.get("fps", 8)))
        if row < 0 or (row + 1) * fh > image.h:
            row = 0
        frame = int(time * fps) % frames if config.get("loop", True) else min(frames - 1, max(0, int(time * fps)))
        bottom = image.h - (row + 1) * fh
        width = float(config.get("draw_width", fw * 2)) * scale
        height = float(config.get("draw_height", fh * 2)) * scale
        image.opacify(alpha)
        if glow:
            from sdl2 import SDL_SetTextureBlendMode, SDL_BLENDMODE_ADD
            SDL_SetTextureBlendMode(image.texture, SDL_BLENDMODE_ADD)
        if mirrored:
            image.clip_composite_draw(frame * fw, bottom, fw, fh, 0, "h", pos.x,
                                      pos.y + float(config.get("offset_y", 8)), width, height)
        else:
            image.clip_draw(frame * fw, bottom, fw, fh, pos.x,
                            pos.y + float(config.get("offset_y", 8)), width, height)
        if glow:
            from sdl2 import SDL_BLENDMODE_BLEND
            SDL_SetTextureBlendMode(image.texture, SDL_BLENDMODE_BLEND)
        image.opacify(1)
        return True

    def draw_cell(self, name, column, row, pos, width, height, alpha=1):
        """장치·탄환·효과처럼 한 칸씩 사용하는 작은 시트의 지정 프레임."""
        if name not in self.entries:
            return False
        image, _, fw, fh, _ = self.entries[name]
        if column < 0 or row < 0 or (column + 1) * fw > image.w or (row + 1) * fh > image.h:
            return False
        image.opacify(alpha)
        image.clip_draw(column * fw, image.h - (row + 1) * fh, fw, fh,
                        pos.x, pos.y, width, height)
        image.opacify(1)
        return True

    def draw_rotated_cell(self, name, column, row, pos, width, height, angle, alpha=1):
        if name not in self.entries:
            return False
        image, _, fw, fh, _ = self.entries[name]
        if column < 0 or row < 0 or (column + 1) * fw > image.w or (row + 1) * fh > image.h:
            return False
        image.opacify(alpha)
        image.clip_composite_draw(column * fw, image.h - (row + 1) * fh, fw, fh,
                                  angle, "", pos.x, pos.y, width, height)
        image.opacify(1)
        return True
