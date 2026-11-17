"""잔영의 검 진입점. VS Code에서 이 파일을 F5로 실행한다."""

import argparse
from pathlib import Path
import sys
import time

import config as C
from geometry import Vec
from input_controls import mouse_position
from campaign import CampaignGame as Game


def capture_png(path, pico):
    """자동 실행 확인용: SDL의 현재 출력 버퍼를 PNG로 저장한다."""
    import pico2d.pico2d as engine
    from sdl2 import (SDL_CreateRGBSurfaceWithFormat, SDL_PIXELFORMAT_ARGB8888,
                      SDL_RenderReadPixels, SDL_FreeSurface)
    from sdl2.sdlimage import IMG_SavePNG
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    surface = SDL_CreateRGBSurfaceWithFormat(0, C.WIDTH, C.HEIGHT, 32, SDL_PIXELFORMAT_ARGB8888)
    if not surface:
        raise RuntimeError("화면 캡처용 버퍼 생성 실패")
    try:
        data = surface.contents
        if SDL_RenderReadPixels(engine.renderer, None, SDL_PIXELFORMAT_ARGB8888, data.pixels, data.pitch):
            raise RuntimeError("화면 캡처 실패")
        if IMG_SavePNG(surface, str(path).encode("utf-8")):
            raise RuntimeError("PNG 저장 실패")
    finally:
        SDL_FreeSurface(surface)


