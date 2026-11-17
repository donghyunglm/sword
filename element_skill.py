"""잔영을 소모하는 원소 원거리 공격. 적 탄환과 독립적으로 갱신한다."""
from projectile import Projectile
from geometry import path_hits


class ElementSkill:
    def __init__(self):
        self.cooldown = 0.0
        self.pending = []
        self.timer = 0.0
        self.bolts = []

    def cast(self, combat, direction, target=None):
        bonus = combat.counter_active
        if (not combat.skill_element or not combat.trail or combat.player.dash_left
                or (self.cooldown > 0 and not bonus) or (self.pending and not bonus) or combat.player.hp <= 0):
            return False
        points = combat.trail.visible_points()
        if len(points) > 6:
            points = [points[round(i * (len(points) - 1) / 5)] for i in range(6)]
        if combat.skill_element == "fire" and not bonus and combat.arrows is not None:
            if combat.arrows < len(points):
                combat.events.append(("no_arrows", combat.player.pos))
                return False
            combat.arrows -= len(points)
        # 마우스 조준은 각 잔영의 위치에서 클릭한 지점으로 향한다.
        # 키보드/자동 검증 호출은 기존 방향 지정도 사용할 수 있다.
        self.pending.extend((pos, (target - pos).normalized() if target is not None
                             and (target - pos).length() > 1 else direction.normalized(), combat.skill_element)
                            for pos in points)
        combat.trail = None
        combat.auto_echo_timer = None
        self.timer = 0.0
        self.cooldown = 2.5 if combat.skill_element == "fire" else 3.0
        if bonus:
            combat.counter_charges -= 1
            combat.player.cooldown = 0
            if combat.counter_charges > 0:
                self.cooldown = 0
        return True

    def update(self, dt, combat):
        self.cooldown = max(0, self.cooldown - dt)
        self.timer -= dt
        while self.pending and self.timer <= 0:
            pos, direction, element = self.pending.pop(0)
            self.bolts.append(Projectile(pos, direction * 440, lifetime=1.8, radius=10, kind=element))
            combat.events.append(("element_" + element, pos))
            self.timer += 0.09
        survivors = []
        for bolt in self.bolts:
            old = bolt.pos
            destination = bolt.pos + bolt.velocity * dt
            gate = next((g for g in combat.shot_targets if not g.opened
                         and path_hits([old, destination], g.pos, g.radius + bolt.radius)), None)
            if gate is not None:
                if gate.receive(bolt.kind):
                    combat.events.append(("gate_melt", gate.pos))
                continue
            if not bolt.update(dt, combat.arena):
                combat.events.append(("element_" + bolt.kind, bolt.pos))
                continue
            target = next((e for e in sorted(combat.enemies, key=lambda e: e.pos.distance(old))
                           if e.hp > 0 and path_hits([old, bolt.pos], e.pos, e.radius + bolt.radius)), None)
            if target is None:
                survivors.append(bolt)
                continue
            landed = combat.hit_enemy(target, bolt.kind, old)
            if landed and bolt.kind == "ice" and target.kind not in ("guardian", "knight", "dragon"):
                target.freeze_left = max(target.freeze_left, 0.55)
                target.slow_left = max(target.slow_left, 2.2)
            combat.events.append(("element_" + bolt.kind, bolt.pos))
            if landed:
                combat.events.append(("hit", target.pos))
                if target.hp <= 0:
                    combat.kills += 1
                    combat.events.append(("kill", target.pos))
        self.bolts = survivors
        combat.enemies = [e for e in combat.enemies if e.hp > 0]
