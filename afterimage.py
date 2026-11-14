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
        n = len(self.points)
        return [self.points[i] for i in sorted({round(i * (n - 1) / 3) for i in range(4)})]


@dataclass
class Slash:
    points: list
    direction: object
    radius: float
    boosted: bool = False
    age: float = 0
    resolved: bool = False

    @property
    def alive(self):
        return self.age < 0.27
