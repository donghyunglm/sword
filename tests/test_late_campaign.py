import tempfile
import unittest
from pathlib import Path

from combat import Combat
from game import Game
from geometry import Vec
from late_bosses import Knight, Dragon
from projectile import Projectile
from afterimage import Slash
from save_data import validate


class LateCampaignTests(unittest.TestCase):
    def test_linked_terminals_require_same_slash(self):
        combat = Combat()
        combat.spawn_device("terminal", Vec(485, 345), "A")
        combat.spawn_device("terminal", Vec(635, 345), "A")
        combat.resolve(Slash([Vec(485, 345)], Vec(1, 0), 34))
        self.assertEqual(len(combat.devices), 2)
        self.assertEqual(combat.kills, 0)
        combat.resolve(Slash([Vec(x, 345) for x in range(485, 636, 12)], Vec(1, 0), 34))
        self.assertEqual(len(combat.devices), 0)
        self.assertEqual(combat.kills, 2)

    def test_slash_clears_projectile_and_damages_crystal(self):
        combat = Combat()
        combat.spawn_device("crystal", Vec(500, 400))
        combat.projectiles.append(Projectile(Vec(530, 400), Vec(0, 0)))
        combat.resolve(Slash([Vec(500, 400)], Vec(1, 0), 34))
        self.assertFalse(combat.projectiles)
        self.assertEqual(combat.devices[0].hp, 1)
        self.assertEqual(combat.player.cooldown, 0)

    def test_late_bosses_only_take_one_weak_hit_per_window(self):
        for boss_type in (Knight, Dragon):
            boss = boss_type(1, Vec(560, 490))
            self.assertFalse(boss.receive_slash())
            boss.state = "weak"
            self.assertTrue(boss.receive_slash())
            self.assertFalse(boss.receive_slash())
            self.assertEqual(boss.hp, boss.max_hp - 2)

    def test_dragon_moves_to_stomp_marker_then_exposes_weakness(self):
        from geometry import Arena
        from player import Player
        dragon = Dragon(1, Vec(560, 490))
        player = Player(pos=Vec(560, 300))
        arena = Arena()
        for _ in range(260):
            dragon.update(1 / 120, player, arena)
            if dragon.state == "weak":
                break
        self.assertEqual(dragon.state, "weak")
        self.assertLess(dragon.pos.y, 490)
        self.assertGreaterEqual(dragon.pos.y, 370)

    def test_breath_damage_follows_visible_growth(self):
        from geometry import Arena
        from player import Player
        dragon = Dragon(1, Vec(560, 490), state="tell", timer=0.01,
                        attack="breath", direction=Vec(0, -1))
        player = Player(pos=Vec(560, 180))
        dragon.update(0.02, player, Arena())
        self.assertEqual(dragon.state, "attack")
        self.assertFalse(dragon.threatens(Vec(560, 400)))
        dragon.update(0.1, player, Arena())
        self.assertTrue(dragon.threatens(Vec(560, 400)))
        self.assertFalse(dragon.threatens(Vec(560, 300)))
        dragon.update(0.1, player, Arena())
        self.assertTrue(dragon.threatens(Vec(560, 300)))

    def test_stomp_damages_only_on_landing(self):
        from geometry import Arena
        from player import Player
        marker = Vec(560, 400)
        dragon = Dragon(1, Vec(560, 490), state="tell", timer=0.01,
                        attack="stomp", marker=marker, direction=Vec(0, -1),
                        stomp_remaining=90)
        player = Player(pos=marker)
        dragon.update(0.02, player, Arena())
        dragon.update(0.1, player, Arena())
        self.assertEqual(dragon.state, "attack")
        self.assertFalse(dragon.threatens(marker))
        dragon.update(0.1, player, Arena())
        self.assertEqual(dragon.state, "weak")
        self.assertTrue(dragon.threatens(marker))

    def test_checkpoint_in_sanctuary_and_full_upgrade_skip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "save.json"
            game = Game(path)
            game.load_stage(10, {"range": 3, "lifetime": 3, "speed": 3})
            game.gate_open = True
            game.enter_gate()
            self.assertTrue(game.skip_upgrade())
            self.assertEqual(game.stage["id"], "3-2")
            restored = Game(path)
            self.assertTrue(restored.continue_game())
            self.assertEqual(restored.stage["id"], "3-2")
            validate(restored.snapshot())


if __name__ == "__main__":
    unittest.main()
