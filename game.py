import copy
import config as C
from combat import Combat
from geometry import Vec
from player import Player
from boss import Guardian
from late_bosses import Knight, Dragon
from stage import load_stages, make_arena
from save_data import read_save, write_save, DEFAULT_PATH


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

    @property
    def stage(self):
        return self.stages[self.index]

    def tell(self, message, duration=2.5):
        self.toast, self.toast_left = message, duration

    def snapshot(self, phase="play"):
        p = self.combat.player
        return {"version": 1, "stage": self.index, "phase": phase, "hp": max(1, p.hp),
                "upgrades": dict(p.upgrades), "cleared": list(self.cleared)}

    def persist(self, phase="play"):
        if self.training or self.trial:
            return
        data = self.snapshot(phase)
        try:
            write_save(data, self.save_path)
            self.saved = copy.deepcopy(data)
        except OSError:
            self.notice = "저장할 수 없습니다. 현재 게임은 계속할 수 있습니다."

    def load_stage(self, index, upgrades=None, hp=C.MAX_HP, persist=True):
        self.index = index
        stage = self.stage
        player = Player(pos=Vec(*stage["start"]), hp=hp)
        if upgrades:
            player.upgrades = dict(upgrades)
        self.combat = Combat(make_arena(stage), player)
        self.mode, self.paused = "play", False
        self.wave_index = 0
        self.gate_open = False
        self.stage_hits = 0
        self.banner_left = 2.8
        self.toast, self.toast_left = "", 0
        self.hazard_timer, self.hazard_marker, self.hazard_active = 3.5, None, 0
        for device in stage.get("devices", []):
            kind, x, y = device[:3]
            self.combat.spawn_device(kind, Vec(x, y), device[3] if len(device) > 3 else "")
        if stage.get("boss"):
            self.combat.uid += 1
            boss_type = {True: Guardian, "knight": Knight, "dragon": Dragon}[stage["boss"]]
            self.combat.enemies.append(boss_type(self.combat.uid, Vec(560, 490)))
        self.round_start = copy.deepcopy(self.snapshot())
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
        self.load_stage(data["stage"], data["upgrades"], data["hp"], persist=False)
        self.mode = data["phase"]
        self.gate_open = self.mode != "play"
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
            self.load_stage(data["stage"], data["upgrades"], data["hp"])

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
        hp = C.MAX_HP
        self.load_stage(self.index + 1, levels, hp)
        return True

    def skip_upgrade(self):
        if self.mode != "upgrade" or any(self.combat.player.upgrades[k] < C.UPGRADE_LIMIT for k in C.UPGRADES):
            return False
        self.load_stage(self.index + 1, self.combat.player.upgrades, C.MAX_HP)
        return True

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
        self.mode = "victory" if self.index == len(self.stages) - 1 else "upgrade"
        self.persist(self.mode)
        return True

    def update(self, dt, movement=Vec()):
        if self.paused or self.mode != "play":
            return
        self.toast_left = max(0, self.toast_left - dt)
        self.banner_left = max(0, self.banner_left - dt)
        self.combat.update(dt, movement)
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
                self.combat.spawn(kind, Vec(x, y))
            self.wave_index += 1
        if (not self.gate_open and self.wave_index == len(waves)
                and not self.combat.enemies and not self.combat.devices
                and self.combat.kills >= self.stage["goal"]):
            self.gate_open = True
            self.tell("봉인 해제! 위쪽 빛의 문으로 이동하세요.", 4)
            self.combat.events.append(("open", Vec(560, 606)))
        if self.gate_open and self.combat.player.pos.distance(Vec(560, 604)) < 37:
            self.enter_gate()
