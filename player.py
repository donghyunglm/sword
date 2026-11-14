from dataclasses import dataclass, field
import config as C
from geometry import Vec


@dataclass
class Player:
    pos: Vec = field(default_factory=lambda: Vec(560, 180))
    facing: Vec = field(default_factory=lambda: Vec(0, 1))
    radius: float = 14
    hp: int = C.MAX_HP
    invulnerable: float = 0
    dash_left: float = 0
    cooldown: float = 0
    upgrades: dict = field(default_factory=lambda: dict.fromkeys(C.UPGRADES, 0))

    @property
    def speed(self):
        return C.PLAYER_SPEED * (1 + self.upgrades["speed"] * 0.09)

    @property
    def slash_radius(self):
        return C.SLASH_RADIUS + self.upgrades["range"] * 7

    @property
    def trail_lifetime(self):
        return C.TRAIL_LIFETIME + self.upgrades["lifetime"] * 0.2

    def hurt(self, amount=1):
        if self.invulnerable > 0 or self.dash_left > 0:
            return False
        self.hp = max(0, self.hp - amount)
        self.invulnerable = 1.0
        return True
