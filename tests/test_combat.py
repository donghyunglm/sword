import unittest
from geometry import Arena, Rect, Vec
from combat import Combat
from afterimage import Trail
from boss import Guardian


class CombatTests(unittest.TestCase):
    def tick(self, c, seconds, move=Vec()):
        for _ in range(round(seconds * 120)):
            c.update(1 / 120, move)

    def test_normalized_diagonal_movement(self):
        a, b = Combat(), Combat()
        origin = a.player.pos
        self.tick(a, 0.3, Vec(1, 0))
        self.tick(b, 0.3, Vec(1, 1))
        self.assertAlmostEqual(a.player.pos.distance(origin), b.player.pos.distance(origin))

    def test_dash_does_no_damage_and_cannot_stack_paths(self):
        c = Combat()
        c.spawn("wolf", Vec(560, 270))
        self.assertTrue(c.dash())
        self.assertFalse(c.slash())
        self.tick(c, 0.2)
        self.assertEqual(c.enemies[0].hp, 1)
        self.assertFalse(c.dash())
        self.assertLess(c.trail.points[0].y, c.trail.points[-1].y)

    def test_multi_hit_is_counted_per_enemy_and_recharges(self):
        c = Combat()
        c.dash()
        self.tick(c, 0.2)
        for x in (545, 575):
            c.spawn("wolf", Vec(x, 280))
        self.assertTrue(c.slash())
        self.assertFalse(c.dash())
        self.tick(c, 0.6)
        self.assertEqual(c.last_hits, 2)
        self.assertEqual(c.kills, 2)
        self.assertTrue(c.ready)
        self.tick(c, 0.2)
        self.assertEqual(c.kills, 2)

    def test_single_hit_and_miss_cooldowns(self):
        c = Combat()
        c.dash()
        self.tick(c, 0.2)
        c.spawn("boar", Vec(560, 280))
        c.slash()
        self.tick(c, 0.6)
        self.assertEqual(c.last_hits, 1)
        self.assertGreater(c.player.cooldown, 0)
        self.assertEqual(c.enemies[0].hp, 1)
        self.assertFalse(c.ready)

    def test_expiry_requires_cooldown(self):
        c = Combat()
        c.dash()
        self.tick(c, 1.45)
        self.assertIsNone(c.trail)
        self.assertFalse(c.ready)
        self.tick(c, 0.9)
        self.assertTrue(c.ready)

    def test_dash_sweep_cannot_pass_thin_wall(self):
        c = Combat(Arena([Rect(500, 230, 130, 3)]))
        c.dash()
        c.update(0.18)
        self.assertLessEqual(c.player.pos.y, 216)
        self.assertTrue(all(p.y <= 216 for p in c.trail.points))

    def test_distance_sampling_is_frame_independent(self):
        a, b = Trail(Vec(), Vec(1, 0), 1.2), Trail(Vec(), Vec(1, 0), 1.2)
        a.record(Vec(190, 0))
        for i in range(1, 191):
            b.record(Vec(i, 0))
        self.assertEqual(a.points, b.points)

    def test_chain_strikes_in_order_and_each_enemy_once(self):
        c = Combat()
        c.player.facing = Vec(1, 0)
        self.assertTrue(c.dash())
        self.tick(c, 0.2)
        c.spawn("wolf", Vec(575, 180))
        c.spawn("wolf", Vec(740, 180))
        self.assertTrue(c.slash())
        self.tick(c, 0.09)
        self.assertEqual(c.kills, 1)
        self.tick(c, 0.55)
        self.assertEqual(c.kills, 2)
        self.assertEqual(c.last_hits, 2)

    def test_direct_sword_is_available_without_dash(self):
        c = Combat()
        c.spawn("wolf", Vec(560, 235))
        self.assertTrue(c.slash())
        self.tick(c, 0.08)
        self.assertEqual(c.kills, 1)

    def test_chain_boss_hits_are_sequential_and_capped(self):
        c = Combat()
        c.player.facing = Vec(1, 0)
        c.dash()
        self.tick(c, 0.2)
        boss = Guardian(1, Vec(655, 180), state="weak", timer=2)
        c.enemies = [boss]
        c.slash()
        self.tick(c, 0.16)
        first_damage = boss.max_hp - boss.hp
        self.tick(c, 0.5)
        self.assertGreater(boss.max_hp - boss.hp, first_damage)
        self.assertLessEqual(boss.max_hp - boss.hp, 4)

    def test_seal_break_destroys_crystal_in_one_strike(self):
        c = Combat(seal_break=True)
        c.player.pos = Vec(500, 340)
        c.player.facing = Vec(0, 1)
        c.spawn_device("crystal", Vec(500, 400))
        c.slash()
        self.tick(c, 0.08)
        self.assertFalse(c.devices)


if __name__ == "__main__":
    unittest.main()
