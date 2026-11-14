"""수호수: 추적, 방향 예고, 직선 돌진, 짧은 약점 창, 회복."""

from dataclasses import dataclass, field
from geometry import Vec


@dataclass
class Guardian:
    uid: int
    pos: Vec
    kind: str = "guardian"
    radius: float = 38
    hp: int = 16
    max_hp: int = 16
    state: str = "approach"
    timer: float = 1.2
    flash: float = 0
    direction: Vec = field(default_factory=lambda: Vec(0, -1))
    weak_used: bool = False
    cycles: int = 0

    def update(self, dt, player, arena, others=()):
        self.flash = max(0, self.flash - dt)
        self.timer -= dt
        if self.state == "approach":
            self.direction = (player.pos - self.pos).normalized()
            if self.pos.distance(player.pos) > 220:
                self.pos, _ = arena.move(self.pos, self.direction * (68 * dt), self.radius)
            if self.timer <= 0:
                self.direction = (player.pos - self.pos).normalized()
                self.state, self.timer = "tell", 0.75
        elif self.state == "tell":
            if self.timer <= 0:
                self.state, self.timer = "charge", 0.5
        elif self.state == "charge":
            self.pos, blocked = arena.move(self.pos, self.direction * (580 * dt), self.radius, False)
            if self.timer <= 0 or blocked:
                self.state, self.timer, self.weak_used = "weak", 1.1, False
        elif self.state == "weak":
            if self.timer <= 0:
                self.state, self.timer = "recover", 0.65
        elif self.state == "recover" and self.timer <= 0:
            self.cycles += 1
            self.state, self.timer = "approach", 0.8

    def receive_slash(self):
        if self.state != "weak" or self.weak_used:
            return False
        self.hp -= 2
        self.flash, self.weak_used = 0.2, True
        return True
