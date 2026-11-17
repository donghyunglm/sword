import unittest
from combat import Combat
from final_dragon import FinalDragon
from geometry import Vec


class FinalDragonTests(unittest.TestCase):
    def encounter(self):
        c = Combat()
        c.player.pos = Vec(560, 310)
        boss = FinalDragon(1, Vec(560, 375))
        boss.state, boss.timer, boss.direction = "charge", 0.5, Vec(0, -1)
        c.enemies = [boss]
        return c, boss

    def test_parry_stuns_two_seconds_blocks_damage_and_grants_two_casts(self):
        c, boss = self.encounter()
        boss.shield_element = "fire"
        self.assertTrue(c.parry())
        c.update(1 / 120)
        self.assertEqual(boss.state, "stunned")
        self.assertEqual(boss.timer, 2)
        self.assertEqual(c.player.hp, 6)
        self.assertEqual(c.counter_charges, 2)
        self.assertEqual(c.skill_element, "fire")
        self.assertIsNone(c.element)
        self.assertTrue(c.dash(Vec(1, 0)))
        for _ in range(23):
            c.update(1 / 120)
        self.assertTrue(c.element_skill.cast(c, Vec(0, 1)))
        self.assertEqual(c.element_skill.cooldown, 0)
        self.assertTrue(c.dash(Vec(-1, 0)))
        for _ in range(23):
            c.update(1 / 120)
        self.assertTrue(c.element_skill.cast(c, Vec(0, 1)))
        self.assertEqual(c.counter_charges, 0)
        self.assertEqual(c.element_skill.cooldown, 3)
        self.assertFalse(c.element_skill.cast(c, Vec(0, 1)))

    def test_failed_parry_does_not_stun(self):
        c, boss = self.encounter()
        c.parry()
        c.parry_left = 0
        c.update(1 / 120)
        self.assertNotEqual(boss.state, "stunned")
        self.assertLess(c.player.hp, 6)

    def test_matching_shield_and_single_backstab_bonus(self):
        c, boss = self.encounter()
        boss.shield_element = "ice"
        c.hit_enemy(boss, "fire", c.player.pos)
        self.assertEqual(boss.shield_hp, 8)
        c.hit_enemy(boss, "ice", c.player.pos)
        self.assertEqual(boss.shield_hp, 7)
        self.assertEqual(boss.hp, 36)
        boss.break_shield(True)
        c.counter_left, c.backstab_ready = 2, True
        rear = boss.pos + Vec(0, 100)
        c.hit_enemy(boss, "soul", rear, True)
        self.assertEqual(boss.hp, 32)
        c.hit_enemy(boss, "soul", rear, True)
        self.assertEqual(boss.hp, 31)

    def test_shield_random_change_has_preview_and_never_repeats(self):
        c, boss = self.encounter()
        boss.elements = ["soul", "ice", "fire"]
        boss.shield_timer = 0.71
        boss.state, boss.timer = "approach", 20
        boss.update(0.02, c.player, c.arena)
        self.assertNotEqual(boss.next_element, boss.shield_element)
        preview = boss.next_element
        boss.update(0.70, c.player, c.arena)
        self.assertEqual(boss.shield_element, preview)

    def test_stun_ends_and_shield_returns(self):
        c, boss = self.encounter()
        boss.break_shield(True)
        boss.update(1.99, c.player, c.arena)
        self.assertEqual(boss.state, "stunned")
        boss.update(0.02, c.player, c.arena)
        self.assertEqual(boss.shield_hp, 8)
        self.assertEqual(boss.state, "recover")
