"""거점 → 탐험 → 재료 회수 → 합성 → 다음 지역으로 이어지는 새 모험."""
import copy
from pathlib import Path
import config as C
from game import Game as LegacyGame
from combat import Combat
from player import Player
from geometry import Arena, Rect, Vec
from campaign_data import STAGES, REGIONS, CampaignArena
from campaign_save import DEFAULT_PATH, read, write
from region_bosses import RegionBoss, FrozenGate
from final_dragon import FinalDragon
from enemy import Enemy
from items import ITEMS, RECIPES, GEAR, name

HUB_FACILITIES = (("forge", Vec(265, 465), "대장간"), ("storage", Vec(850, 355), "보관함"),
                  ("map", Vec(560, 110), "출발"))


class CampaignGame(LegacyGame):
    def __init__(self, save_path=DEFAULT_PATH):
        super().__init__(save_path)
        self.stages = copy.deepcopy(STAGES)
        self.saved, self.notice = read(save_path)
        self.bag, self.equipped = {}, set()
        self.collected, self.opened = set(), set()
        self.next_stage = 0
        self.recipe_index = self.map_region = self.inventory_selected = 0
        self.forge_flash = 0.0
        self.corpses, self.drops, self.chests = [], [], []
        self.frozen_gate = None
        self.storage_open = False
        self.in_hub = False
        self._boss = None

    def snapshot(self, phase=None):
        phase = phase or self.mode
        if phase not in ("play", "transit", "victory"):
            phase = "hub"
        return {"version": 2, "stage": self.index, "next_stage": self.next_stage, "phase": phase,
                "hp": max(1, self.combat.player.hp), "weapon": self.combat.player.weapon,
                "element": self.combat.element, "bag": dict(self.bag), "equipped": sorted(self.equipped),
                "cleared": list(self.cleared), "collected": sorted(self.collected), "opened": sorted(self.opened)}

    def persist(self, phase=None):
        if self.training or self.trial:
            return
        try:
            data = self.snapshot(phase)
            write(data, self.save_path)
            self.saved = copy.deepcopy(data)
        except OSError:
            self.notice = "진행을 저장하지 못했습니다. 현재 모험은 계속할 수 있습니다."

    def _restore_bag(self, data):
        self.bag = dict(data["bag"])
        self.equipped = set(data["equipped"])
        self.collected, self.opened = set(data["collected"]), set(data["opened"])
        self.cleared = list(data["cleared"])
        self.owned_elements = [e for e in ("ice", "fire") if self.bag.get(e + "_stone")]
        self.combat.element = data.get("element")
        self.next_stage = data["next_stage"]

    def new_game(self):
        self.training = self.trial = False
        self.bag = {"healing_potion": 2}
        self.equipped, self.collected, self.opened = set(), set(), set()
        self.cleared, self.owned_elements = [], []
        self.next_stage, self.index = 0, 0
        self.combat = Combat()
        self.load_stage(0, persist=False)
        self.enter_hub()
        self.tell("부모를 죽인 용은 자신의 성으로 돌아갔다. 숲을 지나 놈을 찾아가자.", 7)

    def continue_game(self):
        data, self.notice = read(self.save_path)
        if not data:
            return False
        self.saved = copy.deepcopy(data)
        self.training = self.trial = False
        self._restore_bag(data)
        self.load_stage(data["stage"], hp=data["hp"], weapon=data["weapon"], persist=False)
        self.next_stage = data["next_stage"]
        if data["phase"] == "hub":
            self.enter_hub()
        elif data["phase"] == "victory":
            self.mode = "victory"
        elif data["phase"] == "transit":
            self.begin_transit()
        return True

    def load_stage(self, index, upgrades=None, hp=C.MAX_HP, persist=True, weapon=1):
        previous_element = self.combat.element
        self.index = self.next_stage = index
        data = self.stage
        p = Player(pos=Vec(*data["start"]), hp=hp)
        p.weapon = weapon if weapon in self.available_weapons(index) else 1
        self.combat = Combat(CampaignArena(data), p, purification=True, seal_break=True)
        self.combat.element = previous_element if previous_element in self.owned_elements else None
        self.combat.magic_damage = 2
        self.combat.arrows = self.bag.get("arrow_bundle", 0)
        self._apply_gear()
        self.mode, self.paused, self.inventory_open, self.storage_open, self.in_hub = "play", False, False, False, False
        self.wave_index, self.gate_open = 0, False
        self.goal, self.banner_left = data["goal"], 5
        self.toast, self.toast_left = data.get("story", ""), 5
        self.hazard_timer, self.hazard_active, self.hazard_marker = 4.5, 0, None
        self.transit_progress, self.transit_x = 0, 560
        self.chests = [dict(c, id=f"{data['id']}:chest:{i}") for i, c in enumerate(data["chests"])]
        self.drops, self.corpses, self.element_drops = [], [], []
        self._boss = None
        boss = data.get("boss")
        if boss:
            pos = Vec(*data.get("boss_pos", [560, 460]))
            if boss == "final_dragon":
                enemy = FinalDragon(1, pos)
                enemy.name = "부모를 앗아간 마룡"
            elif boss == "boar_lord":
                enemy = Enemy.make(1, "boar", pos)
                enemy.hp, enemy.max_hp, enemy.radius, enemy.name = 8, 8, 28, "마족화된 큰 멧돼지"
            else:
                enemy = RegionBoss(1, pos, boss)
            self.combat.uid = 1
            self.combat.enemies.append(enemy)
            self._boss = enemy
        self.frozen_gate = None
        if data.get("frozen_gate"):
            self.frozen_gate = FrozenGate(Vec(*data["frozen_gate"]), self.combat.arena,
                                          f"{data['id']}:gate" in self.collected)
            self.combat.shot_targets = [self.frozen_gate]
        self.round_start = copy.deepcopy(self.snapshot("play"))
        if persist:
            self.persist("play")

    def _apply_gear(self):
        p = self.combat.player
        p.environment_speed = 0.72 if self.stage["region"] == 2 and "fur_leather_coat" not in self.equipped else 1.0
        p.magic_resistant = "magic_resist_amulet" in self.equipped

    def available_weapons(self, index):
        return (1,) + ((2,) if "ice" in self.owned_elements else ()) + ((3,) if 13 in self.cleared else ())

    def select_weapon(self, number):
        if self.mode not in ("play", "hub", "forge", "map") or (self.paused and not self.inventory_open):
            return False
        if number not in self.available_weapons(self.index):
            return False
        self.combat.element, self.combat.player.weapon = None, number
        self.persist()
        return True

    def select_item(self, slot):
        if self.mode not in ("play", "hub", "forge", "map") or (self.paused and not self.inventory_open):
            return False
        if slot < 3:
            return self.select_weapon(slot + 1)
        element = {3: "ice", 4: "fire"}.get(slot)
        if element not in self.owned_elements:
            self.tell("대장간에서 원소석을 먼저 합성하세요.")
            return False
        self.combat.element = element
        self.persist()
        return True

    def toggle_inventory(self):
        if self.mode not in ("play", "hub") or (self.paused and not self.inventory_open):
            return
        self.inventory_open = not self.inventory_open
        self.paused = self.inventory_open
        if not self.inventory_open:
            self.storage_open = False

    def inventory_entries(self):
        return [("weapon", str(n)) for n in self.available_weapons(self.index)] + [("item", k) for k in ITEMS if self.bag.get(k, 0)]

    def use_inventory(self, entry_index):
        entries = self.inventory_entries()
        if not 0 <= entry_index < len(entries):
            return
        self.inventory_selected = entry_index
        kind, key = entries[entry_index]
        if kind == "weapon":
            return self.select_weapon(int(key))
        if key.endswith("_stone"):
            return self.select_item(3 if key == "ice_stone" else 4)
        if key in GEAR:
            if key in self.equipped:
                self.equipped.remove(key)
            else:
                self.equipped.add(key)
            self._apply_gear()
            self.tell(name(key) + (" 착용" if key in self.equipped else " 해제"))
        elif key == "healing_potion" and self.combat.player.hp < C.MAX_HP:
            self.bag[key] -= 1
            self.combat.player.hp = min(C.MAX_HP, self.combat.player.hp + 2)
            self.tell("회복약 사용 · 체력 +2")
        self.persist()

    def enter_hub(self):
        self.mode, self.paused, self.inventory_open, self.in_hub = "hub", False, False, True
        c = self.combat
        c.player.pos, c.player.hp = Vec(560, 285), C.MAX_HP
        c.enemies, c.devices, c.projectiles, c.slashes = [], [], [], []
        c.trail = None
        c.element_skill.pending.clear()
        c.element_skill.bolts.clear()
        c.counter_left, c.counter_charges = 0, 0
        c.arena = Arena([Rect(170, 415, 175, 70), Rect(785, 310, 130, 55), Rect(80, 105, 230, 130),
                         Rect(460, 565, 145, 70), Rect(995, 300, 70, 210), Rect(805, 575, 245, 75)])
        c.arena.bounds = Rect(75, 90, 980, 565)
        self.corpses = []
        self.persist("hub")

    def open_facility(self, facility, require_near=True):
        if self.mode != "hub" or self.inventory_open:
            return False
        entry = next((f for f in HUB_FACILITIES if f[0] == facility), None)
        if not entry or (require_near and self.combat.player.pos.distance(entry[1]) > 145):
            self.tell("시설 가까이 이동한 뒤 E 또는 클릭하세요.")
            return False
        if facility == "storage":
            self.toggle_inventory()
            self.storage_open = True
        else:
            self.mode = facility
            self.map_region = self.stages[min(14, self.next_stage)]["region"]
        return True

    def interact(self):
        if self.paused:
            return False
        if self.mode == "hub":
            facility = min(HUB_FACILITIES, key=lambda f: self.combat.player.pos.distance(f[1]))
            return self.open_facility(facility[0])
        if self.mode != "play":
            return False
        pos = self.combat.player.pos
        nearby_drop = next((d for d in self.drops if pos.distance(d["pos"]) < 70), None)
        if nearby_drop:
            self.give(nearby_drop["loot"], nearby_drop["id"])
            self.drops.remove(nearby_drop)
            self.persist("play")
            return True
        box = next((c for c in self.chests if c["id"] not in self.opened and pos.distance(Vec(*c["pos"])) < 90), None)
        if box:
            self.opened.add(box["id"])
            self.give(box["loot"], box["id"])
            self.persist("play")
            return True
        if self.gate_open and pos.distance(Vec(*self.stage["exit"])) < 80:
            return self.enter_gate()
        self.tell("가까운 상자와 보스 전리품을 E로 획득할 수 있습니다.")
        return False

    def pickup_element(self):
        return self.interact()

    def give(self, loot, reward_id):
        if reward_id in self.collected:
            return False
        self.collected.add(reward_id)
        for key, count in loot.items():
            self.bag[key] = min(9999, self.bag.get(key, 0) + count)
        self.combat.arrows = self.bag.get("arrow_bundle", 0)
        self.tell("획득: " + " · ".join(f"{name(k)} {v}" for k, v in loot.items()), 4)
        self.combat.events.append(("open", self.combat.player.pos))
        return True

    def craft(self):
        recipe = RECIPES[self.recipe_index]
        result = recipe["result"]
        if self.bag.get(result):
            self.tell("이미 완성한 원소석입니다.")
            return False
        if any(self.bag.get(k, 0) < v for k, v in recipe["cost"].items()):
            self.tell("지역의 재료 상자와 보스 핵을 먼저 회수하세요.")
            return False
        for key, count in recipe["cost"].items():
            self.bag[key] -= count
        self.bag[result] = 1
        self.owned_elements.append(recipe["element"])
        self.combat.element = recipe["element"]
        self.forge_flash = 1.1
        self.combat.events.append(("open", Vec(550, 350)))
        self.tell(name(result) + " 완성! 원소 슬롯에 장착했습니다.", 5)
        self.persist("hub")
        return True

    def region_reason(self, region):
        if not 0 <= region < 4:
            return "지역을 선택하세요."
        if region and REGIONS[region - 1]["end"] not in self.cleared:
            return "이전 지역의 보스를 먼저 쓰러뜨리세요."
        if region >= 2 and not self.bag.get("fire_stone"):
            return "대장간에서 불의 돌을 먼저 합성하세요."
        if region >= 3 and not self.bag.get("ice_stone"):
            return "대장간에서 얼음의 돌을 먼저 합성하세요."
        if all(i in self.cleared for i in range(REGIONS[region]["start"], REGIONS[region]["end"] + 1)):
            return "완료한 지역입니다."
        return ""

    def launch_region(self):
        reason = self.region_reason(self.map_region)
        if reason:
            self.tell(reason)
            return False
        region = REGIONS[self.map_region]
        index = next(i for i in range(region["start"], region["end"] + 1) if i not in self.cleared)
        if self.bag.get("fire_stone"):
            self.bag["arrow_bundle"] = max(24, self.bag.get("arrow_bundle", 0))
        self.load_stage(index, weapon=self.combat.player.weapon)
        return True

    def enter_gate(self):
        if self.mode != "play" or not self.gate_open or self.training:
            return False
        if self.index not in self.cleared:
            self.cleared.append(self.index)
        self.next_stage = self.index + 1
        if self.index == 14:
            self.mode = "victory"
            self.persist("victory")
        elif self.index in (2, 6, 10):
            self.enter_hub()
            self.tell("거점으로 귀환했습니다. 대장간과 보관함에서 다음 여정을 준비하세요.", 5)
        else:
            self.begin_transit()
        return True

    def begin_transit(self):
        self.mode, self.transit_progress, self.transit_x = "transit", 0.0, 560
        self.persist("transit")

    def retry(self):
        if self.training:
            return self.start_training()
        if self.round_start:
            data = copy.deepcopy(self.round_start)
            self._restore_bag(data)
            if self.bag.get("fire_stone"):
                self.bag["arrow_bundle"] = max(24, self.bag.get("arrow_bundle", 0))
            self.load_stage(data["stage"], weapon=data["weapon"])

    def return_hub(self):
        self.next_stage = self.index
        self.enter_hub()

    def start_trial(self, index):
        if not 0 <= index < len(self.stages):
            return False
        self.trial, self.training = True, False
        self.bag, self.equipped, self.collected, self.opened = {"healing_potion": 3, "arrow_bundle": 80}, set(), set(), set()
        self.cleared = list(range(index))
        self.owned_elements = []
        for element, threshold in (("fire", 7), ("ice", 11)):
            if index >= threshold:
                self.bag[element + "_stone"] = 1
                self.owned_elements.append(element)
        self.combat.element = "fire" if index >= 7 else None
        self.load_stage(index, persist=False)
        self.tell("라운드 체험 · 기존 진행 저장은 유지됩니다.", 4)
        return True

    def exit_to_title(self):
        self.mode, self.paused, self.inventory_open = "title", False, False
        self.trial = self.training = False
        self.saved, self.notice = read(self.save_path)

    def update(self, dt, movement=Vec()):
        if self.paused:
            return
        self.toast_left = max(0, self.toast_left - dt)
        self.forge_flash = max(0, self.forge_flash - dt)
        if self.mode == "transit":
            self.transit_progress = min(1, self.transit_progress + max(0, movement.y) * dt)
            if self.transit_progress >= 1:
                self.load_stage(self.next_stage, hp=C.MAX_HP, weapon=self.combat.player.weapon)
            return
        if self.mode == "hub":
            p = self.combat.player
            if movement.length():
                p.pos, _ = self.combat.arena.move(p.pos, movement.normalized() * (p.speed * dt), p.radius)
                p.facing = movement.normalized()
            p.moving = movement.length() > 0
            return
        if self.mode != "play":
            return
        self.banner_left = max(0, self.banner_left - dt)
        c = self.combat
        if self._boss and type(self._boss) is FinalDragon:
            self._boss.elements = ["soul"] + self.owned_elements
        c.update(dt, movement)
        self.bag["arrow_bundle"] = c.arrows
        for corpse in self.corpses:
            corpse[1] += dt
        self.corpses = [corpse for corpse in self.corpses if corpse[1] < 1.6]
        if self._boss and self._boss.hp <= 0:
            self.corpses.append([self._boss, 0])
            reward_id = self.stage["id"] + ":boss"
            if reward_id not in self.collected:
                self.drops.append({"id": reward_id, "pos": self._boss.pos, "loot": self.stage.get("boss_loot", {})})
                self.tell("보스 전리품을 E로 회수하세요.", 5)
            self._boss = None
        if self.frozen_gate and self.frozen_gate.opened and self.stage["id"] + ":gate" not in self.collected:
            self.collected.add(self.stage["id"] + ":gate")
            self.tell("불화살로 얼음문이 녹았습니다!", 4)
            self.persist("play")
        while self.wave_index < len(self.stage["waves"]) and c.elapsed >= self.stage["waves"][self.wave_index][0]:
            for kind, x, y in self.stage["waves"][self.wave_index][1]:
                c.spawn(kind, Vec(x, y))
            self.wave_index += 1
        if self.training and len(c.enemies) < 3:
            c.spawn("wolf", Vec(300, 480))
        self._hazards(dt)
        if c.player.hp <= 0:
            self.mode = "defeat"
            return
        required = all(not box["required"] or box["id"] in self.opened for box in self.chests)
        melted = not self.frozen_gate or self.frozen_gate.opened
        if not self.training and not c.enemies and self.wave_index == len(self.stage["waves"]) and required and melted and not self.drops:
            if not self.gate_open:
                self.gate_open = True
                self.tell("길이 열렸습니다. 출구로 이동하세요.", 4)
            if c.player.pos.distance(Vec(*self.stage["exit"])) < 35:
                self.enter_gate()

    def _hazards(self, dt):
        hazard = self.stage.get("hazards")
        if not hazard or any(getattr(e, "state", "") == "stunned" for e in self.combat.enemies):
            self.hazard_marker, self.hazard_active = None, 0
            return
        self.hazard_timer -= dt
        if self.hazard_marker is None and self.hazard_timer <= 0:
            self.hazard_marker, self.hazard_timer = self.combat.player.pos, 0.9
        elif self.hazard_marker is not None and self.hazard_timer <= 0:
            self.hazard_active, self.hazard_timer = 0.3, 4.5
        if self.hazard_active > 0:
            self.hazard_active = max(0, self.hazard_active - dt)
            resistant = "heatproof_gloves" in self.equipped if hazard == "fire" else "magic_resist_amulet" in self.equipped
            if self.combat.player.pos.distance(self.hazard_marker) < 65 and self.combat.player.hurt(1 if resistant else 2):
                self.combat.events.append(("hurt", self.combat.player.pos))
            if self.hazard_active == 0:
                self.hazard_marker = None
