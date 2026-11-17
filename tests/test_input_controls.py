import unittest
from input_controls import window_to_game
from combat import Combat
from geometry import Vec


class PointerTests(unittest.TestCase):
    def test_screen_below_character_faces_down(self):
        combat = Combat()
        combat.player.pos = Vec(560, 380)
        for x, y, expected in ((560, 600, Vec(0, -1)), (560, 150, Vec(0, 1)),
                               (200, 379, Vec(-1, 0)), (900, 379, Vec(1, 0))):
            combat.aim_at(window_to_game(x, y))
            self.assertEqual(combat.player.facing, expected)

    def test_window_scaling_keeps_same_aim(self):
        self.assertEqual(window_to_game(560, 600), window_to_game(840, 900, 1680, 1140))
