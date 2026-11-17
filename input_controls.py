"""SDL 창 좌표를 게임 좌표로 변환하는 단일 경로."""
from ctypes import byref, c_int
import config as C
from geometry import Vec


def window_to_game(x, y, width=C.WIDTH, height=C.HEIGHT):
    return Vec(x * C.WIDTH / max(1, width),
               C.HEIGHT - 1 - y * C.HEIGHT / max(1, height))


def mouse_position(window):
    from sdl2 import SDL_GetMouseState, SDL_GetWindowSize
    x, y, width, height = c_int(), c_int(), c_int(), c_int()
    SDL_GetMouseState(byref(x), byref(y))
    SDL_GetWindowSize(window, byref(width), byref(height))
    return window_to_game(x.value, y.value, width.value, height.value)
