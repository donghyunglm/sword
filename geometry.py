"""렌더링에 의존하지 않는 좌표와 충돌 계산. 좌표 원점은 화면 왼쪽 아래."""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Vec:
    x: float = 0.0
    y: float = 0.0

    def __add__(self, other):
        return Vec(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return Vec(self.x - other.x, self.y - other.y)

    def __mul__(self, scale):
        return Vec(self.x * scale, self.y * scale)

    def length(self):
        return math.hypot(self.x, self.y)

    def normalized(self):
        size = self.length()
        return self * (1 / size) if size else Vec()

    def distance(self, other):
        return (self - other).length()


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    w: float
    h: float

    def touches_circle(self, p, radius):
        nearest = Vec(max(self.x, min(p.x, self.x + self.w)),
                      max(self.y, min(p.y, self.y + self.h)))
        return nearest.distance(p) < radius


class Arena:
    bounds = Rect(40, 108, 1040, 516)

    def __init__(self, walls=()):
        self.walls = list(walls)

    def valid(self, p, radius):
        b = self.bounds
        return (b.x + radius <= p.x <= b.x + b.w - radius
                and b.y + radius <= p.y <= b.y + b.h - radius
                and not any(w.touches_circle(p, radius) for w in self.walls))

    def move(self, start, delta, radius, slide=True):
        """5px 이하의 작은 구간으로 검사해 저프레임의 벽 관통도 방지한다."""
        steps = max(1, math.ceil(delta.length() / 5))
        step = delta * (1 / steps)
        p, blocked = start, False
        for _ in range(steps):
            candidate = p + step
            if self.valid(candidate, radius):
                p = candidate
                continue
            blocked = True
            if not slide:
                break
            px, py = p + Vec(step.x, 0), p + Vec(0, step.y)
            if self.valid(px, radius):
                p = px
            py = p + Vec(0, step.y)
            if self.valid(py, radius):
                p = py
        return p, blocked


def path_hits(points, target, radius):
    if any(p.distance(target) <= radius for p in points):
        return True
    for a, b in zip(points, points[1:]):
        delta = b - a
        length2 = delta.x * delta.x + delta.y * delta.y
        if length2:
            t = max(0, min(1, ((target.x - a.x) * delta.x + (target.y - a.y) * delta.y) / length2))
            if (a + delta * t).distance(target) <= radius:
                return True
    return False
