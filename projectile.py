"""마법사의 느린 구체. 잔영 참격으로 제거할 수 있다."""

from dataclasses import dataclass
from geometry import Vec


@dataclass
class Projectile:
    pos: Vec
    velocity: Vec
    lifetime: float = 3.2
    radius: float = 9

    def update(self, dt, arena):
        self.pos = self.pos + self.velocity * dt
        self.lifetime -= dt
        return self.lifetime > 0 and arena.valid(self.pos, self.radius)
