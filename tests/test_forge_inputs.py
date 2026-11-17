import unittest
from unittest.mock import patch
from campaign import CampaignGame
from campaign_renderer import CampaignRenderer
from campaign_save import validate
from geometry import Vec


class ForgeInputTests(unittest.TestCase):
    def setUp(self):
        self.g = CampaignGame('.cache/unused-forge-inputs.json')
        self.g.start_trial(0)
        self.g.enter_hub()
        self.g.open_facility('forge', require_near=False)

    def test_owned_materials_do_not_fill_slots_automatically(self):
        self.assertEqual(self.g.forge_inputs, {})
        self.assertFalse(self.g.forge_ready())
        self.assertFalse(self.g.craft())
        self.assertEqual(self.g.bag['ember_fragment'], 3)

    def test_only_double_click_registers_needed_count(self):
        self.g.bag['ember_fragment'] = 8
        self.assertFalse(self.g.forge_material_click('ember_fragment', 10))
        self.assertEqual(self.g.forge_inputs, {})
        self.assertTrue(self.g.forge_material_click('ember_fragment', 10.2))
        self.assertEqual(self.g.forge_inputs['ember_fragment'], 3)
        self.assertEqual(self.g.bag['ember_fragment'], 5)
        self.assertFalse(self.g.insert_forge_material('ember_fragment'))
        self.assertFalse(self.g.forge_ready())
        self.g.insert_forge_material('flame_core')
        self.assertTrue(self.g.forge_ready())
        self.assertTrue(self.g.craft())
        self.assertEqual(self.g.bag['ember_fragment'], 5)
        self.assertEqual(self.g.forge_inputs, {})

    def test_partial_materials_can_be_topped_up(self):
        self.g.bag['ember_fragment'] = 1
        self.g.insert_forge_material('ember_fragment')
        self.assertEqual(self.g.forge_inputs['ember_fragment'], 1)
        self.assertFalse(self.g.forge_ready())
        self.g.bag['ember_fragment'] = 2
        self.g.insert_forge_material('ember_fragment')
        self.assertEqual(self.g.forge_inputs['ember_fragment'], 3)

    def test_recipe_change_and_close_refund_without_duplication(self):
        self.g.insert_forge_material('ember_fragment')
        self.g.choose_recipe(1)
        self.assertEqual(self.g.bag['ember_fragment'], 3)
        self.assertEqual(self.g.forge_inputs, {})
        self.g.choose_recipe(0)
        self.g.insert_forge_material('flame_core')
        self.g.close_forge()
        self.g.close_forge()
        self.assertEqual(self.g.bag['flame_core'], 1)
        self.assertEqual(self.g.forge_inputs, {})

    def test_staged_materials_return_on_save_restore(self):
        self.g.insert_forge_material('ember_fragment')
        data = self.g.snapshot()
        validate(data)
        self.assertEqual(data['bag']['ember_fragment'], 3)
        restored = CampaignGame('.cache/unused-forge-inputs.json')
        restored._restore_bag(data)
        self.assertEqual(restored.bag['ember_fragment'], 3)
        self.assertEqual(restored.forge_inputs, {})

    def test_inventory_mouse_double_click_fills_slot(self):
        renderer = CampaignRenderer.__new__(CampaignRenderer)
        i = self.g.inventory_entries().index(('item', 'ember_fragment'))
        pos = Vec(747 + i % 4 * 86, 515 - i // 4 * 80)
        with patch('campaign_renderer.time.monotonic', side_effect=[20, 20.2]):
            renderer.click(self.g, pos, 1)
            self.assertEqual(self.g.forge_inputs, {})
            renderer.click(self.g, pos, 1)
        self.assertEqual(self.g.forge_inputs['ember_fragment'], 3)


if __name__ == '__main__':
    unittest.main()