def prepare_scene(game, name):
    """스모크 테스트 전용 장면. 사용자의 진행 저장을 건드리지 않는다."""
    if name in ("hub", "forge", "map", "inventory"):
        game.new_game()
        if name == "inventory": game.toggle_inventory()
        else: game.mode = name
        return
    if name == "title":
        return
    if name == "select":
        game.open_trial_select()
        game.selected_stage = 14
        return
    game.training = False
    scene_stages = {"boss": 4, "fortress": 5, "devices": 6, "knight": 9, "chain": 0, "beacon": 1,
                    "weapon-frost": 8, "weapon-shatter": 10,
                    "sanctuary": 10, "dragon": 14, "dragon-dual": 14, "dragon-windup": 14,
                    "final": 15, "parry": 15, "inventory": 15, "element-ice": 15, "element-fire": 15, "fire-volley": 15, "transit": 4,
                    "dragon-attack": 14}
    game.start_trial(min(14, scene_stages.get(name, 0)))
    if name == "play":
        game.combat.player.pos = Vec(660, 315)
        game.combat.player.facing = Vec(1, 0)
        from afterimage import Trail
        game.combat.trail = Trail(Vec(470, 315), Vec(1, 0), 1.2)
        game.combat.trail.record(Vec(660, 315))
        game.combat.trail.finish()
        game.combat.spawn("wolf", Vec(500, 375))
        game.combat.spawn("wolf", Vec(560, 390))
        game.combat.spawn("boar", Vec(800, 450))
    if name == "chain":
        from afterimage import Trail
        game.combat.player.pos = Vec(760, 340)
        game.combat.player.facing = Vec(1, 0)
        game.combat.trail = Trail(Vec(330, 340), Vec(1, 0), 1.2)
        game.combat.trail.record(Vec(760, 340))
        game.combat.trail.finish()
        game.combat.spawn("wolf", Vec(430, 370))
        game.combat.spawn("wolf", Vec(560, 370))
        game.combat.spawn("wolf", Vec(690, 370))
        game.combat.slash()
        for _ in range(22):
            game.combat.update(1 / 120)
    if name in ("element-ice", "element-fire", "fire-volley"):
        from afterimage import Trail
        kind = "fire" if name == "fire-volley" else name.split("-")[1]
        drop = next(pos for element, pos in game.element_drops if element == kind)
        game.combat.player.pos = drop
        game.pickup_element()
        game.combat.player.pos = Vec(760, 325)
        game.combat.player.facing = Vec(1, 0)
        game.combat.trail = Trail(Vec(340, 325), Vec(1, 0), 1.2, kind)
        game.combat.trail.record(game.combat.player.pos)
        game.combat.trail.finish()
        if name == "fire-volley":
            game.combat.element_skill.cast(game.combat, Vec(0, 1))
            game.combat.element_skill.update(0.25, game.combat)
    if name == "fortress":
        game.combat.spawn("mage", Vec(360, 470))
        game.combat.spawn("sentinel", Vec(770, 470))
    if name == "beacon":
        game.combat.spawn("wolf", Vec(470, 455))
        game.combat.spawn("wolf", Vec(650, 455))
    if name == "transit":
        game.trial = True
        game.gate_open = True
        game.enter_gate()
        game.choose_upgrade(0)
        game.transit_progress = 0.5
    if name in ("weapon-frost", "weapon-shatter"):
        game.combat.player.weapon = 2 if name == "weapon-frost" else 3
        game.combat.player.pos = Vec(560, 330)
        game.combat.player.facing = Vec(0, 1)
        if name == "weapon-frost":
            game.combat.spawn("sentinel", Vec(560, 405))
        game.combat.slash()
        for _ in range(8):
            game.combat.update(1 / 120)
    if name == "dragon-attack":
        dragon = game.combat.enemies[0]
        dragon.attack, dragon.state, dragon.timer = "breath", "attack", 0.3
        dragon.direction = Vec(0, -1)
        dragon.breath_reach = 210
        game.combat.events.append(("boss_breath", dragon.pos))
    if name == "dragon-windup":
        dragon = game.combat.enemies[0]
        dragon.attack, dragon.state, dragon.timer = "breath", "tell", 0.35
        dragon.direction = Vec(0, -1)
    if name == "dragon-dual":
        dragon = game.combat.enemies[0]
        dragon.state, dragon.timer = "weak", 1.0
        game.combat.player.pos = Vec(620, 410)
        game.combat.player.facing = Vec(0, 1)
        from afterimage import Trail
        game.combat.trail = Trail(Vec(500, 410), Vec(1, 0), 1.2)
        game.combat.trail.record(Vec(620, 410))
        game.combat.trail.finish()
        game.combat.slash()
    if name in ("upgrade", "defeat", "victory"):
        game.mode = name
    if name == "inventory":
        game.owned_elements = ["ice", "fire"]
        game.combat.element = "fire"
        game.toggle_inventory()
    if name == "parry":
        c = game.combat
        boss = c.enemies[0]
        c.player.pos = Vec(560, 310)
        boss.pos = Vec(560, 375)
        boss.state, boss.timer, boss.direction = "charge", 0.5, Vec(0, -1)
        boss.shield_element = "fire"
        c.parry()
        c.update(1 / 120)
        c.dash(Vec(1, 0))
        for _ in range(23):
            c.update(1 / 120)


