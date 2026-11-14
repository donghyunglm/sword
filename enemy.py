from dataclasses import dataclass, field
from geometry import Vec


@dataclass
class Enemy:
    uid: int
    kind: str
    pos: Vec
    hp: int = 1
    radius: float = 16
    state: str = "chase"
    timer: float = 0
    flash: float = 0
    attack_wait: float = 0.7
    direction: Vec = field(default_factory=Vec)

    @classmethod
    def make(cls, uid, kind, pos):
        return cls(uid, kind, pos, hp=2 if kind == "boar" else 1,
                   radius=20 if kind == "boar" else 16)

    def update(self, dt, player, arena, others=()):
        self.flash = max(0, self.flash - dt)
        self.attack_wait = max(0, self.attack_wait - dt)
        delta = player.pos - self.pos
        if self.state == "tell":
            self.timer -= dt
            if self.timer <= 0:
                self.state, self.timer = "charge", 0.46
            return
        if self.state == "charge":
            self.pos, blocked = arena.move(self.pos, self.direction * (480 * dt), self.radius, False)
            self.timer -= dt
            if self.timer <= 0 or blocked:
                self.state, self.timer = "recover", 0.7
            return
        if self.state == "recover":
            self.timer -= dt
            if self.timer <= 0:
                self.state, self.attack_wait = "chase", 1.1
            return
        if self.kind == "boar" and delta.length() < 290 and self.attack_wait <= 0:
            self.state, self.timer, self.direction = "tell", 0.65, delta.normalized()
            return
        desired = delta.normalized()
        # 가까운 적이 정확히 포개지지 않도록 약하게 밀어낸다.
        separation = Vec()
        for e in others:
            d = self.pos - e.pos
            if e.uid != self.uid and 0.01 < d.length() < self.radius + e.radius + 4:
                separation = separation + d.normalized() * 0.5
        desired = (desired + separation).normalized()
        speed = 112 if self.kind == "wolf" else 83
        proposed, _ = arena.move(self.pos, desired * (speed * dt), self.radius)
        if proposed.distance(self.pos) < speed * dt * 0.2 and delta.length() > 45:
            # 초기의 단순한 장애물에 대한 국소 우회. 고급 길 찾기는 사용하지 않는다.
            perpendicular = Vec(-desired.y, desired.x)
            options = [arena.move(self.pos, perpendicular * (sign * speed * dt), self.radius)[0]
                       for sign in (-1, 1)]
            proposed = min(options, key=lambda p: p.distance(player.pos))
        self.direction = desired
        self.pos = proposed

    def receive_slash(self):
        damage = 2 if self.kind == "boar" and self.state in ("charge", "recover") else 1
        self.hp -= damage
        self.flash = 0.14
        return True
