"""순수 게임 로직: pico2d 없이 단위 테스트할 수 있다."""

import config as C
from geometry import Arena, Vec, path_hits
from player import Player
from afterimage import Trail, Slash
from enemy import Enemy


class Combat:
    def __init__(self, arena=None, player=None):
        self.arena = arena or Arena()
        self.player = player or Player()
        self.trail = None
        self.slashes = []
        self.enemies = []
        self.events = []
        self.elapsed = 0.0
        self.kills = 0
        self.max_hits = 0
        self.prism = False
        self.last_hits = 0
        self.uid = 0

    @property
    def ready(self):
        p = self.player
        return (p.hp > 0 and not p.dash_left and p.cooldown <= 0
                and self.trail is None and not any(not s.resolved for s in self.slashes))

    def spawn(self, kind, pos):
        self.uid += 1
        e = Enemy.make(self.uid, kind, pos)
        self.enemies.append(e)
        return e

    def dash(self):
        if not self.ready:
            return False
        p = self.player
        p.dash_left = C.DASH_TIME
        self.trail = Trail(p.pos, p.facing, p.trail_lifetime)
        self.events.append(("dash", p.pos))
        return True

    def slash(self):
        if self.trail is None or self.player.dash_left > 0:
            return False
        t = self.trail
        self.slashes.append(Slash(list(t.points), t.direction,
                                  self.player.slash_radius * (1.3 if self.prism else 1), self.prism))
        self.prism = False
        self.trail = None
        self.events.append(("slash", self.player.pos))
        return True

    def resolve(self, slash):
        hits, dead, weak = 0, 0, False
        # 대상 객체당 한 번만 검사하므로 여러 경로 점에 겹쳐도 중복 피해가 없다.
        for enemy in self.enemies:
            if enemy.hp <= 0 or not path_hits(slash.points, enemy.pos, slash.radius + enemy.radius):
                continue
            if enemy.receive_slash():
                hits += 1
                weak = weak or enemy.kind == "guardian"
                self.events.append(("hit", enemy.pos))
                if enemy.hp <= 0:
                    dead += 1
                    self.events.append(("kill", enemy.pos))
        self.kills += dead
        self.last_hits = hits
        self.max_hits = max(self.max_hits, hits)
        self.player.cooldown = 0 if hits >= 2 or weak else C.SINGLE_COOLDOWN if hits else C.MISS_COOLDOWN
        if hits >= 2 or weak:
            self.events.append(("recharge", self.player.pos))
        if dead >= 3:
            self.prism = True
        self.enemies = [e for e in self.enemies if e.hp > 0]

    def update(self, dt, movement=Vec()):
        self.elapsed += dt
        p = self.player
        p.cooldown = max(0, p.cooldown - dt)
        p.invulnerable = max(0, p.invulnerable - dt)
        if p.dash_left > 0:
            active = min(dt, p.dash_left)
            p.pos, blocked = self.arena.move(p.pos, p.facing * (C.DASH_SPEED * active), p.radius, False)
            if self.trail:
                self.trail.record(p.pos)
            p.dash_left = max(0, p.dash_left - dt)
            if blocked:
                p.dash_left = 0
            if p.dash_left == 0 and self.trail:
                self.trail.finish()
        else:
            if movement.length():
                p.facing = movement.normalized()
                p.pos, _ = self.arena.move(p.pos, p.facing * (p.speed * dt), p.radius)
            if self.trail:
                self.trail.remaining -= dt
                if self.trail.remaining <= 0:
                    self.trail = None
                    p.cooldown = C.MISS_COOLDOWN
                    self.events.append(("expire", p.pos))
        for enemy in self.enemies:
            enemy.update(dt, p, self.arena, self.enemies)
        for slash in self.slashes:
            slash.age += dt
            if not slash.resolved and slash.age >= C.SLASH_HIT_TIME:
                slash.resolved = True
                self.resolve(slash)
        self.slashes = [s for s in self.slashes if s.alive]
        for enemy in self.enemies:
            if p.pos.distance(enemy.pos) < p.radius + enemy.radius and p.hurt():
                self.events.append(("hurt", p.pos))
                knock = (p.pos - enemy.pos).normalized() * 35
                p.pos, _ = self.arena.move(p.pos, knock, p.radius)
