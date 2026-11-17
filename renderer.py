"""pico2d 출력 전용. 매끈한 2D 임시 도형은 게임 판정과 독립적이다."""

import math
import random
from pathlib import Path
import pico2d as p
from geometry import Vec, Rect
from sprite_bank import SpriteBank
import config as C

INK = (10, 19, 28)
WHITE = (234, 242, 239)
MUTED = (151, 180, 179)
CYAN = (104, 231, 210)
GOLD = (246, 204, 116)
VIOLET = (183, 128, 216)
RED = (234, 108, 112)
FROST = (160, 220, 255)
SHATTER = (255, 178, 93)
FIRE = (255, 112, 55)
SOUL = (210, 242, 255)


def weapon_color(number):
    return FROST if number == 2 else SHATTER if number == 3 else CYAN

def element_color(element, weapon=1):
    return FROST if element == "ice" else FIRE if element == "fire" else SOUL if element == "soul" else weapon_color(weapon)

def rect(x, y, w, h, color, alpha=255, filled=True):
    p.draw_rectangle(int(x), int(y), int(x + w), int(y + h), *color, alpha, filled)


def circle(pos, radius, color, alpha=255, filled=False):
    p.draw_circle(int(pos.x), int(pos.y), max(0, int(radius)), *color, alpha, filled)


def line(a, b, color, alpha=255):
    p.draw_line(int(a.x), int(a.y), int(b.x), int(b.y), *color, alpha)


