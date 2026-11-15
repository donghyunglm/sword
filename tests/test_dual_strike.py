import tempfile
import unittest
from pathlib import Path

from combat import Combat
from game import Game
from geometry import Vec
from late_bosses import Dragon


class DualStrikeTests(unittest.TestCase):
    def advance(self, combat, seconds):
        for _ in range(round(seconds * 120)):
            combat.update(1 / 120)

    def test_direct_sword_works_without_dash_and_faces_forward(self):
        combat = Combat(dual_mode=True)
        combat.spawn("wolf", Vec(560, 242))
        combat.spawn("wolf", Vec(560, 118))
        self.assertTrue(combat.slash())
        self.advance(combat, 0.08)
        self.assertEqual(combat.kills, 1)
        self.assertEqual(combat.enemies[0].pos.y < combat.player.pos.y, True)
        self.assertEqual(combat.slashes[0].style, "dual")

    def test_dash_leaves_one_echo_that_attacks_from_origin(self):
        combat = Combat(dual_mode=True)
        origin = combat.player.pos
        self.assertTrue(combat.dash())
        self.assertFalse(combat.slash())
        self.advance(combat, 0.2)
        self.assertEqual(combat.echo_pos, origin)
        self.assertIsNone(combat.trail)
        combat.spawn("wolf", origin + Vec(0, 62))
        self.assertTrue(combat.slash())
        self.advance(combat, 0.08)
        self.assertEqual(combat.kills, 1)
        self.assertIsNone(combat.echo_pos)
        self.assertEqual(len(combat.slashes[0].points), 2)

    def test_only_dragon_round_uses_experimental_controls(self):
        with tempfile.TemporaryDirectory() as directory:
            game = Game(Path(directory) / "save.json")
            game.load_stage(13, persist=False)
            self.assertFalse(game.combat.dual_mode)
            game.load_stage(14, persist=False)
            self.assertTrue(game.combat.dual_mode)

    def test_two_swords_hit_one_boss_only_once(self):
        combat = Combat(dual_mode=True)
        combat.player.pos = Vec(620, 410)
        combat.player.facing = Vec(0, 1)
        combat.echo_pos = Vec(500, 410)
        combat.echo_remaining = 1.2
        dragon = Dragon(1, Vec(560, 490), state="weak", timer=1)
        combat.enemies = [dragon]
        self.assertTrue(combat.slash())
        self.advance(combat, 0.08)
        self.assertEqual(dragon.hp, dragon.max_hp - 2)
        self.assertEqual(combat.last_hits, 1)


if __name__ == "__main__":
    unittest.main()
