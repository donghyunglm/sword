import unittest
from geometry import Arena, Rect, Vec
from combat import Combat
from afterimage import Trail


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
        self.tick(c, 0.08)
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
        self.tick(c, 0.07)
        self.assertEqual(c.last_hits, 1)
        self.assertGreater(c.player.cooldown, 0.45)
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


if __name__ == "__main__":
    unittest.main()
