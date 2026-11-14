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

HERO = (
    "....hhhhh.....", "...hhhhhhh....", "..hhhwwhhhh...", "..hhwwwwwhh...",
    "...hsssssh....", "...seseess....", "....sssss.....", "..tttttttttt..",
    "..ttaaaatt....", "...aaaaaaa....", "..saaAAaas....", "..saaAAaas....",
    "...aaaaaa.....", "...dddddd.....", "...dd..dd.....", "..bbb..bbb....")
WOLF = (
    "..v......v...", "..vv....vv...", "..vkvvvvkv...", "...vvvvvv....",
    "..vvrvvrvv...", "..vvvvvvvv...", "...vvvvvv....", "....vvvv.....",
    "...vvvvvv....", "..vvvvvvvv...", "..kkvvvvkk...", "....vvvv.....",
    "...kk..kk....")
BOAR = (
    "...aa..aa....", "..aaaaaaaa...", ".aaappppaaa..", "aaappppppaaa.",
    "aaappppppaaa.", "aaappppppaaa.", "aaappppppaaa.", ".aaaaaaaaaa..",
    "..arAAAra....", "..aaAAAaa....", "..wAAAAAw....", "..wAAAAAw....",
    "...AAAAA.....", "...kk.kk.....")


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
        self.visual_time = 0
        rng = random.Random(41)
        self.grass = [(rng.randint(55, 1064), rng.randint(119, 613), rng.randrange(3)) for _ in range(180)]
        self.palette = {"h": (167, 184, 200), "w": (222, 237, 241), "s": (227, 192, 155),
                        "e": (24, 39, 54), "t": (63, 202, 182), "a": (49, 73, 99),
                        "A": (122, 145, 152), "d": (40, 46, 66), "b": (25, 32, 43),
                        "v": (103, 62, 132), "k": (43, 32, 57), "r": (232, 108, 144),
                        "p": (174, 104, 169)}

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
            if kind in ("hit", "kill", "hurt", "recharge", "open"):
                self.effects.append([kind, pos, 0.0])
            if kind == "hurt":
                self.shake = 0.18
        events.clear()

    def tick(self, dt):
        self.visual_time += dt
        self.shake = max(0, self.shake - dt)
        for item in self.effects:
            item[2] += dt
        self.effects = [e for e in self.effects if e[2] < 0.7]

    def pixel(self, pattern, pos, scale=3, ghost=False, alpha=255, flash=False, bob=0):
        width, height = len(pattern[0]), len(pattern)
        ox, oy = pos.x - width * scale / 2, pos.y + height * scale / 2 + 6 + bob
        for row, contents in enumerate(pattern):
            col = 0
            while col < len(contents):
                char = contents[col]
                end = col + 1
                while end < len(contents) and contents[end] == char:
                    end += 1
                if char != ".":
                    color = WHITE if flash else CYAN if ghost else self.palette.get(char, WHITE)
                    rect(ox + col * scale, oy - (row + 1) * scale, (end - col) * scale, scale, color, alpha)
                col = end

    def actor(self, kind, pos, direction, state="idle", ghost=False, alpha=255, flash=False):
        scale = 2 if kind in ("guardian", "knight", "dragon") else 1
        if not ghost:
            circle(pos + Vec(0, -9), 19 * scale, INK, 110, True)
        if self.bank.draw("player" if ghost else kind, pos, self.visual_time, direction, state,
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
        if kind in ("mage", "knight"):
            circle(center, 18 * scale, GOLD if state == "weak" else color, 80, False)
        if kind == "dragon":
            for sign in (-1, 1):
                wing = center + side * (sign * 27 * scale)
                circle(wing, 12 * scale, color, alpha // 2, True)
        if kind == "player":
            grip = center + side * 12
            line(grip, grip + direction * (31 if state == "slash" else 23), CYAN if ghost else WHITE, alpha)
            circle(center + direction * 7, 5, GOLD, alpha, True)

    def floor(self, game):
        rect(0, 0, C.WIDTH, C.HEIGHT, INK)
        theme = game.stage.get("theme", "forest")
        base = {"forest": (25, 48, 45), "fortress": (42, 43, 60),
                "sanctuary": (40, 38, 60)}[theme]
        rect(30, 98, 1060, 536, base)
        if not self.bank.draw(theme, Vec(560, 366), 0, scale=1):
            for x, y, tone in self.grass:
                if theme == "forest":
                    circle(Vec(x, y), 2 + tone, (49, 89, 69), 90, True)
                else:
                    circle(Vec(x, y), 2 + tone, VIOLET if theme == "sanctuary" else MUTED, 35, True)
            for x in range(92, 1050, 120):
                for y in (153, 555):
                    circle(Vec(x, y), 18 if theme == "forest" else 10,
                           (45, 84, 67) if theme == "forest" else (73, 72, 92), 120, True)
        for x in range(42, 1080, 65):
            for y in (105, 626):
                circle(Vec(x, y), 15 if theme == "forest" else 9,
                       (39, 76, 59) if theme == "forest" else (93, 89, 111), 200, True)
        for wall in game.combat.arena.walls:
            rect(wall.x - 3, wall.y - 5, wall.w + 6, wall.h + 7, INK)
            rect(wall.x, wall.y, wall.w, wall.h, (61, 77, 79) if theme == "forest" else (81, 79, 101))
            rect(wall.x + 3, wall.y + wall.h - 9, wall.w - 6, 7, MUTED, 55)
        gate_color = CYAN if game.gate_open else VIOLET
        rect(510, 588, 100, 40, (12, 23, 32))
        rect(508, 586, 9, 44, gate_color)
        rect(603, 586, 9, 44, gate_color)
        if game.gate_open:
            rect(520, 590, 80, 36, CYAN, 35 + int(20 * (1 + math.sin(self.visual_time * 4))))
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
            circle(game.hazard_marker, 70, color, 45, True)
        for device in combat.devices:
            color = WHITE if device.flash else GOLD if device.kind == "terminal" else VIOLET
            circle(device.pos, device.radius + 7, color, 90)
            circle(device.pos, device.radius, color, 180, True)
            circle(device.pos, device.radius - 9, INK, 220, True)
            if device.kind == "crystal":
                circle(device.pos, 7, color, 220, True)
                if device.hp > 1:
                    circle(device.pos, device.radius + 11, color, 180)
            else:
                self.text(device.link, device.pos.x - 5, device.pos.y - 8, 16, color)
        for bullet in combat.projectiles:
            circle(bullet.pos, bullet.radius + 5, VIOLET, 85, True)
            circle(bullet.pos, bullet.radius, WHITE, 230, True)
        if combat.trail:
            trail = combat.trail
            alpha = int(55 + 95 * trail.remaining / trail.lifetime)
            for a, b in zip(trail.points, trail.points[1:]):
                line(a, b, CYAN, alpha)
            for pos in trail.visible_points():
                circle(pos, combat.player.slash_radius, CYAN, 35)
                self.actor("player", pos, trail.direction, ghost=True, alpha=alpha)
        for enemy in combat.enemies:
            if enemy.state == "tell":
                length = 290 if enemy.kind in ("guardian", "knight") else 230
                end = enemy.pos + enemy.direction * length
                side = Vec(-enemy.direction.y, enemy.direction.x) * enemy.radius
                color = RED if enemy.kind == "guardian" else GOLD
                line(enemy.pos - side, end - side, color, 170)
                line(enemy.pos + side, end + side, color, 170)
                line(end - side, end + side, color, 170)
                circle(enemy.pos, enemy.radius + 7, color, 180)
            if enemy.kind in ("guardian", "knight", "dragon") and enemy.state == "weak":
                circle(enemy.pos, enemy.radius + 7, GOLD, 160)
            if enemy.kind == "dragon" and enemy.state in ("tell", "attack"):
                color = RED if enemy.state == "attack" else GOLD
                if enemy.attack == "stomp":
                    circle(enemy.marker, 90, color, 180)
                    circle(enemy.marker, 90, color, 35, True)
                else:
                    side = Vec(-enemy.direction.y, enemy.direction.x) * 56
                    end = enemy.pos + enemy.direction * 440
                    line(enemy.pos - side, end - side, color, 180)
                    line(enemy.pos + side, end + side, color, 180)
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
            self.actor(kind, actor.pos, direction, state, alpha=alpha,
                       flash=not is_player and actor.flash > 0)
            if not is_player and actor.kind in ("boar", "sentinel") and actor.hp == 1:
                rect(actor.pos.x - 11, actor.pos.y + 37, 22, 3, RED)
            if self.debug:
                circle(actor.pos, actor.radius, GOLD if is_player else RED, 200)
        for slash in combat.slashes:
            n = len(slash.points)
            for i in sorted({round(k * (n - 1) / 3) for k in range(4)}):
                pos = slash.points[i]
                alpha = int(190 * max(0, 1 - slash.age / 0.27))
                self.actor("player", pos, slash.direction, ghost=True, alpha=alpha)
                self.arc(pos, slash.radius, slash.direction, slash.age, GOLD if slash.boosted else CYAN)
        for kind, pos, age in self.effects:
            color = RED if kind == "hurt" else GOLD if kind == "recharge" else CYAN
            alpha = int(max(0, 1 - age / 0.7) * 240)
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
        self.text("TRAINING" if game.training else f"{game.stage['id']}  {game.stage['title']}", 215, 731, 23, CYAN)
        for i in range(C.MAX_HP):
            color = RED if i < player.hp else (48, 57, 62)
            rect(34 + i * 25, 685, 18, 16, color)
            rect(38 + i * 25, 702, 10, 3, color)
        status = "DASH READY" if c.ready else "DASHING" if player.dash_left else "J : 참격" if c.trail else "참격 중" if any(not s.resolved for s in c.slashes) else f"충전 {player.cooldown:.1f}s"
        self.text(status, 215, 695, 20, CYAN if c.ready else GOLD)
        self.text(f"최대 동시 적중 {c.max_hits}", 450, 695, 18, MUTED)
        goal = "적을 모아 잔영으로 베어 보세요" if game.training else f"봉인 해제  {min(c.kills, game.stage['goal'])} / {game.stage['goal']} 처치"
        self.text(goal, 720, 731, 20, GOLD)
        rect(722, 688, 308, 8, (42, 49, 59))
        ratio = 0 if game.training else min(1, c.kills / game.stage["goal"])
        rect(722, 688, 308 * ratio, 8, CYAN)
        if c.trail:
            self.text(f"잔영 {c.trail.remaining:.1f}초", 450, 731, 18, CYAN)
        if c.prism:
            self.text("PRISM / 다음 참격 확대", 720, 667, 16, GOLD)
        bosses = [e for e in c.enemies if e.kind in ("guardian", "knight", "dragon")]
        if bosses:
            boss = bosses[0]
            rect(300, 591, 520, 13, (30, 20, 37))
            rect(300, 591, 520 * boss.hp / boss.max_hp, 13, VIOLET)
            label = {"guardian": "숲의 수호수", "knight": "봉인 수호기사", "dragon": "침식된 드래곤"}[boss.kind]
            state = {"tell": "공격 예고", "charge": "돌진", "attack": "공격", "weak": "약점! J 참격", "recover": "회복", "approach": "대기"}[boss.state]
            self.text(label + "  /  " + state, 360, 616, 18, GOLD if boss.state == "weak" else WHITE)
        rect(0, 0, C.WIDTH, 78, INK)
        self.text("WASD / 방향키  이동     Space  대시     J  잔영 참격", 32, 51, 18, WHITE)
        self.text("Esc 일시정지    F1 판정 표시    M 효과음 " + ("켜짐" if self.audio_enabled else "꺼짐"), 32, 23, 16, MUTED)
        self.text("임시 2D 그래픽 / 교체 가능", 850, 25, 14, MUTED)
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
        self.text("숲·요새·성역 15라운드 / 수호기사·드래곤 / 선택 강화", 92, 145, 18, MUTED)
        if game.saved:
            self.text("새 모험은 기존 진행을 새로 시작합니다.", 92, 109, 16, RED)
        if game.notice:
            self.center(game.notice, 83, 14, RED)

    def menu(self, game):
        if game.mode == "title":
            self.shade()
            self.title(game)
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
        if game.mode != "title":
            self.scene(game)
            self.hud(game)
        self.menu(game)

    def close(self):
        # SDL 종료 전에 네이티브 텍스처와 글꼴을 해제한다.
        self.bank.entries.clear()
        self.fonts.clear()
