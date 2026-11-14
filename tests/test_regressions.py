import unittest
from boss import Guardian
from combat import Combat
from geometry import Vec, Arena


class RegressionTests(unittest.TestCase):
    def advance(self, combat, seconds):
        for _ in range(round(seconds * 120)):
            combat.update(1 / 120)

    def test_boss_weak_hit_recharges_even_with_one_target(self):
        c = Combat()
        c.dash()
        self.advance(c, 0.2)
        boss = Guardian(1, Vec(560, 280), state="weak", timer=1)
        c.enemies = [boss]
        c.slash()
        self.advance(c, 0.08)
        self.assertEqual(boss.hp, 14)
        self.assertTrue(c.ready)

    def test_boss_armor_does_not_count_as_success(self):
        c = Combat()
        c.dash()
        self.advance(c, 0.2)
        boss = Guardian(1, Vec(560, 280), timer=1)
        c.enemies = [boss]
        c.slash()
        self.advance(c, 0.08)
        self.assertEqual(boss.hp, 16)
        self.assertEqual(c.last_hits, 0)
        self.assertFalse(c.ready)

    def test_prism_bonus_is_one_use_only(self):
        c = Combat()
        c.dash()
        self.advance(c, 0.2)
        for x in (530, 560, 590):
            c.spawn("wolf", Vec(x, 280))
        c.slash()
        self.advance(c, 0.08)
        self.assertTrue(c.prism)
        c.dash()
        self.advance(c, 0.2)
        c.slash()
        self.assertTrue(c.slashes[-1].boosted)
        self.assertFalse(c.prism)

    def test_boar_windup_uses_locked_direction(self):
        c = Combat()
        boar = c.spawn("boar", Vec(560, 390))
        boar.attack_wait = 0
        c.update(1 / 120)
        self.assertEqual(boar.state, "tell")
        direction = boar.direction
        c.player.pos = Vec(800, 200)
        self.advance(c, 0.7)
        self.assertEqual(boar.direction, direction)
        self.assertEqual(boar.state, "charge")

    def test_dashing_avoids_contact_damage(self):
        c = Combat()
        c.spawn("wolf", Vec(560, 245))
        c.dash()
        self.advance(c, 0.15)
        self.assertEqual(c.player.hp, 6)


if __name__ == "__main__":
    unittest.main()
