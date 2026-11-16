from dataclasses import dataclass
import config as C


class Trail:
    """실제 이동 구간을 일정 거리 간격으로 보간한다. 표시 잔영은 그 일부만 사용."""

    def __init__(self, origin, direction, lifetime):
        self.points = [origin]
        self.direction = direction
        self.remaining = lifetime
        self.lifetime = lifetime
        self.last = origin
        self.remainder = 0.0

    def record(self, pos):
        delta = pos - self.last
        distance = delta.length()
        if distance:
            direction = delta.normalized()
            step = C.TRAIL_SPACING - self.remainder
            while step <= distance + 1e-8:
                self.points.append(self.last + direction * step)
                step += C.TRAIL_SPACING
            self.remainder = (self.remainder + distance) % C.TRAIL_SPACING
        self.last = pos

    def finish(self):
        if self.points[-1].distance(self.last) > 1:
            self.points.append(self.last)

    def visible_points(self):
        return self.points[::2] + ([self.points[-1]] if len(self.points) % 2 == 0 else [])


@dataclass
class Slash:
    points: list
    direction: object
    radius: float
    boosted: bool = False
    age: float = 0
    resolved: bool = False
    style: str = "trail"
    weapon: int = 1
    next_point: int = 0
    hit_ids: object = None
    pending_links: object = None
    boss_hits: object = None
    frost_ids: object = None

    def __post_init__(self):
        self.hit_ids = set() if self.hit_ids is None else self.hit_ids
        self.pending_links = set() if self.pending_links is None else self.pending_links
        self.boss_hits = {} if self.boss_hits is None else self.boss_hits
        self.frost_ids = set() if self.frost_ids is None else self.frost_ids

    @property
    def alive(self):
        interval = 0.06 if self.weapon == 3 else 0.045
        return self.age < (0.20 + len(self.points) * interval if self.style == "chain" else 0.27)
