"""숫자 슬롯 데이터와 드래그 영역. 아이템 실물은 인벤토리에 유지된다."""
from geometry import Vec

DEFAULT_SLOTS = ['weapon:1', None, None, None, None]
LEGACY_SLOTS = ['weapon:1', 'weapon:2', 'weapon:3', 'item:ice_stone', 'item:fire_stone']
ASSIGNABLE = {'weapon:1', 'weapon:2', 'weapon:3', 'item:ice_stone', 'item:fire_stone', 'item:healing_potion'}


def slot_at(pos):
    for i in range(5):
        if abs(pos.x - (64 + i * 58)) <= 27 and abs(pos.y - 608) <= 27:
            return i
    return None


def entry_position(i):
    return Vec(155 + i % 6 * 145, 450 - i // 6 * 120)
