"""키 입력과 같은 로직 호출만 사용하는 결정적 자동 플레이 진단.

체력/피해/처치 수를 변경하지 않는다. 봇의 승리는 게임성 평가를 대신하지 않는다.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from game import Game
from geometry import Vec, path_hits


def steer(arena, pos, desired, radius=14):
    candidates = [desired, Vec(-desired.y, desired.x), Vec(desired.y, -desired.x), desired * -1]
    return next((v for v in candidates if arena.valid(pos + v * 35, radius)), Vec())


def run(start=0):
    game = Game(Path(__file__).resolve().parents[1] / ".cache/playthrough.json")
    game.new_game()
    if start:
        game.load_stage(start, {"range": 2, "lifetime": 1, "speed": 1})
    defeated, seen, previous = 0, [], -1
    for tick in range(120 * 1200):
        if game.index != previous:
            previous = game.index
            seen.append(game.stage["id"])
            print("ENTER", game.stage["id"])
        if game.mode == "victory":
            print("PLAYTHROUGH OK:", " / ".join(seen), "재도전", defeated)
            return True
        if game.mode == "upgrade":
            choice = next((i for i, key in enumerate(("range", "lifetime", "speed"))
                           if game.combat.player.upgrades[key] < 3), None)
            if choice is None:
                game.skip_upgrade()
            else:
                game.choose_upgrade(choice)
            continue
        if game.mode == "defeat":
            defeated += 1
            print("RETRY", game.stage["id"], "kills", game.combat.kills)
            if defeated > 24:
                break
            game.retry()
            continue
        c, player = game.combat, game.combat.player
        direction = Vec()
        if game.gate_open:
            direction = (Vec(560, 604) - player.pos).normalized()
        elif not c.enemies and c.devices:
            linked = next((d for d in c.devices if d.link), None)
            if linked:
                partner = next(d for d in c.devices if d is not linked and d.link == linked.link)
                left, right = sorted((linked, partner), key=lambda d: d.pos.x)
                origin = Vec(left.pos.x - 45, (left.pos.y + right.pos.y) / 2)
                delta = origin - player.pos
                if delta.length() > 15:
                    direction = steer(c.arena, player.pos, delta.normalized())
                elif c.ready:
                    player.facing = Vec(1, 0)
                    c.dash()
                if c.trail and not player.dash_left and all(path_hits(c.trail.points, d.pos, player.slash_radius + d.radius) for d in (left, right)):
                    c.slash()
            else:
                target = min(c.devices, key=lambda d: d.pos.distance(player.pos))
                delta = target.pos - player.pos
                distance = delta.length()
                direction = steer(c.arena, player.pos, delta.normalized() if distance > 115 else delta.normalized() * -1)
                if c.ready and 80 < distance < 185:
                    player.facing = delta.normalized()
                    c.dash()
                if c.trail and not player.dash_left and path_hits(c.trail.points, target.pos, player.slash_radius + target.radius):
                    c.slash()
        elif c.enemies:
            wolves = [e for e in c.enemies if e.kind in ("wolf", "mage")]
            target = min(wolves or c.enemies, key=lambda e: e.pos.distance(player.pos))
            delta = target.pos - player.pos
            distance = delta.length()
            if target.kind == "dragon":
                if target.state == "tell" and target.timer < 0.14 and c.ready and distance < 95:
                    player.facing = Vec(-target.direction.y, target.direction.x)
                    c.dash()
                elif target.state in ("approach", "recover", "tell", "weak", "attack"):
                    direction = delta.normalized() if distance > 78 else delta.normalized() * -1 if distance < 68 else Vec()
                if target.state == "weak" and not player.dash_left:
                    if c.dual_mode:
                        origins = [player.pos] + ([c.echo_pos] if c.echo_pos is not None else [])
                        origin = min(origins, key=lambda p: p.distance(target.pos))
                        if origin.distance(target.pos) <= 55 + player.upgrades["range"] * 7 + target.radius:
                            player.facing = (target.pos - origin).normalized()
                            c.slash()
                    elif c.trail and path_hits(c.trail.points, target.pos, player.slash_radius + target.radius):
                        c.slash()
            elif target.kind in ("guardian", "knight", "boar", "sentinel"):
                if target.state == "tell" and target.timer < 0.16 and c.ready:
                    side = Vec(-target.direction.y, target.direction.x)
                    options = [side, side * -1]
                    direction = max(options, key=lambda d: int(c.arena.valid(player.pos + d * 180, player.radius)))
                    player.facing = direction
                    c.dash()
                elif target.state in ("approach", "chase"):
                    # 돌진을 맞을 위치로 유도하되 너무 가까워지지 않는다.
                    direction = delta.normalized() if distance > 210 else delta.normalized() * -1 if distance < 150 else Vec()
                vulnerable = target.state == "weak" if target.kind in ("guardian", "knight") else target.state in ("charge", "recover")
                if c.trail and not player.dash_left and vulnerable:
                    if path_hits(c.trail.points, target.pos, player.slash_radius + target.radius):
                        c.slash()
            else:
                if c.ready and distance < (230 if target.kind == "mage" else 185):
                    player.facing = delta.normalized()
                    c.dash()
                if c.trail and not player.dash_left:
                    hit = any(path_hits(c.trail.points, e.pos, player.slash_radius + e.radius) for e in c.enemies)
                    if hit or c.trail.remaining < 0.12:
                        c.slash()
                direction = ((delta.normalized() if distance > 125 else delta.normalized() * -1)
                             if target.kind == "mage" else
                             (delta.normalized() if distance > (95 if c.defend_pos is not None else 205)
                              else delta.normalized() * -1))
                if target.state in ("tell", "charge") and distance < 240:
                    direction = Vec(-target.direction.y, target.direction.x)
            threats = []
            for e in c.enemies:
                if e.kind not in ("boar", "sentinel") or e.state != "charge":
                    continue
                offset = player.pos - e.pos
                along = offset.x * e.direction.x + offset.y * e.direction.y
                across = abs(offset.x * e.direction.y - offset.y * e.direction.x)
                if -25 < along < 270 and across < e.radius + player.radius + 24:
                    threats.append(e)
            if threats:
                e = min(threats, key=lambda b: b.pos.distance(player.pos))
                perpendicular = Vec(-e.direction.y, e.direction.x)
                options = [perpendicular, perpendicular * -1]
                direction = max(options, key=lambda d: (
                    int(c.arena.valid(player.pos + d * 100, player.radius)),
                    min((player.pos + d * 80).distance(b.pos) for b in c.enemies)))
                if c.ready:
                    player.facing = direction
                    c.dash()
            direction = steer(c.arena, player.pos, direction)
        if game.hazard_marker and game.hazard_active == 0 and player.pos.distance(game.hazard_marker) < 100:
            direction = steer(c.arena, player.pos, (player.pos - game.hazard_marker).normalized())
        game.update(1 / 120, direction)
        c.events.clear()
    print("PLAYTHROUGH INCOMPLETE:", game.stage["id"], game.mode, "HP", game.combat.player.hp,
          "kills", game.combat.kills, "seconds", round(game.combat.elapsed, 1),
          "pos", game.combat.player.pos, "devices", [(d.kind, d.pos) for d in game.combat.devices],
          "enemies", [(e.kind, e.pos) for e in game.combat.enemies],
          "ready", game.combat.ready, "trail", len(game.combat.trail.points) if game.combat.trail else 0)
    return False


if __name__ == "__main__":
    raise SystemExit(0 if run() else 1)