def main(argv=None):
    parser = argparse.ArgumentParser(description="잔영의 검 / Python + pico2d")
    parser.add_argument("--training", action="store_true", help="저장하지 않는 연습장으로 시작")
    parser.add_argument("--element-demo", action="store_true", help="저장하지 않고 3-6 원소 체험으로 바로 시작")
    parser.add_argument("--combat-demo", action="store_true", help="저장하지 않고 2-4 자동 잔영 전투로 바로 시작")
    parser.add_argument("--smoke-test", action="store_true", help="정해진 프레임 후 종료하는 렌더 검사")
    parser.add_argument("--scene", choices=("hub", "forge", "map", "title", "select", "play", "boss", "fortress", "devices", "knight", "chain", "beacon", "weapon-frost", "weapon-shatter", "transit",
                                            "sanctuary", "dragon", "dragon-dual", "dragon-windup", "dragon-attack", "final", "element-ice", "element-fire", "fire-volley", "inventory", "parry",
                                            "upgrade", "defeat", "victory"), default="play")
    parser.add_argument("--frames", type=int, default=120)
    parser.add_argument("--capture", type=Path)
    parser.add_argument("--mute", action="store_true")
    args = parser.parse_args(argv)
    try:
        import pico2d as pico
    except ImportError:
        print("pico2d가 없습니다. 선택한 Python에서 python -m pip install -r requirements.txt 를 실행하세요.")
        return 1
    from campaign_renderer import CampaignRenderer as Renderer
    from audio import Audio
    import pico2d.pico2d as engine
    from sdl2 import (SDL_SetRenderDrawBlendMode, SDL_BLENDMODE_BLEND, SDL_SetWindowTitle,
                      SDL_GetWindowFlags, SDL_WINDOW_INPUT_FOCUS)

    pico.open_canvas(C.WIDTH, C.HEIGHT, sync=not args.smoke_test)
    SDL_SetWindowTitle(engine.window, "잔영의 검 | Afterimage Sword".encode("utf-8"))
    SDL_SetRenderDrawBlendMode(engine.renderer, SDL_BLENDMODE_BLEND)
    renderer, audio = None, None
    try:
        renderer = Renderer()
        audio = Audio(pico, not args.mute and not args.smoke_test)
        renderer.audio_enabled = audio.enabled
        for warning in renderer.bank.warnings:
            print("임시 그래픽 사용:", warning)
        game = Game(save_path=Path(__file__).resolve().parent / (".cache/smoke-save.json" if args.smoke_test else "saves/campaign_progress.json"))
        if args.smoke_test:
            prepare_scene(game, args.scene)
        elif args.element_demo:
            game.open_trial_select()
            game.start_trial(14)
        elif args.combat_demo:
            game.open_trial_select()
            game.start_trial(8)
        elif args.training:
            game.start_training()
        pressed = set()
        mouse_pos = Vec(C.WIDTH / 2, C.HEIGHT / 2)
        running, frames, accumulator = True, 0, 0.0
        last = time.perf_counter()
        was_focused = bool(SDL_GetWindowFlags(engine.window) & SDL_WINDOW_INPUT_FOCUS)
        while running:
            now = time.perf_counter()
            dt = 1 / 60 if args.smoke_test else min(0.12, now - last)
            last = now
            focused = bool(SDL_GetWindowFlags(engine.window) & SDL_WINDOW_INPUT_FOCUS)
            if was_focused and not focused and not args.smoke_test:
                pressed.clear()
                if game.mode == "play":
                    game.paused = True
            was_focused = focused
            if focused and not args.smoke_test:
                mouse_pos = mouse_position(engine.window)
            renderer.tick(dt if not game.paused else 0)
            for event in pico.get_events():
                if event.type == pico.SDL_QUIT:
                    running = False
                elif event.type == pico.SDL_KEYUP:
                    pressed.discard(event.key)
                elif event.type == pico.SDL_MOUSEMOTION:
                    mouse_pos = mouse_position(engine.window)
                    game.pointer_pos = mouse_pos
                    if game.mode == "play" and not game.paused:
                        game.combat.aim_at(mouse_pos)
                elif event.type == pico.SDL_MOUSEWHEEL:
                    if game.mode == "play" and not game.paused and event.y:
                        game.cycle_item(1 if event.y < 0 else -1)
                elif event.type == pico.SDL_MOUSEBUTTONUP:
                    mouse_pos = mouse_position(engine.window)
                    game.pointer_pos = mouse_pos
                    renderer.release(game, mouse_pos, event.button)
                elif event.type == pico.SDL_MOUSEBUTTONDOWN:
                    mouse_pos = mouse_position(engine.window)
                    game.pointer_pos = mouse_pos
                    if game.mode == "play" and not game.paused:
                        game.combat.aim_at(mouse_pos)
                    if renderer.click(game, mouse_pos, event.button):
                        continue
                    if game.mode != "play":
                        continue
                    if game.inventory_open:
                        if event.button == 1 and 265 <= mouse_pos.x <= 855:
                            row = round((500 - mouse_pos.y) / 70)
                            if 0 <= row < 5 and abs(mouse_pos.y - (500 - row * 70)) <= 29:
                                game.select_item(row)
                        continue
                    if game.paused:
                        continue
                    if event.button == 1 and 575 <= mouse_pos.y <= 641 and 35 <= mouse_pos.x < 325:
                        game.select_item(int((mouse_pos.x - 35) // 58))
                    elif 98 <= mouse_pos.y <= 634 and 30 <= mouse_pos.x <= 1090:
                        aim = (mouse_pos - game.combat.player.pos).normalized()
                        if aim.length():
                            game.combat.player.facing = aim
                        if event.button == 3:
                            game.combat.parry()
                        elif event.button == 1:
                            if game.combat.skill_element:
                                if not game.combat.element_skill.cast(game.combat, game.combat.player.facing, mouse_pos):
                                    game.tell("재사용 대기 중" if game.combat.element_skill.cooldown else "먼저 대시로 잔영을 남기세요.", 1)
                            elif not game.combat.auto_echo:
                                if game.combat.trail is not None or game.combat.echo_pos is not None:
                                    game.combat.slash()
                                else:
                                    game.tell("대시로 잔영을 남긴 뒤 좌클릭하세요.", 1)
                elif event.type == pico.SDL_KEYDOWN:
                    key = event.key
                    repeat = key in pressed
                    pressed.add(key)
                    if repeat:
                        continue
                    if key == pico.SDLK_F1:
                        renderer.debug = not renderer.debug
                    if key == pico.SDLK_m:
                        audio.enabled = not audio.enabled
                        renderer.audio_enabled = audio.enabled
                    if game.inventory_open:
                        if key in (pico.SDLK_i, pico.SDLK_ESCAPE, pico.SDLK_TAB): game.toggle_inventory()
                        continue
                    if game.mode in ("hub", "forge", "map"):
                        if key == pico.SDLK_ESCAPE:
                            if game.mode == 'forge': game.close_forge()
                            else: game.mode = "hub"
                        elif key == pico.SDLK_i and game.mode == "hub": game.toggle_inventory()
                        elif key == pico.SDLK_e: game.interact()
                        elif game.mode == "forge":
                            if key in (pico.SDLK_1, pico.SDLK_2): game.choose_recipe(key - pico.SDLK_1)
                            elif key == pico.SDLK_RETURN: game.craft()
                        elif game.mode == "map":
                            if pico.SDLK_1 <= key <= pico.SDLK_4: game.map_region = key - pico.SDLK_1
                            elif key == pico.SDLK_RETURN: game.launch_region()
                        continue
                    if game.mode == "title":
                        if key == pico.SDLK_RETURN:
                            game.new_game()
                        elif key == pico.SDLK_c:
                            game.continue_game()
                        elif key == pico.SDLK_t:
                            game.start_training()
                        elif key == pico.SDLK_F2:
                            game.open_trial_select()
                        elif key == pico.SDLK_ESCAPE:
                            running = False
                    elif game.mode == "select":
                        if key in (pico.SDLK_UP, pico.SDLK_w):
                            game.selected_stage = (game.selected_stage - 1) % len(game.stages)
                        elif key in (pico.SDLK_DOWN, pico.SDLK_s):
                            game.selected_stage = (game.selected_stage + 1) % len(game.stages)
                        elif key == pico.SDLK_RETURN:
                            game.start_trial(game.selected_stage)
                        elif key == pico.SDLK_ESCAPE:
                            game.exit_to_title()
                    elif game.mode == "play":
                        if key in (pico.SDLK_TAB, pico.SDLK_i):
                            game.toggle_inventory()
                            pressed.clear()
                        elif key == pico.SDLK_ESCAPE and game.inventory_open:
                            game.toggle_inventory()
                            pressed.clear()
                        elif key == pico.SDLK_ESCAPE:
                            game.paused = not game.paused
                            pressed.clear()
                        elif game.paused:
                            if game.inventory_open:
                                if pico.SDLK_1 <= key <= pico.SDLK_5:
                                    game.select_item(key - pico.SDLK_1)
                                continue
                            if key == pico.SDLK_RETURN:
                                game.paused = False
                            elif key == pico.SDLK_q:
                                game.exit_to_title()
                            elif key == pico.SDLK_r:
                                game.retry()
                        elif key == pico.SDLK_SPACE:
                            # 같은 프레임에서 방향키와 대시를 누른 경우도 마지막 입력을 반영.
                            direction = movement(pressed, pico)
                            aim = (mouse_pos - game.combat.player.pos).normalized()
                            if aim.length():
                                game.combat.player.facing = aim
                            game.combat.dash(direction)
                        elif key in (pico.SDLK_f, pico.SDLK_j):
                            aim = mouse_pos - game.combat.player.pos
                            if aim.length():
                                game.combat.player.facing = aim.normalized()
                            game.combat.basic_attack()
                        elif key in (pico.SDLK_e, pico.SDLK_z):
                            game.pickup_element()
                        elif key == pico.SDLK_g:
                            direction = mouse_pos - game.combat.player.pos
                            game.combat.element_skill.cast(game.combat,
                                direction if direction.length() else game.combat.player.facing, mouse_pos)
                        elif key in (pico.SDLK_1, pico.SDLK_2, pico.SDLK_3, pico.SDLK_4, pico.SDLK_5):
                            game.select_item(key - pico.SDLK_1)
                    elif game.mode == "upgrade":
                        if key in (pico.SDLK_1, pico.SDLK_2, pico.SDLK_3):
                            game.choose_upgrade(key - pico.SDLK_1)
                        elif key == pico.SDLK_RETURN:
                            game.skip_upgrade()
                        elif key == pico.SDLK_q:
                            game.exit_to_title()
                    elif game.mode == "transit":
                        if key in (pico.SDLK_ESCAPE, pico.SDLK_q):
                            game.exit_to_title()
                    elif game.mode == "defeat":
                        if key in (pico.SDLK_r, pico.SDLK_RETURN):
                            game.retry()
                        elif key == pico.SDLK_q:
                            game.exit_to_title()
                    elif game.mode == "victory" and key in (pico.SDLK_RETURN, pico.SDLK_q):
                        game.exit_to_title()
            accumulator += dt
            while accumulator >= C.FIXED_DT:
                if not args.smoke_test:
                    if game.mode == "play":
                        game.combat.aim_at(mouse_pos)
                    game.update(C.FIXED_DT, movement(pressed, pico))
                accumulator -= C.FIXED_DT
            if not args.smoke_test and game.mode == "play" and not game.paused:
                game.combat.aim_at(mouse_pos)
            for event, _ in game.combat.events:
                audio.play(event)
            game.pointer_pos = mouse_pos
            renderer.consume(game.combat.events)
            renderer.draw(game)
            frames += 1
            if args.smoke_test and frames >= max(1, args.frames):
                if args.capture:
                    capture_png(args.capture, pico)
                running = False
            pico.update_canvas()
            if not args.smoke_test:
                pico.delay(0.001)
        if args.smoke_test:
            print(f"SMOKE OK: scene={args.scene}, frames={frames}")
        return 0
    finally:
        if audio:
            audio.sounds.clear()
        if renderer:
            renderer.close()
        pico.close_canvas()


def movement(keys, pico):
    return Vec(int(bool(keys & {pico.SDLK_d, pico.SDLK_RIGHT})) - int(bool(keys & {pico.SDLK_a, pico.SDLK_LEFT})),
               int(bool(keys & {pico.SDLK_w, pico.SDLK_UP})) - int(bool(keys & {pico.SDLK_s, pico.SDLK_DOWN})))


if __name__ == "__main__":
    sys.exit(main())
