"""요새 기사와 성역 드래곤. 예고된 공격 직후에만 잔영 참격이 통한다."""

from dataclasses import dataclass, field
from geometry import Vec


@dataclass
class Knight:
    uid: int
    pos: Vec
    kind: str = "knight"
    radius: float = 30
    hp: int = 14
    max_hp: int = 14
    state: str = "approach"
    timer: float = 1.0
    flash: float = 0
    direction: Vec = field(default_factory=lambda: Vec(0, -1))
    weak_used: bool = False
    cycles: int = 0
    charge_distance: float = 0
    projectile_request: bool = False

    def update(self, dt, player, arena, others=()):
        self.flash = max(0, self.flash - dt)
        self.timer -= dt
        if self.state == "approach":
            self.direction = (player.pos - self.pos).normalized()
            if self.pos.distance(player.pos) > 180:
                self.pos, _ = arena.move(self.pos, self.direction * (86 * dt), self.radius)
            if self.timer <= 0:
                self.direction = (player.pos - self.pos).normalized()
                self.state, self.timer = "tell", 0.78
                self.charge_distance = min(270, self.pos.distance(player.pos) + 18)
        elif self.state == "tell" and self.timer <= 0:
            if self.cycles % 2:
                self.projectile_request = True
                self.state, self.timer, self.weak_used = "weak", 0.95, False
            else:
                self.state, self.timer = "charge", 0.5
        elif self.state == "charge":
            distance = min(self.charge_distance, 530 * dt)
            self.pos, blocked = arena.move(self.pos, self.direction * distance, self.radius, False)
            self.charge_distance = max(0, self.charge_distance - distance)
            if self.timer <= 0 or blocked or self.charge_distance <= 0:
                self.state, self.timer, self.weak_used = "weak", 1.05, False
        elif self.state == "weak" and self.timer <= 0:
            self.state, self.timer = "recover", 0.5
        elif self.state == "recover" and self.timer <= 0:
            self.cycles += 1
            self.state, self.timer = "approach", 0.65

    def receive_slash(self):
        if self.state != "weak" or self.weak_used:
            return False
        self.hp -= 2
        self.flash, self.weak_used = 0.2, True
        return True


@dataclass
class Dragon:
    uid: int
    pos: Vec
    kind: str = "dragon"
    radius: float = 48
    hp: int = 20
    max_hp: int = 20
    state: str = "approach"
    timer: float = 0.9
    flash: float = 0
    direction: Vec = field(default_factory=lambda: Vec(0, -1))
    weak_used: bool = False
    cycles: int = 0
    marker: Vec = field(default_factory=Vec)
    attack: str = "stomp"
    hazard_time: float = 0

    def update(self, dt, player, arena, others=()):
        self.flash = max(0, self.flash - dt)
        self.hazard_time = max(0, self.hazard_time - dt)
        self.timer -= dt
        if self.state == "approach" and self.timer <= 0:
            self.attack = "stomp" if self.cycles % 2 == 0 else "breath"
            self.marker = player.pos if self.attack == "stomp" else self.pos
            self.direction = (player.pos - self.pos).normalized()
            self.state, self.timer = "tell", 0.9
        elif self.state == "tell" and self.timer <= 0:
            self.state, self.timer = "attack", 0.32
            self.hazard_time = 0.32
        elif self.state == "attack" and self.timer <= 0:
            self.state, self.timer, self.weak_used = "weak", 1.3, False
        elif self.state == "weak" and self.timer <= 0:
            self.state, self.timer = "recover", 0.4
        elif self.state == "recover" and self.timer <= 0:
            self.cycles += 1
            self.state, self.timer = "approach", 0.5

    def threatens(self, pos):
        if self.hazard_time <= 0:
            return False
        if self.attack == "stomp":
            return pos.distance(self.marker) < 90
        offset = pos - self.pos
        along = offset.x * self.direction.x + offset.y * self.direction.y
        across = abs(offset.x * self.direction.y - offset.y * self.direction.x)
        return 0 < along < 440 and across < 56

    def receive_slash(self):
        if self.state != "weak" or self.weak_used:
            return False
        self.hp -= 2
        self.flash, self.weak_used = 0.2, True
        return True
