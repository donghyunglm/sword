import unittest
from campaign import CampaignGame
from campaign_renderer import CampaignRenderer
from campaign_save import validate
from geometry import Vec
from quickbar import entry_position, LEGACY_SLOTS


class QuickbarTests(unittest.TestCase):
    def setUp(self):
        self.game = CampaignGame('.cache/unused-quickbar.json')
        self.game.start_trial(14)
        self.game.toggle_inventory()
        self.renderer = CampaignRenderer.__new__(CampaignRenderer)

    def drag_entry(self, token, target):
        index = next(i for i, entry in enumerate(self.game.inventory_entries()) if ':'.join(entry) == token)
        start = entry_position(index)
        self.renderer.click(self.game, start, 1)
        self.assertIsNotNone(self.game.drag)
        self.renderer.release(self.game, target, 1)

    def test_inventory_drop_swaps_existing_slot_and_keeps_inventory(self):
        bag = dict(self.game.bag)
        self.drag_entry('item:fire_stone', Vec(64, 608))
        self.assertEqual(self.game.quickslots[0], 'item:fire_stone')
        self.assertEqual(self.game.quickslots[4], 'weapon:1')
        self.assertEqual(self.game.bag, bag)
        self.assertTrue(self.game.select_item(0))
        self.assertEqual(self.game.combat.element, 'fire')

    def test_drop_outside_cancels_without_losing_item(self):
        before = list(self.game.quickslots)
        self.drag_entry('item:fire_stone', Vec(1100, 50))
        self.assertEqual(self.game.quickslots, before)
        self.assertIsNone(self.game.drag)

    def test_move_shortcuts_and_clear_with_right_click(self):
        self.renderer.click(self.game, Vec(64, 608), 1)
        self.renderer.release(self.game, Vec(122, 608), 1)
        self.assertEqual(self.game.quickslots[:2], ['weapon:2', 'weapon:1'])
        self.renderer.click(self.game, Vec(122, 608), 3)
        self.assertIsNone(self.game.quickslots[1])
        self.assertIn(('weapon', '1'), self.game.inventory_entries())

    def test_potion_registration_consumes_only_on_activation(self):
        count = self.game.bag['healing_potion']
        self.drag_entry('item:healing_potion', Vec(180, 608))
        self.assertEqual(self.game.bag['healing_potion'], count)
        self.game.toggle_inventory()
        self.game.combat.player.hp = 2
        self.assertTrue(self.game.select_item(2))
        self.assertEqual(self.game.combat.player.hp, 4)
        self.assertEqual(self.game.bag['healing_potion'], count - 1)

    def test_layout_restore_and_old_save_migration(self):
        self.drag_entry('item:fire_stone', Vec(64, 608))
        data = self.game.snapshot()
        validate(data)
        restored = CampaignGame('.cache/unused-quickbar.json')
        restored._restore_bag(data)
        self.assertEqual(restored.quickslots, self.game.quickslots)
        del data['quickslots']
        validate(data)
        restored._restore_bag(data)
        self.assertEqual(restored.quickslots, LEGACY_SLOTS)

    def test_materials_cannot_be_registered(self):
        self.game.bag['ember_fragment'] = 1
        self.assertFalse(self.game.begin_drag('item:ember_fragment'))
        self.assertIsNone(self.game.drag)

    def test_wheel_uses_reordered_slots(self):
        self.drag_entry('item:fire_stone', Vec(122, 608))
        self.game.toggle_inventory()
        self.game.select_item(0)
        self.assertTrue(self.game.cycle_item(1))
        self.assertEqual(self.game.combat.element, 'fire')


if __name__ == '__main__':
    unittest.main()
