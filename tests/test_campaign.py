import unittest
from campaign import CampaignGame
from campaign_save import validate
from items import RECIPES


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
