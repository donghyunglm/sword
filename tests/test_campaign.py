import unittest
from campaign import CampaignGame
from campaign_save import validate
from items import RECIPES
from geometry import Vec


class CampaignTests(unittest.TestCase):
    def game(self):
        game = CampaignGame('.cache/test-campaign-unused.json')
        game.trial = True
        return game

    def test_every_stage_updates(self):
        game = self.game()
        for index in range(15):
            game.start_trial(index)
            game.update(0.016)
            self.assertEqual(game.index, index)
            self.assertIsNotNone(game.combat.arena)

    def test_rewards_cannot_be_farmed_twice(self):
        game = self.game()
        self.assertTrue(game.give({'ember_fragment': 1}, 'chest'))
        self.assertFalse(game.give({'ember_fragment': 1}, 'chest'))
        self.assertEqual(game.bag['ember_fragment'], 1)

    def test_hub_faces_walk_direction_and_retains_it_when_stopped(self):
        game = self.game()
        game.start_trial(0)
        game.enter_hub()
        for direction in (Vec(-1, 0), Vec(0, 1), Vec(1, 0), Vec(0, -1)):
            game.combat.aim_target = game.combat.player.pos - direction * 200
            game.update(0.02, direction)
            self.assertEqual(game.combat.player.facing, direction)
            game.update(0.02)
            self.assertEqual(game.combat.player.facing, direction)

    def test_campaign_dash_moves_independently_of_mouse_aim(self):
        game = self.game()
        game.start_trial(14)
        combat = game.combat
        origin = combat.player.pos
        combat.aim_target = origin + Vec(200, 0)
        self.assertTrue(combat.dash(Vec(0, 1)))
        game.update(0.02)
        self.assertGreater(combat.player.pos.y, origin.y)
        self.assertAlmostEqual(combat.player.pos.x, origin.x)
        self.assertEqual(combat.player.facing, Vec(0, 1))

    def test_every_round_faces_movement_despite_opposite_mouse(self):
        game = self.game()
        for index in range(15):
            game.start_trial(index)
            combat = game.combat
            for direction in (Vec(-1, 0), Vec(0, 1), Vec(1, 0), Vec(0, -1)):
                combat.aim_at(combat.player.pos - direction * 200)
                game.update(.01, direction)
                # 메인 루프가 렌더 직전 마우스 좌표를 갱신해도 회전하지 않는다.
                combat.aim_at(combat.player.pos - direction * 200)
                self.assertEqual(combat.player.facing, direction, (index, direction))
                game.update(.01)
                self.assertEqual(combat.player.facing, direction)

    def test_crafting_consumes_materials_once(self):
        game = self.game()
        recipe = RECIPES[0]
        self.assertFalse(game.craft())
        game.bag.update(recipe['cost'])
        self.assertTrue(game.craft())
        self.assertFalse(game.craft())
        self.assertNotIn(recipe['result'], game.bag)
        game.update(4.9)
        self.assertIsNone(game.forge_drop)
        game.update(.11)
        self.assertEqual(game.forge_drop, recipe['result'])
        self.assertNotIn(recipe['result'], game.bag)
        self.assertFalse(game.craft())
        self.assertTrue(game.interact())
        self.assertEqual(game.bag[recipe['result']], 1)
        self.assertIsNone(game.forge_drop)
        for key in recipe['cost']:
            self.assertEqual(game.bag[key], 0)

    def test_presentation_materials_are_added_only_once(self):
        game = self.game()
        game.start_trial(0)
        game.enter_hub()
        self.assertEqual(game.bag['ember_fragment'], 3)
        self.assertEqual(game.bag['flame_core'], 1)
        game.enter_hub()
        self.assertEqual(game.bag['ember_fragment'], 3)
        self.assertEqual(game.bag['flame_core'], 1)

    def test_crafting_blocks_movement_and_survives_restore(self):
        game = self.game()
        game.bag.update(RECIPES[0]['cost'])
        game.craft()
        origin = game.combat.player.pos
        game.update(2, Vec(1, 0))
        self.assertEqual(game.combat.player.pos, origin)
        data = game.snapshot()
        validate(data)
        restored = self.game()
        restored._restore_bag(data)
        restored.mode = 'hub'
        restored.update(3.1)
        self.assertEqual(restored.forge_drop, 'fire_stone')
        self.assertIsNone(restored.forge_job)
        data = restored.snapshot()
        validate(data)
        game._restore_bag(data)
        self.assertEqual(game.forge_drop, 'fire_stone')

    def test_can_walk_in_all_directions_after_crafting(self):
        game = self.game()
        game.start_trial(0)
        game.enter_hub()
        self.assertTrue(game.craft())
        game.update(5.01)
        origin = game.combat.player.pos
        self.assertTrue(game.combat.arena.valid(origin, game.combat.player.radius))
        for direction in (Vec(-1, 0), Vec(0, 1), Vec(1, 0), Vec(0, -1)):
            game.combat.player.pos = origin
            game.update(.04, direction)
            self.assertGreater(game.combat.player.pos.distance(origin), 8)

    def test_old_forge_position_is_unstuck_when_crafting_finishes(self):
        game = self.game()
        game.start_trial(0)
        game.enter_hub()
        game.craft()
        game.combat.player.pos = Vec(350, 430)
        self.assertFalse(game.combat.arena.valid(game.combat.player.pos, 14))
        game.update(5.01)
        self.assertTrue(game.combat.arena.valid(game.combat.player.pos, 14))


if __name__ == '__main__':
    unittest.main()
