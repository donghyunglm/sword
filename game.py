import copy
import config as C
from combat import Combat
from geometry import Vec
from player import Player
from boss import Guardian
from late_bosses import Knight, Dragon
from stage import load_stages, make_arena
from save_data import read_save, write_save, DEFAULT_PATH
from projectile import Projectile


class Game:
    def __init__(self, save_path=DEFAULT_PATH):
        self.stages = load_stages()
        self.save_path = save_path
        self.saved, self.notice = read_save(save_path)
        self.mode = "title"
        self.combat = Combat()
        self.index = 0
        self.cleared = []
        self.training = False
        self.trial = False
        self.selected_stage = 0
        self.paused = False
        self.wave_index = 0
        self.gate_open = False
        self.toast, self.toast_left = "", 0
        self.banner_left = 0
        self.stage_hits = 0
        self.round_start = None
        self.records = {"kills": 0, "hits": 0, "time": 0.0}
        self.hazard_timer = 3.5
        self.hazard_marker = None
        self.hazard_active = 0
        self.production_timer = 4.0
        self.production_counts = {}
        self.beacon_pos = Vec(560, 390)
        self.beacon_hp = 0
        self.beacon_timer = 1.0
        self.remote_timer = 2.4
        self.remote_shots = 0
        self.transit_progress = 0.0
        self.transit_x = 560.0

    @property
    def stage(self):
        return self.stages[self.index]

    def tell(self, message, duration=2.5):
        self.toast, self.toast_left = message, duration

    def snapshot(self, phase="play"):
        p = self.combat.player
        return {"version": 1, "stage": self.index, "phase": phase, "hp": max(1, p.hp),
                "upgrades": dict(p.upgrades), "cleared": list(self.cleared), "weapon": p.weapon}

    def persist(self, phase="play"):
        if self.training or self.trial:
            return
        data = self.snapshot(phase)
        try:
            write_save(data, self.save_path)
            self.saved = copy.deepcopy(data)
        except OSError:
            self.notice = "저장할 수 없습니다. 현재 게임은 계속할 수 있습니다."

    def load_stage(self, index, upgrades=None, hp=C.MAX_HP, persist=True, weapon=1):
        self.index = index
        stage = self.stage
        self.goal = stage["goal"] - (sum(kind == "wolf" for _, wave in stage["waves"] for kind, _, _ in wave)
                                     if index == 8 and 7 in self.cleared else 0)
        player = Player(pos=Vec(*stage["start"]), hp=hp)
        player.weapon = weapon if weapon in self.available_weapons(index) else 1
        if upgrades:
            player.upgrades = dict(upgrades)
        self.combat = Combat(make_arena(stage), player,
                             purification=index >= 5, seal_break=index >= 10)
        self.combat.defend_pos = self.beacon_pos if index == 1 else None
        self.beacon_hp = 8 if index == 1 else 0
        self.beacon_timer = 1.0
        self.remote_timer, self.remote_shots = 2.4, 0
        self.transit_progress, self.transit_x = 0.0, 560.0
        self.mode, self.paused = "play", False
        self.wave_index = 0
        self.gate_open = False
        self.stage_hits = 0
        self.banner_left = 2.8
        self.toast, self.toast_left = "", 0
        self.hazard_timer, self.hazard_marker, self.hazard_active = 3.5, None, 0
        self.production_timer, self.production_counts = 4.0, {}
        for device in stage.get("devices", []):
            kind, x, y = device[:3]
            self.combat.spawn_device(kind, Vec(x, y), device[3] if len(device) > 3 else "")
        if stage.get("boss"):
            self.combat.uid += 1
            boss_type = {True: Guardian, "knight": Knight, "dragon": Dragon}[stage["boss"]]
            self.combat.enemies.append(boss_type(self.combat.uid, Vec(560, 490)))
            if index == 14:
                # 성역의 공급 결정을 파괴한 결과가 최종 보스 체력에 남는다.
                destroyed = sum(i in self.cleared for i in (10, 12, 13))
                boss = self.combat.enemies[-1]
                boss.max_hp = max(12, boss.max_hp - destroyed * 2)
                boss.hp = boss.max_hp
        self.round_start = copy.deepcopy(self.snapshot())
        if index == 8 and 7 in self.cleared:
            self.tell("냉기 검 획득! 2번으로 전환 · 요새의 늑대 증원이 끊겼습니다.", 4)
        elif index == 10 and 9 in self.cleared:
            self.tell("파쇄 검 획득! 3번으로 전환해 성역의 결정을 깨세요.", 4)
        elif index == 14 and destroyed:
            self.tell(f"성역의 공급선 {destroyed}개를 끊어 드래곤의 체력이 약해졌습니다.", 4)
        if persist:
            self.persist()

    def new_game(self):
        self.training, self.trial, self.cleared = False, False, []
        self.records = {"kills": 0, "hits": 0, "time": 0.0}
        self.load_stage(0)

    def continue_game(self):
        if not self.saved:
            return False
        data = copy.deepcopy(self.saved)
        self.training, self.trial, self.cleared = False, False, data["cleared"]
        self.load_stage(data["stage"], data["upgrades"], data["hp"], persist=False,
                        weapon=data.get("weapon", 1))
        self.mode = data["phase"]
        self.gate_open = self.mode != "play"
        if self.mode == "transit":
            self.transit_progress, self.transit_x = 0.0, 560.0
        if self.mode != "play":
            self.combat.enemies = []
            self.combat.devices = []
            self.combat.projectiles = []
            self.combat.trail = None
        return True

    def start_training(self):
        self.training, self.trial, self.cleared = True, False, []
        self.load_stage(0, persist=False)
        self.combat.enemies = []
        self.combat.spawn("wolf", Vec(520, 350))
        self.combat.spawn("wolf", Vec(560, 365))
        self.combat.spawn("wolf", Vec(600, 350))
        self.combat.spawn("boar", Vec(800, 490))
        self.tell("연습장: 처치한 적이 다시 나타납니다. 저장 기록에는 영향을 주지 않습니다.", 5)

    def open_trial_select(self):
        if self.mode == "title":
            self.selected_stage = 0
            self.mode = "select"

    def start_trial(self, index):
        if self.mode != "select" or not 0 <= index < len(self.stages):
            return False
        self.training, self.trial = False, True
        self.cleared = list(range(index))
        levels = {key: 0 for key in C.UPGRADES}
        for i in range(min(index, C.UPGRADE_LIMIT * len(C.UPGRADES))):
            levels[C.UPGRADES[i % len(C.UPGRADES)]] += 1
        self.load_stage(index, levels, persist=False)
        self.tell("라운드 체험 중 · 기존 저장은 유지됩니다.", 3)
        return True

    def retry(self):
        if self.training:
            self.start_training()
            return
        if self.round_start:
            data = copy.deepcopy(self.round_start)
            self.cleared = data["cleared"]
            self.load_stage(data["stage"], data["upgrades"], data["hp"], weapon=data.get("weapon", 1))

    @staticmethod
    def available_weapons(index):
        return (1,) + ((2,) if index >= 8 else ()) + ((3,) if index >= 10 else ())

    def select_weapon(self, number):
        if self.mode != "play" or self.paused or number not in (1, 2, 3):
            return False
        if number not in self.available_weapons(self.index):
            self.tell("아직 획득하지 않은 무기입니다.")
            return False
        if self.combat.player.weapon != number:
            self.combat.player.weapon = number
            self.combat.events.append(("weapon_switch", self.combat.player.pos))
            self.tell({1: "기본 검", 2: "냉기 검 · 적 둔화", 3: "파쇄 검 · 느리지만 강력한 일격"}[number], 1.7)
        return True

    def exit_to_title(self):
        self.mode, self.paused = "title", False
        self.trial = False
        self.combat = Combat()
        self.saved, self.notice = read_save(self.save_path)

    def choose_upgrade(self, choice):
        if self.mode != "upgrade" or choice not in range(3):
            return False
        key = C.UPGRADES[choice]
        p = self.combat.player
        if p.upgrades[key] >= C.UPGRADE_LIMIT:
            self.tell("이미 최대 단계입니다. 다른 강화를 골라 주세요.")
            return False
        levels = dict(p.upgrades)
        levels[key] += 1
        p.upgrades, p.hp = levels, C.MAX_HP
        self.begin_transit()
        return True

    def skip_upgrade(self):
        if self.mode != "upgrade" or any(self.combat.player.upgrades[k] < C.UPGRADE_LIMIT for k in C.UPGRADES):
            return False
        self.combat.player.hp = C.MAX_HP
        self.begin_transit()
        return True

    def begin_transit(self):
        self.mode = "transit"
        self.transit_progress, self.transit_x = 0.0, 560.0
        self.combat.enemies.clear()
        self.combat.devices.clear()
        self.combat.projectiles.clear()
        self.combat.trail = None
        self.combat.slashes.clear()
        self.persist("transit")

    def enter_gate(self):
        if self.mode != "play" or not self.gate_open or self.training:
            return False
        if self.index not in self.cleared:
            self.cleared.append(self.index)
            self.records["kills"] += self.combat.kills
            self.records["time"] += self.combat.elapsed
            self.records["hits"] = max(self.records["hits"], self.combat.max_hits)
        self.combat.trail = None
        self.combat.slashes = []
        if self.index == len(self.stages) - 1:
            self.mode = "victory"
            self.persist("victory")
        elif self.index in (4, 9):
            self.mode = "upgrade"
            self.persist("upgrade")
        else:
            self.begin_transit()
        return True

    def update(self, dt, movement=Vec()):
        if self.mode == "transit":
            if movement.y > 0:
                self.transit_progress = min(1.0, self.transit_progress + movement.y * 200 * dt / 230)
                self.transit_x = max(475, min(645, self.transit_x + movement.x * 120 * dt))
                if self.transit_progress >= 1:
                    p = self.combat.player
                    self.load_stage(self.index + 1, p.upgrades, C.MAX_HP, weapon=p.weapon)
            return
        if self.paused or self.mode != "play":
            return
        self.toast_left = max(0, self.toast_left - dt)
        self.banner_left = max(0, self.banner_left - dt)
        if self.index == 12:
            self.remote_timer -= dt
            if self.remote_timer <= 0:
                self.remote_timer = 3.0
                origin = Vec(210 if self.remote_shots % 2 == 0 else 910, 605)
                velocity = (self.combat.player.pos - origin).normalized() * 310
                self.combat.projectiles.append(Projectile(origin, velocity, kind="dragon", radius=15))
                self.combat.events.append(("boss_breath", origin))
                self.remote_shots += 1
        self.combat.update(dt, movement)
        if self.index == 1:
            if any(e.kind == "wolf" and e.pos.distance(self.beacon_pos) < 43 for e in self.combat.enemies):
                self.beacon_timer -= dt
                if self.beacon_timer <= 0:
                    self.beacon_hp -= 1
                    self.beacon_timer = 0.9
                    self.combat.events.append(("beacon_hit", self.beacon_pos))
                    if self.beacon_hp <= 0:
                        self.mode = "defeat"
                        self.tell("이정표가 파괴되었습니다. 다시 도전하세요.", 4)
                        return
            else:
                self.beacon_timer = 1.0
        if self.stage.get("hazards"):
            self.hazard_timer -= dt
            if self.hazard_marker is None and self.hazard_timer <= 0:
                self.hazard_marker = self.combat.player.pos
                self.hazard_timer = 0.9
            elif self.hazard_marker is not None and self.hazard_timer <= 0:
                self.hazard_active = 0.3
                self.hazard_timer = 4.0
            if self.hazard_active > 0:
                self.hazard_active = max(0, self.hazard_active - dt)
                if self.combat.player.pos.distance(self.hazard_marker) < 78 and self.combat.player.hurt():
                    self.combat.events.append(("hurt", self.combat.player.pos))
                if self.hazard_active == 0:
                    self.hazard_marker = None
        if self.combat.player.hp <= 0:
            self.mode = "defeat"
            return
        if self.training:
            if len(self.combat.enemies) < 4 and int(self.combat.elapsed * 120) % 120 == 0:
                kind = "boar" if self.combat.uid % 4 == 3 else "wolf"
                x = (230, 430, 690, 890)[self.combat.uid % 4]
                self.combat.spawn(kind, Vec(x, 510))
            return
        waves = self.stage["waves"]
        while self.wave_index < len(waves) and self.combat.elapsed >= waves[self.wave_index][0]:
            for kind, x, y in waves[self.wave_index][1]:
                # 생산지를 정화했다면 다음 통로의 요새 병력이 일부 사라진다.
                if self.index == 8 and 7 in self.cleared and kind == "wolf":
                    continue
                self.combat.spawn(kind, Vec(x, y))
            self.wave_index += 1
        if self.index == 7 and self.combat.devices:
            self.production_timer -= dt
            if self.production_timer <= 0:
                self.production_timer = 5.0
                for crystal in self.combat.devices:
                    if crystal.kind != "crystal" or self.production_counts.get(crystal.uid, 0) >= 2:
                        continue
                    kind = "wolf" if crystal.pos.x < 400 else "mage" if crystal.pos.x < 700 else "sentinel"
                    spawn_pos = Vec(crystal.pos.x, crystal.pos.y - 75)
                    if self.combat.arena.valid(spawn_pos, 20):
                        self.combat.spawn(kind, spawn_pos)
                        self.production_counts[crystal.uid] = self.production_counts.get(crystal.uid, 0) + 1
                        self.combat.events.append(("production", crystal.pos))
        if (not self.gate_open and self.wave_index == len(waves)
                and not self.combat.enemies and not self.combat.devices
                and self.combat.kills >= self.goal):
            self.gate_open = True
            self.tell("봉인 해제! 위쪽 빛의 문으로 이동하세요.", 4)
            self.combat.events.append(("open", Vec(560, 606)))
        if self.gate_open and self.combat.player.pos.distance(Vec(560, 604)) < 37:
            self.enter_gate()
