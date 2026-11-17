import unittest
import json
import struct
from pathlib import Path
from geometry import Vec
from sprite_bank import SpriteBank


class FakeImage:
    w = 384
    h = 1024

    def __init__(self):
        self.clip = None

    def opacify(self, alpha):
        pass

    def clip_draw(self, *args):
        self.clip = args

    def clip_composite_draw(self, *args):
        self.clip = args


class SpriteBankTests(unittest.TestCase):
    def test_hero_left_uses_mirrored_right_frames_in_all_states(self):
        config = json.loads((Path(__file__).resolve().parents[1] / 'assets/sprites.json').read_text(encoding='utf-8'))['player']
        bank = SpriteBank.__new__(SpriteBank)
        image = FakeImage()
        bank.entries = {'player': (image, config, 64, 64, 6)}
        for state, animation in config['animations'].items():
            bank.draw('player', Vec(200, 200), 0, Vec(-1, 0), state)
            self.assertEqual(image.clip[1], 1024 - (animation['row'] + 3) * 64)
            self.assertEqual(image.clip[5], 'h')
            bank.draw('player', Vec(200, 200), 0, Vec(1, 0), state)
            self.assertEqual(len(image.clip), 8)

    def test_state_direction_and_frame_count(self):
        bank = SpriteBank.__new__(SpriteBank)
        image = FakeImage()
        config = {
            "direction_order": ["down", "left", "right", "up"],
            "animations": {
                "idle": {"row": 0, "frames": 4, "fps": 6},
                "walk": {"row": 4, "frames": 6, "fps": 10},
                "dash": {"row": 8, "frames": 4, "fps": 18},
                "slash": {"row": 12, "frames": 5, "fps": 12},
            },
        }
        bank.entries = {"player": (image, config, 64, 64, 6)}
        self.assertTrue(bank.draw("player", Vec(100, 200), 0.2, Vec(1, 0), "dash"))
        self.assertEqual(image.clip[:4], (3 * 64, 1024 - 11 * 64, 64, 64))
        self.assertTrue(bank.draw("player", Vec(100, 200), 0.4, Vec(0, 1), "slash"))
        self.assertEqual(image.clip[:4], (4 * 64, 1024 - 16 * 64, 64, 64))

    def test_supplied_sheet_grid_and_atlas_cells(self):
        root = Path(__file__).resolve().parents[1] / "assets"
        manifest = json.loads((root / "sprites.json").read_text(encoding="utf-8"))
        for name, settings in manifest.items():
            path = root / settings["file"]
            with path.open("rb") as stream:
                header = stream.read(26)
            self.assertEqual(header[:8], b"\x89PNG\r\n\x1a\n", name)
            width, height = struct.unpack(">II", header[16:24])
            self.assertIn(header[25], (2, 6), name)
            if not settings["file"].startswith("campaign/"):
                self.assertEqual(header[25], 6 if name not in ("forest", "fortress", "sanctuary") else 2)
            fw, fh = settings.get("frame_width", width), settings.get("frame_height", height)
            self.assertEqual(width % fw, 0, name)
            self.assertEqual(height % fh, 0, name)
            for animation in settings.get("animations", {}).values():
                rows = len(settings.get("direction_order", ["down", "left", "right", "up"])) if animation.get("directions", True) else 1
                self.assertLessEqual(animation["row"] + rows, height // fh, name)
                self.assertLessEqual(animation["frames"], width // fw, name)


if __name__ == "__main__":
    unittest.main()
