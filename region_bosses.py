"""지역 수호자: 공통 패링 규칙을 사용하되 핵과 탄환·갑주는 구분한다."""
import math
from final_dragon import FinalDragon
from projectile import Projectile
from geometry import Vec


class RegionBoss(FinalDragon):
    def __init__(self, uid, pos, variant):
        super().__init__(uid, pos)
        self.sprite_key = variant
        self.name = {"fire_guardian": "불타는 지킴이", "ice_guardian": "얼음 수호수", "knight": "성문 수호기사"}[variant]
        self.hp = self.max_hp = {"fire_guardian": 18, "ice_guardian": 22, "knight": 20}[variant]
        self.shield_element = "fire" if variant == "ice_guardian" else "soul"
        self.next_element = self.shield_element
        self.elements = [self.shield_element]
        self.shots = []

    def update(self, dt, player, arena, others=()):
        previous = self.state
        super().update(dt, player, arena, others)
        if self.state == "attack" and previous != "attack":
            self.attack = "nova"
            kind = "frost" if self.sprite_key == "ice_guardian" else "ember"
            for i in range(8):
                theta = i * math.tau / 8 + (self.cycles % 2) * 0.15
                direction = Vec(math.cos(theta), math.sin(theta))
                self.shots.append(Projectile(self.pos + direction * (self.radius + 14), direction * 175,
                                              radius=11, kind=kind))

    def threatens(self, pos):
        return False


class FrozenGate:
    def __init__(self, pos, arena, opened=False):
        from geometry import Rect
        self.pos, self.opened, self.arena = pos, opened, arena
        self.radius = 47
        self.wall = Rect(pos.x - 60, pos.y - 16, 120, 32)
        if not opened:
            arena.walls.append(self.wall)

    def receive(self, element):
        if self.opened or element != "fire":
            return False
        self.opened = True
        if self.wall in self.arena.walls:
            self.arena.walls.remove(self.wall)
        return True
