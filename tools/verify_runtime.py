"""SDL 창을 열어 주입한 키 이벤트로 실제 입력 처리 경로를 확인한다.

사용자 진행 저장은 사용하지 않으며, 테스트 종료 후 창을 닫는다.
"""

from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main
import pico2d as p
import sdl2
from game import Game


def run():
    instances, snapshots = [], {}

    class IsolatedGame(Game):
        def __init__(self, **kwargs):
            super().__init__(Path(__file__).resolve().parents[1] / ".cache/runtime-check.json")
            instances.append(self)

    schedule = {
        0: [(p.SDL_KEYDOWN, p.SDLK_RETURN)],
        1: [(p.SDL_KEYUP, p.SDLK_RETURN), (p.SDL_KEYDOWN, p.SDLK_w)],
        2: [(p.SDL_KEYDOWN, p.SDLK_SPACE)],
        3: [(p.SDL_KEYUP, p.SDLK_SPACE)],
        16: [(p.SDL_KEYUP, p.SDLK_w)],
        20: [(p.SDL_KEYDOWN, p.SDLK_j)],
        21: [(p.SDL_KEYUP, p.SDLK_j)],
        30: [(p.SDL_KEYDOWN, p.SDLK_ESCAPE)],
        31: [(p.SDL_KEYUP, p.SDLK_ESCAPE)],
        45: [(p.SDL_KEYDOWN, p.SDLK_ESCAPE)],
        46: [(p.SDL_KEYUP, p.SDLK_ESCAPE)],
        65: [(p.SDL_QUIT, None)],
    }
    frame, clock = 0, 0.0

    def events():
        nonlocal frame
        if instances:
            game = instances[0]
            snapshots[frame] = (game.combat.elapsed, game.combat.player.pos,
                                game.combat.trail is not None, len(game.combat.slashes), game.paused)
        # 운영체제의 창 이벤트는 비우되 키 입력은 테스트 스케줄로 전달한다.
        original_events()
        result = [SimpleNamespace(type=kind, key=key) for kind, key in schedule.get(frame, [])]
        frame += 1
        return result

    def now():
        nonlocal clock
        clock += 1 / 60
        return clock

    original_events, original_game = p.get_events, main.Game
    original_clock, original_focus = main.time.perf_counter, sdl2.SDL_GetWindowFlags
    try:
        p.get_events, main.Game = events, IsolatedGame
        main.time.perf_counter = now
        sdl2.SDL_GetWindowFlags = lambda window: sdl2.SDL_WINDOW_INPUT_FOCUS
        assert main.main(["--mute"]) == 0
    finally:
        p.get_events, main.Game = original_events, original_game
        main.time.perf_counter, sdl2.SDL_GetWindowFlags = original_clock, original_focus
    assert snapshots[15][2], "Space 입력으로 잔영이 생성되지 않았습니다."
    assert snapshots[25][3] > 0, "J 입력으로 참격 연출이 생성되지 않았습니다."
    assert snapshots[31][4] and snapshots[44][4], "일시정지에 실패했습니다."
    assert snapshots[31][0] == snapshots[44][0], "일시정지 중 게임 시간이 진행했습니다."
    assert snapshots[47][0] > snapshots[45][0], "계속하기 후 게임 시간이 진행하지 않았습니다."
    assert snapshots[15][1].y > snapshots[1][1].y, "이동/대시로 좌표가 변하지 않았습니다."
    print("RUNTIME OK: Enter / 이동 / Space / J / 일시정지 / 계속하기 / 종료")


if __name__ == "__main__":
    run()
