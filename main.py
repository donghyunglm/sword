"""잔영의 검 진입점. VS Code에서 이 파일을 F5로 실행한다."""

import argparse
from pathlib import Path
import sys
import time

import config as C
from geometry import Vec
from game import Game


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
    if name == "title":
        return
    if name == "select":
        game.open_trial_select()
        game.selected_stage = 14
        return
    game.training = False
    scene_stages = {"boss": 4, "fortress": 5, "devices": 6, "knight": 9,
                    "sanctuary": 10, "dragon": 14, "dragon-attack": 14}
    game.load_stage(scene_stages.get(name, 0), persist=False)
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
    if name == "fortress":
        game.combat.spawn("mage", Vec(360, 470))
        game.combat.spawn("sentinel", Vec(770, 470))
    if name == "dragon-attack":
        dragon = game.combat.enemies[0]
        dragon.attack, dragon.state, dragon.timer = "breath", "attack", 0.3
        dragon.direction = Vec(0, -1)
        dragon.breath_reach = 210
        game.combat.events.append(("boss_breath", dragon.pos))
    if name in ("upgrade", "defeat", "victory"):
        game.mode = name


def main(argv=None):
    parser = argparse.ArgumentParser(description="잔영의 검 / Python + pico2d")
    parser.add_argument("--training", action="store_true", help="저장하지 않는 연습장으로 시작")
    parser.add_argument("--smoke-test", action="store_true", help="정해진 프레임 후 종료하는 렌더 검사")
    parser.add_argument("--scene", choices=("title", "select", "play", "boss", "fortress", "devices", "knight",
                                            "sanctuary", "dragon", "dragon-attack", "upgrade", "defeat", "victory"), default="play")
    parser.add_argument("--frames", type=int, default=120)
    parser.add_argument("--capture", type=Path)
    parser.add_argument("--mute", action="store_true")
    args = parser.parse_args(argv)
    try:
        import pico2d as pico
    except ImportError:
        print("pico2d가 없습니다. 선택한 Python에서 python -m pip install -r requirements.txt 를 실행하세요.")
        return 1
    from renderer import Renderer
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
        game = Game(save_path=Path(__file__).resolve().parent / (".cache/smoke-save.json" if args.smoke_test else "saves/progress.json"))
        if args.smoke_test:
            prepare_scene(game, args.scene)
        elif args.training:
            game.start_training()
        pressed = set()
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
            renderer.tick(dt if not game.paused else 0)
            for event in pico.get_events():
                if event.type == pico.SDL_QUIT:
                    running = False
                elif event.type == pico.SDL_KEYUP:
                    pressed.discard(event.key)
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
                        if key == pico.SDLK_ESCAPE:
                            game.paused = not game.paused
                            pressed.clear()
                        elif game.paused:
                            if key == pico.SDLK_RETURN:
                                game.paused = False
                            elif key == pico.SDLK_q:
                                game.exit_to_title()
                            elif key == pico.SDLK_r:
                                game.retry()
                        elif key == pico.SDLK_SPACE:
                            # 같은 프레임에서 방향키와 대시를 누른 경우도 마지막 입력을 반영.
                            direction = movement(pressed, pico)
                            if direction.length():
                                game.combat.player.facing = direction.normalized()
                            game.combat.dash()
                        elif key == pico.SDLK_j:
                            game.combat.slash()
                    elif game.mode == "upgrade":
                        if key in (pico.SDLK_1, pico.SDLK_2, pico.SDLK_3):
                            game.choose_upgrade(key - pico.SDLK_1)
                        elif key == pico.SDLK_RETURN:
                            game.skip_upgrade()
                        elif key == pico.SDLK_q:
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
                    game.update(C.FIXED_DT, movement(pressed, pico))
                accumulator -= C.FIXED_DT
            for event, _ in game.combat.events:
                audio.play(event)
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
