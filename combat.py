"""순수 게임 로직: pico2d 없이 단위 테스트할 수 있다."""

import config as C
from geometry import Arena, Vec, path_hits
from player import Player
from afterimage import Trail, Slash
from enemy import Enemy
from device import Device
from projectile import Projectile
from types import SimpleNamespace


class Combat:
    def __init__(self, arena=None, player=None, dual_mode=False, purification=True, seal_break=False):
        self.arena = arena or Arena()
        self.player = player or Player()
        self.trail = None
        self.dual_mode = dual_mode
        self.purification = purification
        self.seal_break = seal_break
        self.echo_pos = None
        self.echo_remaining = 0.0
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
        self.defend_pos = None

    @property
    def ready(self):
        p = self.player
        return (p.hp > 0 and not p.dash_left and p.cooldown <= 0
                and (self.echo_pos is None if self.dual_mode else self.trail is None)
                and not any(not s.resolved for s in self.slashes))

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
        if self.dual_mode:
            self.echo_pos, self.echo_remaining = p.pos, p.trail_lifetime
        else:
            self.trail = Trail(p.pos, p.facing, p.trail_lifetime)
        self.events.append(("dash", p.pos))
        return True

    def slash(self):
        if self.dual_mode:
            if (self.player.hp <= 0 or self.player.dash_left > 0 or self.player.cooldown > 0
                    or any(not s.resolved for s in self.slashes)):
                return False
            points = [self.player.pos]
            if self.echo_pos is not None:
                points.append(self.echo_pos)
            boosted = len(points) > 1
            self.slashes.append(Slash(points, self.player.facing.normalized(),
                                      55 + self.player.upgrades["range"] * 7,
                                      boosted, style="dual"))
            self.echo_pos, self.echo_remaining = None, 0
            self.events.append(("slash", self.player.pos))
            return True
        if self.player.dash_left > 0 or self.player.cooldown > 0 or any(not s.resolved for s in self.slashes):
            return False
        if self.trail is None:
            self.slashes.append(Slash([self.player.pos], self.player.facing.normalized(),
                                      55 + self.player.upgrades["range"] * 7, style="direct"))
            self.events.append(("slash", self.player.pos))
            return True
        t = self.trail
        # 대시 경로를 약 6~9개의 공격 잔상으로 압축한다. 오래된 잔상부터 차례로 벤다.
        stride = max(1, (len(t.points) - 1) // 7)
        points = t.points[::stride]
        if points[-1] != t.points[-1]:
            points.append(t.points[-1])
        self.slashes.append(Slash(points, t.direction,
                                  self.player.slash_radius * (1.3 if self.prism else 1),
                                  self.prism, style="chain"))
        self.prism = False
        self.trail = None
        self.events.append(("slash", self.player.pos))
        return True

    def resolve(self, slash):
        hits, dead, weak = 0, 0, False
        def touches(pos, radius):
            if slash.style not in ("dual", "direct", "chain"):
                return path_hits(slash.points, pos, slash.radius + radius)
            if slash.style == "chain":
                return any(origin.distance(pos) <= slash.radius + radius for origin in slash.points)
            for origin in slash.points:
                delta = pos - origin
                distance = delta.length()
                if distance <= radius + 12 or (distance <= slash.radius + radius
                                                and delta.normalized().x * slash.direction.x
                                                + delta.normalized().y * slash.direction.y >= 0.35):
                    return True
            return False
        # 대상 객체당 한 번만 검사하므로 여러 경로 점에 겹쳐도 중복 피해가 없다.
        for enemy in self.enemies:
            boss_target = enemy.kind in ("guardian", "knight", "dragon")
            chain_boss = boss_target and slash.style == "chain"
            if (enemy.hp <= 0 or (enemy.uid in slash.hit_ids and not chain_boss)
                    or not touches(enemy.pos, enemy.radius)):
                continue
            landed = False
            if chain_boss and 0 < slash.boss_hits.get(enemy.uid, 0) < 3 and enemy.state == "weak":
                enemy.hp -= 1
                enemy.flash = 0.14
                landed = True
            elif enemy.uid not in slash.hit_ids:
                landed = enemy.receive_slash()
            if landed:
                slash.hit_ids.add(enemy.uid)
                if chain_boss:
                    slash.boss_hits[enemy.uid] = slash.boss_hits.get(enemy.uid, 0) + 1
                hits += 1
                weak = weak or boss_target
                self.events.append(("boss_hit" if boss_target else "hit", enemy.pos))
                if enemy.hp <= 0:
                    dead += 1
                    self.events.append(("kill", enemy.pos))
        # 연결 단자는 같은 참격 경로에 두 개가 함께 놓여야 반응한다.
        touched = [d for d in self.devices if d.uid not in slash.hit_ids and touches(d.pos, d.radius)]
        slash.pending_links.update(d.uid for d in touched if d.link)
        for device in touched:
            if device.link:
                continue
            if device.kind == "crystal" and not self.purification:
                continue
            device.receive_slash(2 if device.kind == "crystal" and self.seal_break else 1)
            slash.hit_ids.add(device.uid)
            hits += 1
            self.events.append(("hit", device.pos))
            if device.hp <= 0:
                dead += 1
                self.events.append(("crystal_break" if device.kind == "crystal" else "terminal_on", device.pos))
        self.devices = [d for d in self.devices if d.hp > 0]
        removed = [b for b in self.projectiles if self.purification and touches(b.pos, b.radius)]
        if removed:
            self.projectiles = [b for b in self.projectiles if b not in removed]
            hits += len(removed)
            self.events.extend(("hit", b.pos) for b in removed)
        self.kills += dead
        slash.boosted = slash.boosted or weak
        slash.total_hits = getattr(slash, "total_hits", 0) + hits
        self.last_hits = slash.total_hits
        self.max_hits = max(self.max_hits, self.last_hits)
        if slash.style != "chain":
            self.finish_slash(slash)
        self.enemies = [e for e in self.enemies if e.hp > 0]

    def finish_slash(self, slash):
        # 연결 단자는 한 차례의 연속 공격이 둘을 모두 지나야 켜진다.
        linked = {d.link for d in self.devices if d.link and
                  sum(other.link == d.link and other.uid in slash.pending_links for other in self.devices) >= 2}
        for device in self.devices:
            if device.link in linked and device.uid in slash.pending_links and device.uid not in slash.hit_ids:
                device.receive_slash()
                slash.hit_ids.add(device.uid)
                slash.total_hits = getattr(slash, "total_hits", 0) + 1
                self.kills += 1
                self.events.append(("terminal_on", device.pos))
        self.devices = [d for d in self.devices if d.hp > 0]
        hits = getattr(slash, "total_hits", 0)
        self.last_hits = hits
        self.max_hits = max(self.max_hits, hits)
        self.player.cooldown = (0.12 if slash.boosted else 0.34) if slash.style == "dual" else (
            0 if hits >= 2 or slash.boosted else C.SINGLE_COOLDOWN if hits else C.MISS_COOLDOWN)
        if hits >= 2 or slash.boosted:
            self.events.append(("recharge", self.player.pos))
        if hits >= 3:
            self.prism = True

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
            if self.dual_mode and self.echo_pos is not None:
                self.echo_remaining = max(0, self.echo_remaining - dt)
                if self.echo_remaining == 0:
                    self.echo_pos = None
        for enemy in self.enemies:
            previous_state = enemy.state
            target = SimpleNamespace(pos=self.defend_pos) if self.defend_pos is not None and enemy.kind == "wolf" else p
            enemy.update(dt, target, self.arena, self.enemies)
            if enemy.kind in ("guardian", "knight", "dragon") and enemy.state != previous_state:
                if enemy.kind == "dragon" and enemy.state == "attack" and enemy.attack == "breath":
                    self.events.append(("boss_breath", enemy.pos))
                elif enemy.kind == "dragon" and previous_state == "attack" and enemy.attack == "stomp":
                    self.events.append(("boss_impact", enemy.marker))
                elif previous_state == "charge" and enemy.state == "weak":
                    self.events.append(("boss_impact", enemy.pos))
            if getattr(enemy, "projectile_request", False):
                direction = enemy.direction.normalized()
                self.projectiles.append(Projectile(enemy.pos + direction * (enemy.radius + 12), direction * 240,
                                                   kind=enemy.kind))
                enemy.projectile_request = False
        self.projectiles = [b for b in self.projectiles if b.update(dt, self.arena)]
        for device in self.devices:
            device.flash = max(0, device.flash - dt)
        for slash in self.slashes:
            slash.age += dt
            if slash.style == "chain" and not slash.resolved:
                while slash.next_point < len(slash.points) and slash.age >= C.SLASH_HIT_TIME + slash.next_point * 0.045:
                    point = slash.points[slash.next_point]
                    slash.points, original = [point], slash.points
                    self.resolve(slash)
                    slash.points = original
                    self.events.append(("chain_hit", point))
                    slash.next_point += 1
                if slash.next_point == len(slash.points):
                    slash.resolved = True
                    self.finish_slash(slash)
            elif not slash.resolved and slash.age >= C.SLASH_HIT_TIME:
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
