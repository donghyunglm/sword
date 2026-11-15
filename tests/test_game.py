import copy
import json
from pathlib import Path
import tempfile
import unittest
from game import Game
from geometry import Vec
from boss import Guardian
from save_data import read_save, validate
from stage import load_stages


class GameTests(unittest.TestCase):
    def setUp(self):
        test_root = Path(__file__).resolve().parents[1] / ".cache" / "tests"
        test_root.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=test_root)
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "progress.json"
        self.game = Game(self.path)

    def test_stage_data_has_fifteen_valid_rounds(self):
        self.assertEqual(len(load_stages()), 15)

    def test_pause_freezes_all_combat_timers(self):
        g = self.game
        g.new_game()
        g.combat.dash()
        g.paused = True
        before = copy.deepcopy(g.combat.__dict__)
        g.update(0.5, Vec(1, 0))
        self.assertEqual(g.combat.elapsed, before["elapsed"])
        self.assertEqual(g.combat.player.dash_left, before["player"].dash_left)

    def test_seal_requires_kills_not_waiting(self):
        g = self.game
        g.new_game()
        for _ in range(240):
            g.update(1 / 120)
        self.assertFalse(g.gate_open)
        for _ in range(600):
            g.update(1 / 120)
        g.combat.enemies.clear()
        g.combat.kills = g.stage["goal"]
        g.update(1 / 120)
        self.assertTrue(g.gate_open)
        self.assertEqual(g.mode, "play")

    def test_reward_continue_and_retry_do_not_duplicate(self):
        g = self.game
        g.new_game()
        g.gate_open = True
        g.enter_gate()
        self.assertEqual(g.mode, "upgrade")
        self.assertFalse(g.enter_gate())
        continued = Game(self.path)
        continued.continue_game()
        self.assertEqual(continued.mode, "upgrade")
        continued.choose_upgrade(0)
        self.assertEqual(continued.index, 1)
        self.assertEqual(continued.combat.player.upgrades["range"], 1)
        self.assertFalse(continued.choose_upgrade(0))
        continued.combat.player.hp = 0
        continued.mode = "defeat"
        continued.retry()
        self.assertEqual(continued.cleared, [0])
        self.assertEqual(sum(continued.combat.player.upgrades.values()), 1)
        self.assertEqual(continued.combat.kills, 0)

    def test_fifteenth_round_finishes_campaign_without_loop(self):
        g = self.game
        g.new_game()
        for i in range(15):
            self.assertEqual(g.index, i)
            g.gate_open = True
            g.enter_gate()
            if i < 14:
                if not g.choose_upgrade(i % 3):
                    g.skip_upgrade()
        self.assertEqual(g.mode, "victory")
        self.assertEqual(g.index, 14)
        restored = Game(self.path)
        restored.continue_game()
        self.assertEqual(restored.mode, "victory")

    def test_boss_weakness_once_per_window(self):
        b = Guardian(1, Vec(560, 490))
        self.assertFalse(b.receive_slash())
        b.state = "weak"
        self.assertTrue(b.receive_slash())
        self.assertFalse(b.receive_slash())
        self.assertEqual(b.hp, 14)

    def test_corrupted_save_is_preserved(self):
        self.path.write_text("{broken", encoding="utf-8")
        save, message = read_save(self.path)
        self.assertIsNone(save)
        self.assertTrue(message)
        self.assertEqual(self.path.read_text(), "{broken")

    def test_invalid_save_types_are_rejected(self):
        self.game.new_game()
        data = self.game.snapshot()
        data["upgrades"]["range"] = True
        with self.assertRaises(ValueError):
            validate(data)

    def test_training_does_not_write_save(self):
        self.game.start_training()
        self.game.update(0.1)
        self.assertFalse(self.path.exists())

    def test_upgrade_restores_health_for_next_round(self):
        g = self.game
        g.new_game()
        g.combat.player.hp = 1
        g.gate_open = True
        g.enter_gate()
        g.choose_upgrade(0)
        self.assertEqual(g.combat.player.hp, 6)

    def test_trial_stage_selection_preserves_existing_save(self):
        g = self.game
        g.new_game()
        original = self.path.read_bytes()
        g.exit_to_title()
        g.open_trial_select()
        self.assertEqual(g.mode, "select")
        self.assertTrue(g.start_trial(14))
        self.assertEqual(g.stage["id"], "3-5")
        self.assertEqual(sum(g.combat.player.upgrades.values()), 9)
        g.gate_open = True
        g.enter_gate()
        self.assertEqual(g.mode, "victory")
        self.assertEqual(self.path.read_bytes(), original)
        g.exit_to_title()
        self.assertTrue(g.continue_game())
        self.assertEqual(g.stage["id"], "1-1")

    def test_campaign_actions_change_later_fights(self):
        g = self.game
        g.cleared = [7, 10, 12, 13]
        g.load_stage(8, persist=False)
        self.assertLess(g.goal, g.stage["goal"])
        g.load_stage(14, persist=False)
        dragon = g.combat.enemies[0]
        self.assertEqual(dragon.max_hp, 14)

    def test_boss_rewards_change_combat_rules(self):
        g = self.game
        g.load_stage(3, persist=False)
        self.assertFalse(g.combat.purification)
        g.load_stage(5, persist=False)
        self.assertTrue(g.combat.purification)
        self.assertFalse(g.combat.seal_break)
        g.load_stage(10, persist=False)
        self.assertTrue(g.combat.seal_break)

    def test_fortress_crystals_spawn_only_while_intact(self):
        g = self.game
        g.load_stage(7, persist=False)
        g.update(1 / 120)
        g.wave_index = len(g.stage["waves"])
        g.combat.enemies.clear()
        g.update(4.1)
        self.assertEqual({e.kind for e in g.combat.enemies}, {"wolf", "mage", "sentinel"})
        g.combat.devices = [d for d in g.combat.devices if d.pos.x != 240]
        g.combat.enemies.clear()
        g.update(5.1)
        self.assertNotIn("wolf", {e.kind for e in g.combat.enemies})

    def test_signpost_can_be_lost_and_retried(self):
        g = self.game
        g.load_stage(1, persist=False)
        for _ in range(14 * 120):
            g.update(1 / 120)
            if g.mode == "defeat":
                break
        self.assertEqual(g.mode, "defeat")
        g.retry()
        self.assertEqual(g.beacon_hp, 8)

    def test_sanctuary_fireball_travels_across_arena(self):
        g = self.game
        g.load_stage(12, persist=False)
        for _ in range(290):
            g.update(1 / 120)
        fireballs = [b for b in g.combat.projectiles if b.kind == "dragon"]
        self.assertTrue(fireballs)
        start = fireballs[0].pos
        g.update(0.1)
        self.assertGreater(fireballs[0].pos.distance(start), 20)


if __name__ == "__main__":
    unittest.main()
