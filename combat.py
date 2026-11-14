"""순수 게임 로직: pico2d 없이 단위 테스트할 수 있다."""

import config as C
from geometry import Arena, Vec, path_hits
from player import Player
from afterimage import Trail, Slash
from enemy import Enemy
from device import Device
from projectile import Projectile


class Combat:
    def __init__(self, arena=None, player=None):
        self.arena = arena or Arena()
        self.player = player or Player()
        self.trail = None
        self.slashes = []
        self.enemies = []
        self.devices = []
        self.projectiles = []
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

    def spawn_device(self, kind, pos, link=""):
        self.uid += 1
        device = Device.make(self.uid, kind, pos, link)
        self.devices.append(device)
        return device

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
                weak = weak or enemy.kind in ("guardian", "knight", "dragon")
                self.events.append(("hit", enemy.pos))
                if enemy.hp <= 0:
                    dead += 1
                    self.events.append(("kill", enemy.pos))
        # 연결 단자는 같은 참격 경로에 두 개가 함께 놓여야 반응한다.
        touched = [d for d in self.devices if path_hits(slash.points, d.pos, slash.radius + d.radius)]
        links = {d.link for d in touched if d.link and sum(other.link == d.link for other in touched) >= 2}
        for device in touched:
            if device.link and device.link not in links:
                continue
            device.receive_slash()
            hits += 1
            self.events.append(("hit", device.pos))
            if device.hp <= 0:
                dead += 1
                self.events.append(("kill", device.pos))
        self.devices = [d for d in self.devices if d.hp > 0]
        removed = [b for b in self.projectiles if path_hits(slash.points, b.pos, slash.radius + b.radius)]
        if removed:
            self.projectiles = [b for b in self.projectiles if b not in removed]
            hits += len(removed)
            self.events.extend(("hit", b.pos) for b in removed)
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
        p.moving = movement.length() > 0 or p.dash_left > 0
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
            if getattr(enemy, "projectile_request", False):
                direction = enemy.direction.normalized()
                self.projectiles.append(Projectile(enemy.pos + direction * (enemy.radius + 12), direction * 240))
                enemy.projectile_request = False
        self.projectiles = [b for b in self.projectiles if b.update(dt, self.arena)]
        for device in self.devices:
            device.flash = max(0, device.flash - dt)
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
            if getattr(enemy, "kind", "") == "dragon" and enemy.threatens(p.pos) and p.hurt():
                self.events.append(("hurt", p.pos))
        for bullet in self.projectiles[:]:
            if p.pos.distance(bullet.pos) < p.radius + bullet.radius:
                if p.hurt():
                    self.events.append(("hurt", p.pos))
                self.projectiles.remove(bullet)
