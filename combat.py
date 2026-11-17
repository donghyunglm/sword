"""순수 게임 로직: pico2d 없이 단위 테스트할 수 있다."""

import config as C
from geometry import Arena, Vec, path_hits
from player import Player
from afterimage import Trail, Slash
from enemy import Enemy
from device import Device
from projectile import Projectile
from types import SimpleNamespace
from element_skill import ElementSkill
from final_dragon import FinalDragon


class Combat:
    def __init__(self, arena=None, player=None, dual_mode=False, purification=True, seal_break=False,
                 auto_echo=False):
        self.arena = arena or Arena()
        self.player = player or Player()
        self.trail = None
        self.dual_mode = dual_mode
        self.auto_echo = auto_echo
        self.auto_echo_timer = None
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
        self.element = None
        self.element_skill = ElementSkill()
        self.aim_target = None
        self.dash_direction = None
        self.parry_left = self.parry_cooldown = 0.0
        self.counter_left = 0.0
        self.counter_charges = 0
        self.counter_element = None
        self.backstab_ready = False

    @property
    def counter_active(self):
        return self.counter_left > 0 and self.counter_charges > 0

    @property
    def skill_element(self):
        if self.counter_active:
            return self.counter_element
        return self.element

    def parry(self):
        if (not any(isinstance(e, FinalDragon) for e in self.enemies) or self.player.hp <= 0
                or self.player.dash_left or self.parry_cooldown > 0):
            return False
        self.parry_left, self.parry_cooldown = 0.18, 0.75
        self.events.append(("parry_ready", self.player.pos))
        return True

    def hit_enemy(self, enemy, element, origin, direct=False):
        if not isinstance(enemy, FinalDragon):
            return enemy.receive_slash()
        old_shield = enemy.shield_hp
        landed = enemy.receive_attack(element or "soul")
        if old_shield > enemy.shield_hp:
            self.events.append(("shield_break" if enemy.shield_hp == 0 else "shield_hit", enemy.pos))
        if (landed and direct and self.backstab_ready and self.counter_left > 0
                and enemy.state == "stunned"):
            offset = (origin - enemy.pos).normalized()
            if offset.x * enemy.direction.x + offset.y * enemy.direction.y < -0.3:
                enemy.hp -= 3
                self.backstab_ready = False
                self.events.append(("backstab", enemy.pos))
        return landed

    @property
    def ready(self):
        p = self.player
        return (p.hp > 0 and not p.dash_left and (p.cooldown <= 0 or self.counter_active)
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

    def dash(self, direction=None):
        if not self.ready:
            return False
        p = self.player
        if self.counter_active:
            p.cooldown = 0
        self.dash_direction = (direction if direction is not None and direction.length() else p.facing).normalized()
        p.dash_left = C.DASH_TIME
        if self.dual_mode:
            self.echo_pos, self.echo_remaining = p.pos, p.trail_lifetime
        else:
            self.trail = Trail(p.pos, self.dash_direction, max(3.0, p.trail_lifetime) if self.skill_element else p.trail_lifetime,
                               self.skill_element, p.weapon)
        self.events.append(("dash", p.pos))
        return True

    def slash(self):
        if self.auto_echo or self.element or self.counter_left > 0:
            if (self.player.hp <= 0 or self.player.dash_left > 0 or self.player.cooldown > 0
                    or any(not s.resolved and s.style == "direct" for s in self.slashes)):
                return False
            self.slashes.append(Slash([self.player.pos], self.player.facing.normalized(),
                                      55 + self.player.upgrades["range"] * 7,
                                      style="direct", weapon=self.player.weapon))
            self.events.append(("slash", self.player.pos))
            return True
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
                                      boosted, style="dual", weapon=self.player.weapon, element=self.element))
            self.echo_pos, self.echo_remaining = None, 0
            self.events.append(("slash", self.player.pos))
            return True
        if self.player.dash_left > 0 or self.player.cooldown > 0 or any(not s.resolved for s in self.slashes):
            return False
        if self.trail is None:
            self.slashes.append(Slash([self.player.pos], self.player.facing.normalized(),
                                      55 + self.player.upgrades["range"] * 7, style="direct",
                                      weapon=self.player.weapon, element=self.element))
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
                                  self.prism, style="chain", weapon=self.player.weapon,
                                  element=t.element))
        self.prism = False
        self.trail = None
        self.events.append(("slash", self.player.pos))
        return True

    def release_auto_echo(self):
        if not self.trail:
            return
        trail = self.trail
        stride = max(1, (len(trail.points) - 1) // 7)
        points = trail.points[::stride]
        if points[-1] != trail.points[-1]:
            points.append(trail.points[-1])
        self.slashes.append(Slash(points, trail.direction, self.player.slash_radius,
                                  style="chain", weapon=trail.weapon, element=trail.element))
        self.trail = None
        self.auto_echo_timer = None
        self.events.append(("slash", points[0]))

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
            chain_boss = boss_target and slash.style == "chain" and not isinstance(enemy, FinalDragon)
            if (enemy.hp <= 0 or (enemy.uid in slash.hit_ids and not chain_boss)
                    or not touches(enemy.pos, enemy.radius)):
                continue
            if slash.weapon == 2 and enemy.uid not in slash.frost_ids and not isinstance(enemy, FinalDragon):
                if boss_target:
                    if enemy.state in ("approach", "tell"):
                        enemy.timer += 0.45
                else:
                    enemy.freeze_left = max(enemy.freeze_left, 0.55)
                    enemy.slow_left = max(enemy.slow_left, 2.2)
                    # 한 마리를 베더라도 근처의 무리를 묶어 대시 경로를 다시 설계할 시간을 준다.
                    for nearby in self.enemies:
                        if (nearby.uid != enemy.uid and nearby.hp > 0
                                and nearby.kind not in ("guardian", "knight", "dragon")
                                and nearby.pos.distance(enemy.pos) <= 105):
                            nearby.freeze_left = max(nearby.freeze_left, 0.55)
                            nearby.slow_left = max(nearby.slow_left, 2.2)
                            self.events.append(("frost", nearby.pos))
                slash.frost_ids.add(enemy.uid)
                self.events.append(("frost", enemy.pos))
            landed = False
            if chain_boss and 0 < slash.boss_hits.get(enemy.uid, 0) < 3 and enemy.state == "weak":
                enemy.hp -= 1
                enemy.flash = 0.14
                landed = True
            elif enemy.uid not in slash.hit_ids:
                element = slash.element or ("ice" if slash.weapon == 2 else "soul")
                landed = self.hit_enemy(enemy, element, slash.points[0], slash.style == "direct")
            if landed:
                if slash.weapon == 3 and enemy.uid not in slash.hit_ids and not isinstance(enemy, FinalDragon):
                    if boss_target or enemy.kind in ("boar", "sentinel"):
                        enemy.hp -= 1
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
            device.receive_slash(2 if device.kind == "crystal" and self.seal_break
                                 and slash.weapon == 3 else 1)
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
        if self.auto_echo and slash.style == "direct":
            self.player.cooldown = 0 if hits >= 2 else 0.20 if hits else 0.27
        if slash.weapon == 3:
            self.player.cooldown = max(self.player.cooldown, 0.70)
        if hits >= 2 or slash.boosted:
            self.events.append(("recharge", self.player.pos))
        if hits >= 3:
            self.prism = True

    def update(self, dt, movement=Vec()):
        self.elapsed += dt
        p = self.player
        if self.aim_target is not None and (self.aim_target - p.pos).length():
            p.facing = (self.aim_target - p.pos).normalized()
        p.cooldown = max(0, p.cooldown - dt)
        self.parry_cooldown = max(0, self.parry_cooldown - dt)
        self.counter_left = max(0, self.counter_left - dt)
        if self.counter_left == 0:
            self.counter_charges = 0
            self.backstab_ready = False
        p.invulnerable = max(0, p.invulnerable - dt)
        p.moving = movement.length() > 0 or p.dash_left > 0
        if p.dash_left > 0:
            active = min(dt, p.dash_left)
            p.pos, blocked = self.arena.move(p.pos, (self.dash_direction or p.facing) * (C.DASH_SPEED * active), p.radius, False)
            if self.trail:
                self.trail.record(p.pos)
            p.dash_left = max(0, p.dash_left - dt)
            if blocked:
                p.dash_left = 0
            if p.dash_left == 0 and self.trail:
                self.trail.finish()
                if self.auto_echo and not self.skill_element:
                    self.auto_echo_timer = 0.35
        else:
            if movement.length():
                if self.aim_target is None:
                    p.facing = movement.normalized()
                p.pos, _ = self.arena.move(p.pos, movement.normalized() * (p.speed * dt), p.radius)
            if self.trail:
                if self.auto_echo and self.auto_echo_timer is not None:
                    self.auto_echo_timer -= dt
                    if self.auto_echo_timer <= 0:
                        self.release_auto_echo()
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
        self.element_skill.update(dt, self)
        for device in self.devices:
            device.flash = max(0, device.flash - dt)
        for slash in self.slashes:
            slash.age += dt
            if slash.style == "chain" and not slash.resolved:
                interval = 0.06 if slash.weapon == 3 else 0.045
                while slash.next_point < len(slash.points) and slash.age >= C.SLASH_HIT_TIME + slash.next_point * interval:
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
            if (isinstance(enemy, FinalDragon) and enemy.state == "charge" and self.parry_left > 0
                    and p.dash_left <= 0 and p.pos.distance(enemy.pos) <= p.radius + enemy.radius + 8):
                self.counter_element = enemy.shield_element
                enemy.break_shield(parried=True)
                enemy.pos, _ = self.arena.move(enemy.pos, enemy.direction * -32, enemy.radius)
                self.counter_left, self.counter_charges = 2.0, 2
                self.backstab_ready = True
                self.parry_left = 0
                p.cooldown = 0
                p.invulnerable = max(p.invulnerable, 0.3)
                self.element_skill.cooldown = 0
                self.trail = None
                self.events.append(("parry_success", enemy.pos))
                continue
            if isinstance(enemy, FinalDragon) and enemy.state == "stunned":
                continue
            if p.pos.distance(enemy.pos) < p.radius + enemy.radius and p.hurt():
                self.events.append(("hurt", p.pos))
                knock = (p.pos - enemy.pos).normalized() * 35
                p.pos, _ = self.arena.move(p.pos, knock, p.radius)
            if getattr(enemy, "kind", "") == "dragon" and enemy.threatens(p.pos) and p.hurt():
                self.events.append(("hurt", p.pos))
        self.parry_left = max(0, self.parry_left - dt)
        for bullet in self.projectiles[:]:
            if p.pos.distance(bullet.pos) < p.radius + bullet.radius:
                if p.hurt():
                    self.events.append(("hurt", p.pos))
                self.projectiles.remove(bullet)
