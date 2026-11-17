"""3-6 전용: 속성 방어막, 몸통 돌진 패링, 2초 반격 창."""
import random
from late_bosses import Dragon
from geometry import Vec


class FinalDragon(Dragon):
    def __init__(self, uid, pos):
        super().__init__(uid, pos)
        self.hp = self.max_hp = 36
        self.shield_element = "soul"
        self.next_element = "soul"
        self.shield_hp = 8
        self.shield_timer = 4.0
        self.elements = ["soul"]
        self.rng = random.Random()
        self.attack = "lunge"

    def break_shield(self, parried=False):
        self.shield_hp = 0
        self.state, self.timer = ("stunned" if parried else "weak"), 2.0
        self.hazard_time = self.breath_reach = 0
        self.weak_used = False

    def update(self, dt, player, arena, others=()):
        self.flash = max(0, self.flash - dt)
        if self.shield_hp > 0:
            self.shield_timer -= dt
            options = [e for e in self.elements if e != self.shield_element]
            if self.shield_timer <= 0.7 and self.next_element == self.shield_element and options:
                self.next_element = self.rng.choice(options)
            if self.shield_timer <= 0:
                self.shield_element = self.next_element
                self.shield_timer = 4.0
        self.timer -= dt
        if self.state in ("stunned", "weak"):
            if self.timer <= 0:
                self.shield_hp, self.shield_timer = 8, 4.0
                self.state, self.timer = "recover", 0.6
            return
        if self.state == "recover":
            if self.timer <= 0:
                self.cycles += 1
                self.state, self.timer = "approach", 0.65
            return
        if self.state == "approach":
            self.direction = (player.pos - self.pos).normalized()
            if self.timer <= 0:
                self.attack = "lunge" if self.cycles % 2 == 0 else "breath"
                self.state, self.timer = "tell", 0.85
                self.breath_reach = 0
            return
        if self.state == "tell":
            if self.timer <= 0:
                self.state, self.timer = ("charge", 0.65) if self.attack == "lunge" else ("attack", 0.65)
            return
        if self.state == "charge":
            self.pos, blocked = arena.move(self.pos, self.direction * (480 * dt), self.radius, False)
            if blocked or self.timer <= 0:
                self.state, self.timer = "recover", 0.8
            return
        if self.state == "attack":
            self.breath_reach = min(440, self.breath_reach + 880 * dt)
            if self.timer <= 0:
                self.state, self.timer = "recover", 0.8

    def threatens(self, pos):
        return self.state == "attack" and super().threatens(pos)

    def receive_attack(self, element):
        if self.shield_hp > 0:
            if element != self.shield_element:
                return False
            self.shield_hp -= 1
            self.flash = 0.12
            if self.shield_hp <= 0:
                self.break_shield()
            return False
        if self.state not in ("weak", "stunned"):
            return False
        self.hp -= 1
        self.flash = 0.15
        return True

    def receive_slash(self):
        return self.receive_attack("soul")
