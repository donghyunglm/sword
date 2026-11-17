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
        self.assertGreater(combat.player.facing.x, 0.9)

    def test_crafting_consumes_materials_once(self):
        game = self.game()
        recipe = RECIPES[0]
        self.assertFalse(game.craft())
        game.bag.update(recipe['cost'])
        self.assertTrue(game.craft())
        self.assertFalse(game.craft())
        self.assertEqual(game.bag[recipe['result']], 1)
        for key in recipe['cost']:
            self.assertEqual(game.bag[key], 0)


if __name__ == '__main__':
    unittest.main()