class Renderer:
    def __init__(self):
        font_candidates = [Path("C:/Windows/Fonts/malgun.ttf"), Path("C:/Windows/Fonts/arial.ttf"),
                           Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")]
        self.font_path = next((str(f) for f in font_candidates if f.exists()), None)
        if self.font_path is None:
            raise RuntimeError("글꼴을 찾지 못했습니다. Windows의 맑은 고딕 글꼴이 필요합니다.")
        self.fonts = {size: p.load_font(self.font_path, size) for size in (14, 16, 18, 20, 23, 26, 32, 42, 64)}
        self.bank = SpriteBank(p)
        self.effects = []
        self.debug = False
        self.audio_enabled = True
        self.shake = 0.0
        self.impact_flash = 0.0
        self.animation_starts = {}
        self.visual_time = 0
        rng = random.Random(41)
        self.grass = [(rng.randint(55, 1064), rng.randint(119, 613), rng.randrange(3)) for _ in range(180)]

    def text(self, message, x, y, size=20, color=WHITE):
        self.fonts[size].draw(x, y, str(message), color)

    def ui(self, name, x, y, width, height, alpha=1):
        return self.bank.draw_cell("ui_" + name, 0, 0, Vec(x, y), width, height, alpha)

    def ui_fill(self, name, ratio, x, y, width, height, source_left=0, source_width=None):
        entry = self.bank.entries.get("ui_" + name)
        if entry is None or ratio <= 0:
            return False
        image = entry[0]
        source_width = image.w - source_left if source_width is None else source_width
        fraction = min(1, ratio)
        crop = max(1, int(source_width * fraction))
        target_width = width * source_width / image.w * fraction
        target_x = x - width / 2 + (source_left / image.w) * width + target_width / 2
        image.clip_draw(source_left, 0, crop, image.h, target_x, y, target_width, height)
        return True

    def center(self, message, y, size=23, color=WHITE):
        # pico2d Font 내부의 SDL_ttf로 실제 너비를 구한다.
        from ctypes import byref, c_int
        width, height = c_int(), c_int()
        font = self.fonts[size]
        p.TTF_SizeUTF8(font.font, str(message).encode("utf-8"), byref(width), byref(height))
        self.text(message, (C.WIDTH - width.value) // 2, y, size, color)

    def consume(self, events):
        for kind, pos in events:
            if kind in ("hit", "kill", "hurt", "recharge", "open", "crystal_break", "terminal_on", "element_ice", "element_fire",
                        "boss_impact", "boss_breath", "boss_hit", "production", "beacon_hit",
                        "frost", "weapon_switch", "parry_ready", "parry_success", "shield_hit", "shield_break", "backstab"):
                self.effects.append([kind, pos, 0.0])
            if kind == "hurt":
                self.shake = 0.18
            if kind in ("parry_success", "backstab"):
                self.shake = 0.18
                self.impact_flash = 0.09
            if kind in ("boss_impact", "boss_breath", "boss_hit"):
                self.impact_flash = 0.13 if kind != "boss_hit" else 0.08
        events.clear()

    def tick(self, dt):
        self.visual_time += dt
        self.shake = max(0, self.shake - dt)
        self.impact_flash = max(0, self.impact_flash - dt)
        for item in self.effects:
            item[2] += dt
        self.effects = [e for e in self.effects if e[2] < 0.7]

    def actor(self, kind, pos, direction, state="idle", ghost=False, alpha=255, flash=False,
              animation_time=None):
        scale = 2 if kind in ("guardian", "knight", "dragon") else 1
        if not ghost:
            circle(pos + Vec(0, -9), 19 * scale, INK, 110, True)
        elif getattr(self, "soul_ghosts", False):
            alpha = min(235, max(170, alpha + 70))
            for offset in (Vec(-2, 0), Vec(2, 0), Vec(0, 2)):
                self.bank.draw("player", pos + offset, self.visual_time, direction, state,
                               alpha=0.45, glow=True)
            line(pos + Vec(-12, -16), pos + Vec(12, -16), SOUL, 180)
        if kind == "dragon" and state in ("tell", "attack"):
            state = ("breath_tell" if self.dragon_attack == "breath" and state == "attack"
                     and self.dragon_reach < 160 else f"{self.dragon_attack}_{state}")
        if self.bank.draw("player" if ghost else kind, pos,
                          self.visual_time if animation_time is None else animation_time,
                          direction, state,
                          alpha / 255, scale):
            return
        direction = direction.normalized() if direction.length() else Vec(0, -1)
        side = Vec(-direction.y, direction.x)
        color = WHITE if flash else CYAN if ghost else {
            "player": (93, 172, 196), "wolf": (127, 92, 150), "boar": (151, 99, 123),
            "mage": (154, 107, 202), "sentinel": (184, 120, 112),
            "guardian": (134, 89, 151), "knight": (160, 165, 181),
            "dragon": (137, 79, 155)}.get(kind, VIOLET)
        center = pos + Vec(0, 7 * scale)
        circle(center, 15 * scale, color, alpha, True)
        circle(center + direction * (7 * scale), 8 * scale, WHITE if flash else (29, 41, 58), alpha, True)
        if kind in ("wolf", "boar", "guardian", "dragon", "sentinel"):
            for sign in (-1, 1):
                ear = center - direction * (7 * scale) + side * (sign * 10 * scale)
                circle(ear, 5 * scale, color, alpha, True)
            for sign in (-1, 1):
                eye = center + direction * (9 * scale) + side * (sign * 5 * scale)
                circle(eye, 2 * scale, RED if kind == "dragon" else GOLD, alpha, True)
        if kind in ("mage", "knight"):
            circle(center, 18 * scale, GOLD if state == "weak" else color, 80, False)
        if kind == "dragon":
            for sign in (-1, 1):
                wing = center + side * (sign * 27 * scale)
                circle(wing, 12 * scale, color, alpha // 2, True)
        if kind == "player":
            cape = center - direction * 11
            line(cape - side * 10, cape - direction * 18, CYAN if ghost else (49, 88, 129), alpha)
            line(cape + side * 10, cape - direction * 18, CYAN if ghost else (49, 88, 129), alpha)
            grip = center + side * 12
            line(grip, grip + direction * (31 if state == "slash" else 23), CYAN if ghost else WHITE, alpha)
            circle(center + direction * 7, 5, GOLD, alpha, True)

    def floor(self, game):
        rect(0, 0, C.WIDTH, C.HEIGHT, INK)
        theme = game.stage.get("theme", "forest")
        base = {"forest": (25, 48, 45), "fortress": (42, 43, 60),
                "sanctuary": (40, 38, 60)}[theme]
        rect(30, 98, 1060, 536, base)
        has_background = self.bank.draw(theme, Vec(560, 366), 0, scale=1)
        if not has_background:
            for x, y, tone in self.grass:
                if theme == "forest":
                    circle(Vec(x, y), 2 + tone, (49, 89, 69), 90, True)
                else:
                    circle(Vec(x, y), 2 + tone, VIOLET if theme == "sanctuary" else MUTED, 35, True)
            for x in range(92, 1050, 120):
                for y in (153, 555):
                    circle(Vec(x, y), 18 if theme == "forest" else 10,
                           (45, 84, 67) if theme == "forest" else (73, 72, 92), 120, True)
            if theme == "fortress":
                for x in (130, 990):
                    for y in (270, 440):
                        circle(Vec(x, y), 29, (91, 89, 111), 150)
                        circle(Vec(x, y), 18, (110, 103, 125), 80, True)
            elif theme == "sanctuary":
                for x, y in ((180, 260), (940, 260), (180, 500), (940, 500)):
                    circle(Vec(x, y), 36, VIOLET, 80)
                    circle(Vec(x, y), 25, CYAN, 55)
            for x in range(42, 1080, 65):
                for y in (105, 626):
                    circle(Vec(x, y), 15 if theme == "forest" else 9,
                           (39, 76, 59) if theme == "forest" else (93, 89, 111), 200, True)
        gate_color = CYAN if game.gate_open else VIOLET
        if not self.bank.draw_cell("door", 2 if game.gate_open else 0, 0,
                                   Vec(560, 600), 120, 89):
            rect(510, 588, 100, 40, (12, 23, 32))
            rect(508, 586, 9, 44, gate_color)
            rect(603, 586, 9, 44, gate_color)
            if game.gate_open:
                rect(520, 590, 80, 36, CYAN, 55)
            else:
                for x in range(526, 602, 15):
                    line(Vec(x, 591), Vec(x, 624), VIOLET, 160)
        seal = Vec(560, 365)
        circle(seal, 43, gate_color, 75)
        circle(seal, 34, gate_color, 75)
        for i in range(6):
            a = seal + Vec(math.cos(i * math.tau / 6), math.sin(i * math.tau / 6)) * 39
            rect(a.x - 2, a.y - 2, 4, 4, gate_color, 90)

    def obstacle(self, theme, wall):
        center = Vec(wall.x + wall.w / 2, wall.y + wall.h / 2)
        circle(center + Vec(0, -8), wall.w * 0.48, INK, 95, True)
        drawn = self.bank.draw_cell("obstacle_" + theme, 0, 0,
                                    center + Vec(0, 20), wall.w + 48, wall.h + 72)
        if not drawn:
            color = (63, 77, 66) if theme == "forest" else (79, 80, 94)
            circle(center, min(wall.w, wall.h) * 0.55, color, 255, True)
            circle(center + Vec(0, 12), min(wall.w, wall.h) * 0.4, MUTED, 90)
        if self.debug:
            rect(wall.x, wall.y, wall.w, wall.h, CYAN, 200, False)

    def ice_crystal(self, pos, direction, scale=1.0, alpha=235):
        side = Vec(-direction.y, direction.x)
        for offset, size in ((Vec(), scale), (direction * -13 + side * 9, scale * 0.6),
                             (direction * -15 - side * 9, scale * 0.55)):
            center = pos + offset * scale
            tip, tail = center + direction * (22 * size), center - direction * (15 * size)
            for i in range(-6, 7):
                waist = center + side * (i * size)
                line(tail, waist, FROST, alpha)
                line(waist, tip, (205, 244, 255), alpha)
            line(tail, tip, WHITE, alpha)

    def boss_shield(self, boss):
        center = boss.pos + Vec(0, 35)
        if boss.shield_hp > 0:
            color = element_color(boss.shield_element)
            circle(center, 92, color, 30, True)
            circle(center, 92, color, 190)
            circle(center, 97, color, 75)
            for i in range(8):
                angle = self.visual_time * 1.6 + i * math.tau / 8
                node = center + Vec(math.cos(angle), math.sin(angle)) * 94
                circle(node, 4, color, 210, True)
            label = {"soul": "기본", "ice": "얼음", "fire": "불"}[boss.shield_element]
            self.text(f"{label} 방어막 {boss.shield_hp}/8", center.x - 65, center.y - 115, 16, color)
            if boss.shield_timer <= 0.7:
                label = {"soul": "기본", "ice": "얼음", "fire": "불"}[boss.next_element]
                self.text("곧 " + label + " 속성", center.x - 40, center.y - 135, 16, GOLD)
        elif boss.state == "stunned":
            self.text(f"STUN {boss.timer:.1f}s", center.x - 48, center.y + 105, 20, GOLD)
            for i in range(3):
                angle = self.visual_time * 4 + i * math.tau / 3
                star = center + Vec(math.cos(angle) * 36, 85 + math.sin(angle) * 8)
                line(star - Vec(5, 0), star + Vec(5, 0), GOLD, 240)
                line(star - Vec(0, 5), star + Vec(0, 5), GOLD, 240)

    def arc(self, origin, radius, direction, age, color=CYAN, alpha=220):
        angle = math.atan2(direction.y, direction.x)
        sweep = -1.5 + min(1, age / 0.2) * 2.8
        previous = None
        for i in range(18):
            theta = angle + sweep - 0.9 + i * 0.1
            q = origin + Vec(math.cos(theta), math.sin(theta)) * radius
            if previous:
                line(previous, q, color, alpha)
                line(previous + Vec(1, 1), q + Vec(1, 1), WHITE, alpha // 2)
            previous = q

    def scene(self, game):
        combat = game.combat
        self.soul_ghosts = (game.index == 15 or getattr(game, "modern_combat", False))
        for pos, direction, element in combat.element_skill.pending:
            self.actor("player", pos, direction, ghost=True, alpha=150)
        for bolt in combat.element_skill.bolts:
            angle = math.atan2(bolt.velocity.y, bolt.velocity.x)
            if bolt.kind == "fire":
                self.bank.draw_rotated_cell("fire_projectile", 0, 0, bolt.pos, 76, 76, angle)
            elif bolt.kind == "ice":
                self.ice_crystal(bolt.pos, bolt.velocity.normalized())
            else:
                line(bolt.pos - bolt.velocity.normalized() * 26, bolt.pos, SOUL, 235)
                circle(bolt.pos, 7, SOUL, 230, True)
        if game.index == 1 and game.beacon_hp > 0:
            self.bank.draw_cell("terminal", 1, 0, game.beacon_pos, 78, 82)
            rect(game.beacon_pos.x - 40, game.beacon_pos.y + 47, 80, 8, INK)
            rect(game.beacon_pos.x - 38, game.beacon_pos.y + 49, 76 * game.beacon_hp / 8, 4, CYAN)
        if game.hazard_marker is not None:
            color = RED if game.hazard_active else GOLD
            circle(game.hazard_marker, 78, color, 105 if game.hazard_active else 190)
            if not self.bank.draw_cell("combat_fx", 2, 0, game.hazard_marker, 156, 156, 0.6):
                circle(game.hazard_marker, 70, color, 45, True)
        for device in combat.devices:
            color = WHITE if device.flash else GOLD if device.kind == "terminal" else VIOLET
            name = "crystal" if device.kind == "crystal" else "terminal"
            frame = 1 if device.flash else 0
            if not self.bank.draw_cell(name, frame, 0, device.pos, 67, 67):
                circle(device.pos, device.radius, color, 180, True)
            if device.kind == "terminal":
                self.text(device.link, device.pos.x - 5, device.pos.y - 8, 16, color)
        if (game.index == 15 or getattr(game, "modern_combat", False)):
            for kind, drop_pos in game.element_drops:
                color = element_color(kind)
                circle(drop_pos, 31 + 3 * math.sin(self.visual_time * 5), color, 115)
                self.bank.draw_cell(kind + "_relic_test", 0, 0, drop_pos, 118, 79)
                if combat.player.pos.distance(drop_pos) < 90:
                    self.text("E 획득", drop_pos.x - 27, drop_pos.y + 36, 16, WHITE)
        for bullet in combat.projectiles:
            row = 1 if bullet.kind == "knight" else 0
            frame = 2 if bullet.kind == "dragon" else int(self.visual_time * 10) % 4
            size = 46 if bullet.kind == "dragon" else 34
            if not self.bank.draw_cell("projectiles", frame, row, bullet.pos, size, size):
                circle(bullet.pos, bullet.radius, WHITE, 230, True)
        if combat.dual_mode and combat.echo_pos is not None:
            alpha = int(70 + 100 * combat.echo_remaining / combat.player.trail_lifetime)
            circle(combat.echo_pos, 31, CYAN, 80)
            self.actor("player", combat.echo_pos, combat.player.facing, ghost=True, alpha=alpha)
        if combat.trail:
            trail = combat.trail
            alpha = int(55 + 95 * trail.remaining / trail.lifetime)
            if (game.index == 15 or getattr(game, "modern_combat", False)):
                alpha = int(150 + 65 * trail.remaining / trail.lifetime)
            trail_color = CYAN if trail.element == "fire" else element_color(trail.element, trail.weapon)
            trail_fx = None if trail.element == "fire" else trail.element or ("ice" if trail.weapon == 2 else None)
            for a, b in zip(trail.points, trail.points[1:]):
                line(a, b, trail_color, alpha)
                if trail_fx:
                    line(a + Vec(0, 3), b + Vec(0, 3), trail_color, alpha // 2)
            visible = trail.visible_points()
            if (game.index == 15 or getattr(game, "modern_combat", False)) and len(visible) > 7:
                visible = [visible[round(i * (len(visible) - 1) / 6)] for i in range(7)]
            for i, pos in enumerate(visible):
                fade = int(alpha * (0.3 + 0.7 * (i + 1) / len(visible)))
                if trail_fx:
                    circle(pos, 30, trail_color, min(200, fade + 30))
                    circle(pos, 18, trail_color, min(125, fade), True)
                self.actor("player", pos, trail.direction, ghost=True,
                           alpha=fade // 2 if trail_fx else fade)
                if trail_fx == "fire":
                    for j in range(3):
                        x = pos.x - 14 + j * 14
                        lift = 16 + ((i + j) % 3) * 7
                        line(Vec(x, pos.y - 9), Vec(x + 3, pos.y + lift), FIRE, min(220, fade + 50))
                        circle(Vec(x + 3, pos.y + lift + 4), 4, GOLD, min(230, fade + 60), True)
                elif trail_fx == "ice":
                    for j in range(3):
                        x = pos.x - 14 + j * 14
                        tip = Vec(x, pos.y + 22 + ((i + j) % 2) * 7)
                        line(Vec(x - 4, pos.y + 5), tip, FROST, min(220, fade + 40))
                        line(tip, Vec(x + 4, pos.y + 5), FROST, min(220, fade + 40))
        for enemy in combat.enemies:
            if enemy.state == "tell" and enemy.kind != "dragon":
                color = RED if enemy.kind == "guardian" else GOLD
                circle(enemy.pos, enemy.radius + 7 + 3 * math.sin(self.visual_time * 15), color, 170)
            if enemy.kind in ("guardian", "knight", "dragon") and enemy.state == "weak":
                circle(enemy.pos, enemy.radius + 7, GOLD, 160)
            if enemy.kind == "dragon" and enemy.state in ("tell", "attack"):
                if enemy.attack == "breath":
                    if enemy.state == "tell":
                        charge = max(0, 1 - enemy.timer / 0.9)
                        mouth = enemy.pos + enemy.direction * 30
                        circle(mouth, 7 + charge * 13, VIOLET, int(80 + charge * 110), True)
                    else:
                        bounds = combat.arena.bounds
                        reach = 440.0
                        if enemy.direction.x > 0:
                            reach = min(reach, (bounds.x + bounds.w - enemy.pos.x) / enemy.direction.x)
                        elif enemy.direction.x < 0:
                            reach = min(reach, (bounds.x - enemy.pos.x) / enemy.direction.x)
                        if enemy.direction.y > 0:
                            reach = min(reach, (bounds.y + bounds.h - enemy.pos.y) / enemy.direction.y)
                        elif enemy.direction.y < 0:
                            reach = min(reach, (bounds.y - enemy.pos.y) / enemy.direction.y)
                        visible_reach = max(0, min(reach, enemy.breath_reach))
                        if visible_reach > 0:
                            center = enemy.pos + enemy.direction * (visible_reach / 2)
                            angle = math.atan2(enemy.direction.y, enemy.direction.x)
                            self.bank.draw_rotated_cell("combat_fx", 3, 0, center,
                                                        visible_reach, 105, angle, 0.85)
            if enemy.state == "charge":
                line(enemy.pos - enemy.direction * 40, enemy.pos, GOLD, 120)
            if (game.index == 15 or getattr(game, "modern_combat", False)) and hasattr(enemy, "shield_hp"):
                self.boss_shield(enemy)
                if enemy.attack == "lunge" and enemy.state in ("tell", "charge"):
                    # 공격 범위를 덮지 않고 몸 앞의 화살표로 돌진 방향만 알린다.
                    direction = enemy.direction
                    side = Vec(-direction.y, direction.x)
                    start = enemy.pos + direction * (enemy.radius + 8)
                    tip = start + direction * (43 if enemy.aim_locked else 28)
                    color = GOLD if enemy.aim_locked else SOUL
                    line(start, tip, color, 235)
                    line(tip - direction * 13 + side * 9, tip, color, 235)
                    line(tip - direction * 13 - side * 9, tip, color, 235)
                    self.text("돌진 준비" if enemy.state == "tell" else "돌진 · 우클릭!",
                              enemy.pos.x - 45, enemy.pos.y - 85, 16, color)
        actors = [(e.pos.y, e) for e in combat.enemies]
        actors.append((combat.player.pos.y, combat.player))
        actors.extend((wall.y, wall) for wall in combat.arena.walls)
        actors.sort(key=lambda item: item[0], reverse=True)
        for _, actor in actors:
            if isinstance(actor, Rect):
                if not hasattr(game, "bag"):
                    self.obstacle(game.stage.get("theme", "forest"), actor)
                continue
            is_player = actor is combat.player
            kind = "player" if is_player else actor.kind
            if is_player:
                state = "dash" if actor.dash_left else "slash" if any(s.age < 0.18 for s in combat.slashes) else "walk" if actor.moving else "idle"
                direction = actor.facing
                alpha = 125 if actor.invulnerable > 0 and int(self.visual_time * 14) % 2 else 255
            else:
                state, direction, alpha = actor.state, actor.direction, 255
                if kind == "mage" and actor.cast_left > 0:
                    state = "cast"
                if kind == "dragon":
                    self.dragon_attack = "stomp" if actor.attack == "lunge" else actor.attack
                    self.dragon_reach = actor.breath_reach
            facing = (("right" if direction.x > 0 else "left") if abs(direction.x) > abs(direction.y)
                      else ("up" if direction.y > 0 else "down"))
            actor_key = (game.index, 0 if is_player else actor.uid)
            phase = ("breath_charge" if kind == "dragon" and state == "attack"
                     and actor.breath_reach < 160 else state)
            token = (phase, facing)
            if actor_key not in self.animation_starts or self.animation_starts[actor_key][0] != token:
                self.animation_starts[actor_key] = (token, self.visual_time)
            animation_time = self.visual_time - self.animation_starts[actor_key][1]
            if is_player and (combat.element or actor.weapon == 2):
                aura = element_color(combat.element, actor.weapon)
                radius = 29 + 2 * math.sin(self.visual_time * 3)
                circle(actor.pos + Vec(0, -10), radius, aura, 38, True)
            draw_state = "weak" if state == "stunned" else "stomp_attack" if kind == "dragon" and state == "charge" else state
            sprite = getattr(actor, "sprite_key", "")
            sprite_state = "stun" if state == "stunned" else "tell" if state in ("windup", "tell") else "charge" if state in ("charge", "attack") else "idle"
            if sprite and self.bank.draw(sprite + "_" + sprite_state, actor.pos, animation_time, direction, scale=2):
                continue
            self.actor(kind, actor.pos, direction, draw_state, alpha=alpha,
                       flash=not is_player and actor.flash > 0,
                       animation_time=animation_time)
            if is_player and (combat.element or actor.weapon == 2):
                circle(actor.pos + Vec(0, -10), radius, aura, 98)
            if not is_player and actor.kind in ("boar", "sentinel") and actor.hp == 1:
                rect(actor.pos.x - 11, actor.pos.y + 37, 22, 3, RED)
            if not is_player and getattr(actor, "freeze_left", 0) > 0:
                circle(actor.pos, actor.radius + 10, FROST, 65, True)
                circle(actor.pos, actor.radius + 13, FROST, 205)
                for angle in range(0, 360, 60):
                    direction = Vec(math.cos(math.radians(angle)), math.sin(math.radians(angle)))
                    line(actor.pos + direction * (actor.radius + 5),
                         actor.pos + direction * (actor.radius + 19), WHITE, 185)
                self.text("빙결", actor.pos.x - 17, actor.pos.y + actor.radius + 24, 16, FROST)
            elif not is_player and getattr(actor, "slow_left", 0) > 0:
                circle(actor.pos, actor.radius + 7, FROST, 130)
            if self.debug:
                circle(actor.pos, actor.radius, GOLD if is_player else RED, 200)
        for slash in combat.slashes:
            blade = element_color(slash.element, slash.weapon)
            slash_fx = slash.element or ("ice" if slash.weapon == 2 else None)
            if slash.style == "chain":
                for i in range(slash.next_point, len(slash.points)):
                    pos = slash.points[i]
                    strength = (i + 1) / len(slash.points)
                    self.actor("player", pos, slash.direction, ghost=True, alpha=int(65 + 95 * strength))
                if slash.next_point:
                    index = min(slash.next_point - 1, len(slash.points) - 1)
                    pos = slash.points[index]
                    interval = 0.06 if slash.weapon == 3 else 0.045
                    phase = max(0, slash.age - (C.SLASH_HIT_TIME + index * interval))
                    if phase < 0.13:
                        self.arc(pos, slash.radius + (16 if slash.weapon == 3 else 10),
                                 slash.direction, phase, blade)
                        if slash_fx:
                            circle(pos, 20 + phase * 100, blade, int(160 * (1 - phase / 0.13)))
                            for j in range(5):
                                angle = j * math.tau / 5 + self.visual_time * 2
                                offset = Vec(math.cos(angle), math.sin(angle)) * (25 + phase * 85)
                                circle(pos + offset, 4 if slash_fx == "fire" else 3, blade,
                                       int(210 * (1 - phase / 0.13)), True)
                        elif slash.weapon == 3:
                            circle(pos, 22 + phase * 90, SHATTER, int(180 * (1 - phase / 0.13)))
                        else:
                            self.bank.draw_cell("combat_fx", 0, 0, pos, 80, 80, 1 - phase / 0.13)
                continue
            n = len(slash.points)
            indices = (range(n) if slash.style == "dual" else
                       sorted({round(k * (n - 1) / 3) for k in range(4)}))
            for i in indices:
                pos = slash.points[i]
                alpha = int(190 * max(0, 1 - slash.age / 0.27))
                self.actor("player", pos, slash.direction, ghost=True, alpha=alpha)
                self.arc(pos, slash.radius, slash.direction, slash.age, blade)
            for center in (slash.points if slash.style == "dual" else [slash.points[n // 2]]):
                if slash_fx:
                    circle(center, 27 + slash.age * 80, blade,
                           int(max(0, 1 - slash.age / 0.27) * 170))
                elif slash.weapon == 3:
                    circle(center, 27 + slash.age * 60, SHATTER, int(max(0, 1 - slash.age / 0.27) * 180))
                else:
                    self.bank.draw_cell("combat_fx", 0, 0, center, 77, 77,
                                        max(0, 1 - slash.age / 0.27))
        for kind, pos, age in self.effects:
            color = (RED if kind in ("hurt", "production", "beacon_hit") else
                     FIRE if kind == "element_fire" else FROST if kind == "element_ice" else
                     FROST if kind == "frost" else SHATTER if kind == "weapon_switch" else
                     GOLD if kind == "recharge" else CYAN)
            alpha = int(max(0, 1 - age / 0.7) * 240)
            if kind in ("parry_ready", "parry_success", "shield_break", "shield_hit", "backstab"):
                color = GOLD if kind in ("parry_success", "backstab") else SOUL
                circle(pos, 25 + age * 100, color, alpha)
                if kind == "parry_success":
                    self.text("PARRY!", pos.x - 40, pos.y + 65, 23, GOLD)
                if kind == "backstab":
                    self.text("배후 일격 +3", pos.x - 45, pos.y + 80, 20, GOLD)
            if kind == "element_ice" and (game.index == 15 or getattr(game, "modern_combat", False)):
                for j in range(4):
                    angle = j * math.tau / 4 + age
                    self.ice_crystal(pos + Vec(math.cos(angle), math.sin(angle)) * age * 65,
                                     Vec(math.cos(angle), math.sin(angle)), 0.35, alpha)
            if kind == "crystal_break" and self.bank.draw_cell("crystal", 2, 0, pos, 72, 72, alpha / 255):
                continue
            if kind == "terminal_on" and self.bank.draw_cell("terminal", 2, 0, pos, 72, 72, alpha / 255):
                continue
            if kind in ("hit", "kill"):
                self.bank.draw_cell("combat_fx", 1, 0, pos, 68, 68, alpha / 255)
            if kind in ("boss_impact", "boss_breath", "boss_hit"):
                size = (75 + age * 270) if kind != "boss_hit" else (70 + age * 110)
                circle(pos, size, GOLD if kind == "boss_hit" else RED, alpha)
                circle(pos, size * 0.7, GOLD if kind == "boss_hit" else VIOLET, alpha // 2)
                self.bank.draw_cell("combat_fx", 1, 0, pos, 120, 120, alpha / 255)
            if kind in ("production", "beacon_hit", "frost", "weapon_switch"):
                circle(pos, 30 + age * 70, color, alpha)
            for i in range(6):
                q = pos + Vec(math.cos(i * 1.8), math.sin(i * 1.8)) * (age * 80 + 5)
                rect(q.x, q.y, 4, 4, color, alpha)
            if kind == "recharge":
                self.text("재대시!", pos.x - 25, pos.y + 42 + age * 30, 18, GOLD)
        if self.debug and combat.trail:
            for point in combat.trail.points:
                circle(point, 2, GOLD, 255, True)
        if combat.aim_target is not None and not game.paused:
            cursor = combat.aim_target
            if 30 < cursor.x < 1090 and 98 < cursor.y < 634:
                circle(cursor, 7, CYAN, 175)
                line(cursor + Vec(-12, 0), cursor + Vec(-4, 0), CYAN, 190)
                line(cursor + Vec(4, 0), cursor + Vec(12, 0), CYAN, 190)
                line(cursor + Vec(0, -12), cursor + Vec(0, -4), CYAN, 190)
                line(cursor + Vec(0, 4), cursor + Vec(0, 12), CYAN, 190)

    def hud(self, game):
        c, player = game.combat, game.combat.player
        rect(32, 575, 294, 66, INK, 210)
        for slot in range(5):
            x = 64 + slot * 58
            owned = slot + 1 in game.available_weapons(game.index) if slot < 3 else ("ice" if slot == 3 else "fire") in game.owned_elements
            selected = (not c.element and player.weapon == slot + 1) if slot < 3 else c.element == ("ice" if slot == 3 else "fire")
            self.ui("slot_selected" if selected else "slot_normal" if owned else "slot_locked", x, 608, 54, 54)
            if owned:
                if slot < 3:
                    self.ui(("weapon_basic", "weapon_frost", "weapon_shatter")[slot], x, 608, 39, 39)
                else:
                    self.bank.draw_cell(("ice" if slot == 3 else "fire") + "_relic_test", 0, 0, Vec(x, 608), 72, 48)
            self.text(str(slot + 1), x - 23, 624, 14, GOLD if selected else MUTED)
        rect(0, 654, C.WIDTH, 106, (9, 17, 27), 245)
        rect(0, 652, C.WIDTH, 2, (68, 98, 107))
        self.text("HP", 32, 722, 16, MUTED)
        for i in range(C.MAX_HP):
            if not self.ui("heart_full" if i < player.hp else "heart_empty", 49 + i * 36, 688, 35, 35):
                self.text("♥" if i < player.hp else "♡", 31 + i * 30, 679, 32,
                          RED if i < player.hp else (73, 82, 91))
        self.text("연습장" if game.training else game.stage['id'], 250, 715, 26, GOLD)
        self.text("TRAINING" if game.training else game.stage['title'], 325, 715, 23, WHITE)
        if game.trial:
            self.text("체험", 615, 715, 16, CYAN)
        if (game.index == 15 or getattr(game, "modern_combat", False)) and c.element:
            self.bank.draw_cell(c.element + "_relic_test", 0, 0, Vec(725, 701), 87, 58)
            self.text("얼음" if c.element == "ice" else "불", 700, 663, 16,
                      element_color(c.element))
        self.text("봉인 해제" if not game.training else "전투 연습", 790, 722, 18, MUTED)
        self.text(f"{min(c.kills, game.goal)} / {game.goal}" if not game.training else "무제한", 965, 711, 26, GOLD)
        ratio = 0 if game.training else min(1, c.kills / max(1, game.goal))
        self.ui("progress_frame", 925, 681, 290, 42)
        self.ui_fill("progress_fill", ratio, 925, 681, 290, 42, 24, 372)
        if game.index == 1 and game.mode == "play" and not getattr(game, "modern_combat", False):
            self.text(f"이정표 {game.beacon_hp}/8", 790, 660, 16, CYAN if game.beacon_hp > 3 else RED)
        elif c.auto_echo and c.trail:
            wait = c.auto_echo_timer
            self.text("잔영 배치 중" if wait is None else f"잔영 자동 참격 {max(0, wait):.1f}초",
                      790, 660, 16, CYAN)
        elif c.trail:
            self.text(f"잔영 {c.trail.remaining:.1f}초", 790, 660, 16, CYAN)
        elif c.dual_mode and c.echo_pos is not None:
            self.text(f"잔영 {c.echo_remaining:.1f}초", 790, 660, 16, CYAN)
        bosses = [e for e in c.enemies if e.kind in ("guardian", "knight", "dragon")]
        if bosses:
            boss = bosses[0]
            self.ui("boss_frame", 560, 603, 480, 74)
            self.ui_fill("boss_fill", boss.hp / boss.max_hp, 560, 603, 480, 74, 95, 220)
            label = getattr(boss, "name", None) or {"guardian": "숲의 수호수", "knight": "봉인 수호기사", "dragon": "침식된 드래곤"}[boss.kind]
            state = {"tell": "공격 예고", "charge": "돌진", "attack": "공격", "weak": "약점! F 검격", "stunned": "패링 성공 · 반격", "recover": "회복", "approach": "대기"}[boss.state]
            self.text(label + "  /  " + state, 325, 666, 18, GOLD if boss.state == "weak" else WHITE)
        rect(0, 0, C.WIDTH, 78, (9, 17, 27), 245)
        rect(0, 77, C.WIDTH, 2, (68, 98, 107))
        self.ui("dash_ready" if c.ready else "dash_cooldown", 57, 39, 59, 59)
        self.text("SPACE", 95, 44, 16, CYAN if c.ready else MUTED)
        self.text("대시 준비" if c.ready else "재충전", 95, 22, 16, WHITE)
        self.ui("slash", 260, 39, 59, 59)
        self.text("F", 300, 44, 20, GOLD)
        self.text("기본 검격", 300, 22, 16, WHITE)
        circle(Vec(460, 39), 22, SOUL if (game.index == 15 or getattr(game, "modern_combat", False)) else MUTED, 165)
        line(Vec(447, 39), Vec(460, 22), SOUL, 180)
        line(Vec(460, 22), Vec(475, 52), SOUL, 180)
        self.text("우클릭", 495, 44, 18, SOUL)
        self.text("패링" if (game.index == 15 or getattr(game, "modern_combat", False)) else "3-6 패링", 495, 22, 16, WHITE if (game.index == 15 or getattr(game, "modern_combat", False)) else MUTED)
        self.ui("slot_normal", 650, 40, 63, 63)
        if c.skill_element:
            if c.skill_element == "soul":
                self.ui("weapon_basic", 650, 40, 45, 45)
            else:
                self.bank.draw_cell(c.skill_element + "_relic_test", 0, 0, Vec(650, 40), 84, 56)
            self.text("좌클릭 " + {"fire": "화염 연사", "ice": "얼음 결정", "soul": "영혼 연사"}[c.skill_element], 690, 45, 18, element_color(c.skill_element))
            wait = c.element_skill.cooldown
            status = f"재사용 {wait:.1f}초" if wait else "대시 후 커서로 조준" if not c.trail else "커서 방향으로 좌클릭 발사"
            self.text(status, 690, 22, 16, MUTED if wait else WHITE)
        else:
            self.ui(("weapon_basic", "weapon_frost", "weapon_shatter")[player.weapon - 1], 650, 40, 46, 46)
            self.text("대시 경로 잔영 검격", 690, 45, 18, CYAN)
            self.text("자동 발동" if c.auto_echo else "좌클릭으로 잔영 발동", 690, 22, 16, MUTED)
        self.text("I 아이템" if getattr(game, "modern_combat", False) else "Tab 아이템", 955, 48, 16, MUTED)
        self.text("휠 교체 / Esc 메뉴", 920, 24, 14, MUTED)
        if (game.index == 15 or getattr(game, "modern_combat", False)):
            if c.counter_left > 0:
                self.text(f"반격 {c.counter_left:.1f}초 · 연속 {c.counter_charges}회 · 배후 일격", 350, 83, 18, GOLD)
            else:
                self.text("우클릭 패링 " + (f"{c.parry_cooldown:.1f}초" if c.parry_cooldown else "준비 · 판정 0.25초"), 400, 83, 18, SOUL)
            if c.parry_left > 0:
                circle(player.pos, 35, GOLD, 200)
        if game.toast_left > 0:
            self.ui("notice_panel", 560, 140, 850, 68)
            self.center(game.toast, 132, 18, GOLD)
        elif game.banner_left > 0:
            self.ui("notice_panel", 560, 140, 1010, 68)
            self.center(game.stage["tip"].replace("J", "F"), 132, 16, MUTED)
        if game.notice:
            self.text(game.notice, 55, 82, 14, RED)

    def shade(self):
        rect(0, 78, C.WIDTH, 582, INK, 240)

    def transit_scene(self, game):
        progress = game.transit_progress
        source = game.stage.get("theme", "forest")
        destination = game.stages[game.index + 1].get("theme", "forest")
        rect(0, 0, C.WIDTH, C.HEIGHT, INK)
        self.bank.draw(source, Vec(560, 366), 0, alpha=1)
        self.bank.draw(destination, Vec(560, 366), 0, alpha=progress)
        # 길바닥이 아래로 흐르고 검사는 제자리에 남아 카메라가 따라가는 느낌을 준다.
        rect(430, 100, 260, 535, INK, 145)
        for i in range(9):
            y = 115 + ((i * 85 - progress * 430) % 535)
            line(Vec(442, y), Vec(678, y), CYAN if destination == "sanctuary" else MUTED, 70)
        line(Vec(430, 100), Vec(430, 635), CYAN, 120)
        line(Vec(690, 100), Vec(690, 635), CYAN, 120)
        self.actor("player", Vec(game.transit_x, 180), Vec(0, 1), state="walk")
        self.center(f"{game.stage['title']}  →  {game.stages[game.index + 1]['title']}", 705, 26, WHITE)
        self.center("W / ↑  앞으로 이동", 43, 20, CYAN)

    def title(self, game):
        for i in range(4):
            pos = Vec(690 + i * 70, 420 + i * 16)
            self.actor("player", pos, Vec(1, 0), ghost=i < 3, alpha=60 + i * 55)
        self.text("잔영의 검", 86, 514, 64, WHITE)
        self.text("이동한 자리에 검격을 남긴다", 91, 448, 26, CYAN)
        self.text("몬스터 처치  ·  봉인 해제  ·  검의 성장", 92, 401, 20, MUTED)
        self.text("Enter   새 모험", 94, 310, 26, WHITE)
        self.text("C          이어하기" + ("" if game.saved else "  (기록 없음)"), 94, 262, 23,
                  CYAN if game.saved else MUTED)
        self.text("T          잔영 검술 연습장", 94, 215, 23, GOLD)
        self.text("F2         라운드 체험 (저장 유지)", 94, 178, 20, CYAN)
        self.text("숲·요새·성역 16라운드 / 수호기사·드래곤 / 선택 강화", 92, 137, 18, MUTED)
        if game.saved:
            self.text("새 모험은 기존 진행을 새로 시작합니다.", 92, 109, 16, RED)
        if game.notice:
            self.center(game.notice, 83, 14, RED)

    def menu(self, game):
        if game.mode == "title":
            self.shade()
            self.title(game)
        elif game.mode == "select":
            self.shade()
            self.center("라운드 체험", 600, 42, CYAN)
            self.center("위·아래 방향키로 선택 / Enter 시작 / Esc 돌아가기", 558, 18, MUTED)
            for i, stage in enumerate(game.stages):
                y = 525 - i * 29
                color = GOLD if i == game.selected_stage else WHITE
                self.text(("▶ " if i == game.selected_stage else "   ") + stage["id"] + "  " + stage["title"],
                          370, y, 18, color)
            self.center("라운드 체험은 기존 진행 저장을 변경하지 않습니다.", 65, 16, CYAN)
        elif game.inventory_open and game.mode == "play":
            self.shade()
            self.center("획득 아이템", 610, 42, CYAN)
            self.center("클릭 · 휠로 교체 / Tab · Esc로 닫기", 560, 18, MUTED)
            labels = ("기본 검", "냉기 검", "파쇄 검", "얼음 원소", "불 원소")
            descriptions = ("검격과 대시 경로 참격", "근처 적 빙결 · 이동 속도 감소", "갑옷과 결정에 강한 검격",
                            "좌클릭: 잔영에서 빙결탄 연사 · 3초", "좌클릭: 잔영에서 화염탄 연사 · 3초")
            for slot in range(5):
                y = 500 - slot * 70
                owned = slot + 1 in game.available_weapons(game.index) if slot < 3 else ("ice" if slot == 3 else "fire") in game.owned_elements
                selected = (not game.combat.element and game.combat.player.weapon == slot + 1) if slot < 3 else game.combat.element == ("ice" if slot == 3 else "fire")
                rect(265, y - 29, 590, 59, (32, 61, 67) if selected else (20, 31, 42))
                self.ui("slot_selected" if selected else "slot_normal" if owned else "slot_locked", 300, y, 55, 55)
                if owned:
                    if slot < 3:
                        self.ui(("weapon_basic", "weapon_frost", "weapon_shatter")[slot], 300, y, 40, 40)
                    else:
                        self.bank.draw_cell(("ice" if slot == 3 else "fire") + "_relic_test", 0, 0, Vec(300, y), 75, 50)
                self.text(labels[slot] + ("  장착" if selected else "" if owned else "  미획득"), 340, y + 8, 18, GOLD if selected else WHITE if owned else MUTED)
                self.text(descriptions[slot], 340, y - 15, 16, MUTED)
        elif game.paused:
            self.shade()
            self.center("잠시 숨 고르기", 470, 42)
            self.center("Esc / Enter  계속하기", 386, 26, CYAN)
            self.center("Q  타이틀로   /   R  현재 라운드 재시작", 327, 20, MUTED)
            self.center("전투·잔영·보스의 시간은 모두 멈춰 있습니다.", 255, 18, MUTED)
        elif game.mode == "upgrade":
            self.shade()
            reward = ("정화의 검 획득 · 결정과 탄환을 벨 수 있습니다" if game.index == 4 else
                      "파쇄 검 획득 · 다음 라운드부터 3번으로 전환" if game.index == 9 else
                      "검에 남은 빛으로 한 가지 힘을 회복하세요")
            self.center("봉인이 풀렸다", 554, 42, CYAN)
            self.center(reward, 496, 23, WHITE)
            names = [("참격 범위", "경로 주변 공격 반경 +7px"),
                     ("잔영 유지", "발동을 기다리는 시간 +0.2초"),
                     ("이동 속도", "일반 이동 속도 +9%")]
            for i, (name, detail) in enumerate(names):
                level = game.combat.player.upgrades[C.UPGRADES[i]]
                y = 414 - i * 95
                self.text(f"{i + 1}   {name}", 247, y, 26, GOLD if level < C.UPGRADE_LIMIT else MUTED)
                self.text(f"{level} / {C.UPGRADE_LIMIT} 단계    {detail}", 520, y, 20, MUTED)
            if all(level >= C.UPGRADE_LIMIT for level in game.combat.player.upgrades.values()):
                self.center("모든 강화 완료 / Enter로 다음 길 이동", 121, 18, CYAN)
            else:
                self.center("강화 확정 후 다음 길로 이동", 121, 18, CYAN)
            if game.toast_left > 0:
                self.center(game.toast, 166, 18, RED)
        elif game.mode == "defeat":
            self.shade()
            self.center("검의 빛이 흐려졌다", 474, 42, WHITE)
            self.center("R / Enter   현재 라운드 재도전", 379, 26, CYAN)
            self.center("획득한 강화는 유지하고 라운드 시작 상태로 돌아갑니다.", 314, 20, MUTED)
            self.center("Q   타이틀로", 248, 20, GOLD)
        elif game.mode == "victory":
            self.shade()
            self.center("세 봉인 해제", 497, 42, CYAN)
            self.center("드래곤의 침식을 정화했습니다", 429, 26, WHITE)
            self.center("16라운드 모험 완료", 369, 23, GOLD)
            self.center(f"최대 연속 적중  {max(game.records['hits'], game.combat.max_hits)}", 310, 20, MUTED)
            self.center("숲에서 배운 잔영 검술로 성역의 재앙을 끝냈습니다.", 244, 18, MUTED)
            self.center("Enter / Q   타이틀로", 172, 23, CYAN)

    def draw(self, game):
        if game.mode == "transit":
            self.transit_scene(game)
            return
        self.floor(game)
        if game.mode not in ("title", "select"):
            self.scene(game)
            if self.impact_flash > 0:
                rect(30, 98, 1060, 536, WHITE if self.impact_flash < 0.08 else RED,
                     int(80 * self.impact_flash / 0.13))
            self.hud(game)
        self.menu(game)

    def close(self):
        # SDL 종료 전에 네이티브 텍스처와 글꼴을 해제한다.
        self.bank.entries.clear()
        self.fonts.clear()
