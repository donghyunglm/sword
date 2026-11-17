import unittest
from combat import Combat
from geometry import Vec


class ElementSkillTests(unittest.TestCase):
    def test_cursor_aim_uses_each_echo_origin(self):
        c = Combat()
        from afterimage import Trail
        c.element = "fire"
        c.trail = Trail(Vec(300, 200), Vec(1, 0), 3)
        c.trail.record(Vec(600, 200))
        target = Vec(200, 150)
        self.assertTrue(c.element_skill.cast(c, Vec(0, 1), target))
        for pos, direction, _ in c.element_skill.pending:
            self.assertAlmostEqual(direction.x, (target - pos).normalized().x)
            self.assertAlmostEqual(direction.y, (target - pos).normalized().y)
            self.assertLess(direction.x, 0)
            self.assertLess(direction.y, 0)

    def tick(self, c, seconds):
        for _ in range(round(seconds * 120)):
            c.update(1 / 120)

    def test_skill_consumes_trail_fires_upward_and_blocks_recast(self):
        c = Combat()
        c.element = "fire"
        c.player.facing = Vec(1, 0)
        c.dash()
        self.tick(c, 0.2)
        self.assertTrue(c.element_skill.cast(c, Vec(0, 1)))
        self.assertIsNone(c.trail)
        self.assertFalse(c.element_skill.cast(c, Vec(0, 1)))
        c.element_skill.update(0.01, c)
        self.assertTrue(c.element_skill.bolts)
        self.assertGreater(c.element_skill.bolts[0].velocity.y, 0)
        self.assertEqual(c.element_skill.bolts[0].velocity.x, 0)
        self.assertTrue(c.element_skill.pending)
        self.tick(c, 0.9)
        self.assertFalse(c.element_skill.pending)

    def test_element_bolt_hits_enemy_once_without_hurting_player(self):
        c = Combat()
        from projectile import Projectile
        target = c.spawn("boar", Vec(560, 270))
        target.attack_wait = 20
        c.element_skill.bolts.append(Projectile(Vec(560, 225), Vec(0, 440), kind="ice"))
        c.element_skill.update(0.1, c)
        self.assertEqual(target.hp, 1)
        self.assertGreater(target.freeze_left, 0)
        self.assertFalse(c.element_skill.bolts)
        self.assertEqual(c.player.hp, 6)
