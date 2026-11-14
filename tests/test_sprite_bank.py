import unittest
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


class SpriteBankTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
