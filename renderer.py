"""pico2d 출력 전용. 매끈한 2D 임시 도형은 게임 판정과 독립적이다."""

import math
import random
from pathlib import Path
import pico2d as p
from geometry import Vec
from sprite_bank import SpriteBank
import config as C

INK = (10, 19, 28)
WHITE = (234, 242, 239)
MUTED = (151, 180, 179)
CYAN = (104, 231, 210)
GOLD = (246, 204, 116)
VIOLET = (183, 128, 216)
RED = (234, 108, 112)

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

    def center(self, message, y, size=23, color=WHITE):
        # pico2d Font 내부의 SDL_ttf로 실제 너비를 구한다.
        from ctypes import byref, c_int
        width, height = c_int(), c_int()
        font = self.fonts[size]
        p.TTF_SizeUTF8(font.font, str(message).encode("utf-8"), byref(width), byref(height))
        self.text(message, (C.WIDTH - width.value) // 2, y, size, color)

    def consume(self, events):
        for kind, pos in events:
            if kind in ("hit", "kill", "hurt", "recharge", "open", "crystal_break", "terminal_on",
                        "boss_impact", "boss_breath", "boss_hit"):
                self.effects.append([kind, pos, 0.0])
            if kind == "hurt":
                self.shake = 0.18
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
        for wall in game.combat.arena.walls:
            if has_background:
                rect(wall.x, wall.y, wall.w, wall.h, VIOLET, 48)
                rect(wall.x, wall.y, wall.w, wall.h, CYAN, 140, False)
            else:
                rect(wall.x - 3, wall.y - 5, wall.w + 6, wall.h + 7, INK)
                rect(wall.x, wall.y, wall.w, wall.h, (61, 77, 79) if theme == "forest" else (81, 79, 101))
                rect(wall.x + 3, wall.y + wall.h - 9, wall.w - 6, 7, MUTED, 55)
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
        for bullet in combat.projectiles:
            row = 1 if bullet.kind == "knight" else 0
            frame = int(self.visual_time * 10) % 4
            if not self.bank.draw_cell("projectiles", frame, row, bullet.pos, 34, 34):
                circle(bullet.pos, bullet.radius, WHITE, 230, True)
        if combat.dual_mode and combat.echo_pos is not None:
            alpha = int(70 + 100 * combat.echo_remaining / combat.player.trail_lifetime)
            circle(combat.echo_pos, 31, CYAN, 80)
            self.actor("player", combat.echo_pos, combat.player.facing, ghost=True, alpha=alpha)
        if combat.trail:
            trail = combat.trail
            alpha = int(55 + 95 * trail.remaining / trail.lifetime)
            for a, b in zip(trail.points, trail.points[1:]):
                line(a, b, CYAN, alpha)
            for pos in trail.visible_points():
                circle(pos, combat.player.slash_radius, CYAN, 35)
                self.actor("player", pos, trail.direction, ghost=True, alpha=alpha)
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
        actors = [(e.pos.y, e) for e in combat.enemies]
        actors.append((combat.player.pos.y, combat.player))
        actors.sort(key=lambda item: item[0], reverse=True)
        for _, actor in actors:
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
                    self.dragon_attack = actor.attack
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
            self.actor(kind, actor.pos, direction, state, alpha=alpha,
                       flash=not is_player and actor.flash > 0,
                       animation_time=animation_time)
            if not is_player and actor.kind in ("boar", "sentinel") and actor.hp == 1:
                rect(actor.pos.x - 11, actor.pos.y + 37, 22, 3, RED)
            if self.debug:
                circle(actor.pos, actor.radius, GOLD if is_player else RED, 200)
        for slash in combat.slashes:
            n = len(slash.points)
            indices = (range(n) if slash.style == "dual" else
                       sorted({round(k * (n - 1) / 3) for k in range(4)}))
            for i in indices:
                pos = slash.points[i]
                alpha = int(190 * max(0, 1 - slash.age / 0.27))
                self.actor("player", pos, slash.direction, ghost=True, alpha=alpha)
                self.arc(pos, slash.radius, slash.direction, slash.age, GOLD if slash.boosted else CYAN)
            for center in (slash.points if slash.style == "dual" else [slash.points[n // 2]]):
                self.bank.draw_cell("combat_fx", 0, 0, center, 77, 77,
                                    max(0, 1 - slash.age / 0.27))
        for kind, pos, age in self.effects:
            color = RED if kind == "hurt" else GOLD if kind == "recharge" else CYAN
            alpha = int(max(0, 1 - age / 0.7) * 240)
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
            for i in range(6):
                q = pos + Vec(math.cos(i * 1.8), math.sin(i * 1.8)) * (age * 80 + 5)
                rect(q.x, q.y, 4, 4, color, alpha)
            if kind == "recharge":
                self.text("재대시!", pos.x - 25, pos.y + 42 + age * 30, 18, GOLD)
        if self.debug and combat.trail:
            for point in combat.trail.points:
                circle(point, 2, GOLD, 255, True)

    def hud(self, game):
        c, player = game.combat, game.combat.player
        rect(0, 660, C.WIDTH, 100, INK)
        self.text("잔영의 검", 32, 730, 26, WHITE)
        label = "TRAINING" if game.training else f"{game.stage['id']}  {game.stage['title']}"
        self.text(label, 215, 731, 23, CYAN)
        if game.trial:
            self.text("체험", 650, 731, 18, GOLD)
        for i in range(C.MAX_HP):
            color = RED if i < player.hp else (48, 57, 62)
            rect(34 + i * 25, 685, 18, 16, color)
            rect(38 + i * 25, 702, 10, 3, color)
        if c.dual_mode:
            status = ("대시 중" if player.dash_left else "J  검사 + 잔영 동시 검격" if c.echo_pos is not None
                      else f"검격 대기 {player.cooldown:.1f}초" if player.cooldown > 0
                      else "J  직접 검격 / Space 잔영 배치")
        else:
            status = "DASH READY" if c.ready else "DASHING" if player.dash_left else "J : 참격" if c.trail else "참격 중" if any(not s.resolved for s in c.slashes) else f"충전 {player.cooldown:.1f}s"
        self.text(status, 215, 695, 20, CYAN if c.ready else GOLD)
        if not c.dual_mode:
            self.text(f"최대 동시 적중 {c.max_hits}", 450, 695, 18, MUTED)
        goal = "적을 모아 잔영으로 베어 보세요" if game.training else f"봉인 해제  {min(c.kills, game.stage['goal'])} / {game.stage['goal']}"
        self.text(goal, 720, 731, 20, GOLD)
        rect(722, 688, 308, 8, (42, 49, 59))
        ratio = 0 if game.training else min(1, c.kills / game.stage["goal"])
        rect(722, 688, 308 * ratio, 8, CYAN)
        if c.trail:
            self.text(f"잔영 {c.trail.remaining:.1f}초", 450, 731, 18, CYAN)
        if c.dual_mode and c.echo_pos is not None:
            self.text(f"잔영 {c.echo_remaining:.1f}초", 610, 695, 18, CYAN)
        if c.prism:
            self.text("PRISM / 다음 참격 확대", 720, 667, 16, GOLD)
        bosses = [e for e in c.enemies if e.kind in ("guardian", "knight", "dragon")]
        if bosses:
            boss = bosses[0]
            rect(300, 562, 520, 13, (30, 20, 37))
            rect(300, 562, 520 * boss.hp / boss.max_hp, 13, VIOLET)
            label = {"guardian": "숲의 수호수", "knight": "봉인 수호기사", "dragon": "침식된 드래곤"}[boss.kind]
            state = {"tell": "공격 예고", "charge": "돌진", "attack": "공격", "weak": "약점! J 참격", "recover": "회복", "approach": "대기"}[boss.state]
            self.text(label + "  /  " + state, 360, 583, 18, GOLD if boss.state == "weak" else WHITE)
        rect(0, 0, C.WIDTH, 78, INK)
        controls = ("WASD / 방향키  이동     J  직접 검격     Space  잔영 대시"
                    if c.dual_mode else "WASD / 방향키  이동     Space  대시     J  잔영 참격")
        self.text(controls, 32, 51, 18, WHITE)
        self.text("Esc 일시정지    F1 판정 표시    M 효과음 " + ("켜짐" if self.audio_enabled else "꺼짐"), 32, 23, 16, MUTED)
        if game.toast_left > 0:
            rect(160, 120, 800, 43, INK, 230)
            self.center(game.toast, 143, 18, GOLD)
        elif game.banner_left > 0:
            rect(55, 120, 1010, 43, INK, 230)
            self.center(game.stage["tip"], 143, 16, MUTED)
        if game.notice:
            self.text(game.notice, 55, 82, 14, RED)

    def shade(self):
        rect(0, 78, C.WIDTH, 582, INK, 240)

    def title(self, game):
        # 임시 2D 타이틀 연출. 실제 게임과 같은 스프라이트를 사용한다.
        for i in range(4):
            pos = Vec(690 + i * 70, 420 + i * 16)
            self.actor("player", pos, Vec(1, 0), ghost=i < 3, alpha=60 + i * 55)
        self.text("잔영의 검", 86, 514, 64, WHITE)
        self.text("이동한 자리에 검격을 남긴다", 91, 448, 26, CYAN)
        self.text("몬스터 처치  ·  봉인 해제  ·  검의 성장", 92, 401, 20, MUTED)
        self.text("Enter   새 모험", 94, 310, 26, WHITE)
        self.text("C          이어하기" + ("" if game.saved else "  (기록 없음)"), 94, 262, 23, CYAN if game.saved else MUTED)
        self.text("T          잔영 검술 연습장", 94, 215, 23, GOLD)
        self.text("F2         라운드 체험 (저장 유지)", 94, 178, 20, CYAN)
        self.text("숲·요새·성역 15라운드 / 수호기사·드래곤 / 선택 강화", 92, 137, 18, MUTED)
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
        elif game.paused:
            self.shade()
            self.center("잠시 숨 고르기", 470, 42)
            self.center("Esc / Enter  계속하기", 386, 26, CYAN)
            self.center("Q  타이틀로   /   R  현재 라운드 재시작", 327, 20, MUTED)
            self.center("전투·잔영·보스의 시간은 모두 멈춰 있습니다.", 255, 18, MUTED)
        elif game.mode == "upgrade":
            self.shade()
            self.center("봉인이 풀렸다", 554, 42, CYAN)
            self.center("검에 남은 빛으로 한 가지 힘을 회복하세요", 496, 23, WHITE)
            names = [("참격 범위", "경로 주변 공격 반경 +7px"),
                     ("잔영 유지", "발동을 기다리는 시간 +0.2초"),
                     ("이동 속도", "일반 이동 속도 +9%")]
            for i, (name, detail) in enumerate(names):
                level = game.combat.player.upgrades[C.UPGRADES[i]]
                y = 414 - i * 95
                self.text(f"{i + 1}   {name}", 247, y, 26, GOLD if level < C.UPGRADE_LIMIT else MUTED)
                self.text(f"{level} / {C.UPGRADE_LIMIT} 단계    {detail}", 520, y, 20, MUTED)
            if all(level >= C.UPGRADE_LIMIT for level in game.combat.player.upgrades.values()):
                self.center("모든 강화 완료 / Enter로 다음 라운드", 121, 18, CYAN)
            else:
                self.center("강화 확정 후 체력 완전 회복 / 다음 라운드로 이동", 121, 18, CYAN)
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
            self.center("15라운드 모험 완료", 369, 23, GOLD)
            self.center(f"최대 동시 적중  {max(game.records['hits'], game.combat.max_hits)}", 310, 20, MUTED)
            self.center("숲에서 배운 잔영 검술로 성역의 재앙을 끝냈습니다.", 244, 18, MUTED)
            self.center("Enter / Q   타이틀로", 172, 23, CYAN)

    def draw(self, game):
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
