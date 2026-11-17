"""새 모험의 재료·장비·합성 정의. 수량은 PNG에 그려 넣지 않는다."""
ITEMS = {
    "healing_potion": ("회복약", "체력을 2 회복합니다.", "소모품"),
    "arrow_bundle": ("화살", "발사한 불화살 수만큼 소모됩니다.", "소모품"),
    "ember_fragment": ("불씨 조각", "불의 돌을 만드는 재료입니다.", "재료"),
    "flame_core": ("화염의 핵", "화염 지킴이가 남긴 핵입니다.", "재료"),
    "fire_stone": ("불의 돌", "잔영이 커서 방향으로 불화살을 발사합니다.", "원소"),
    "ice_fragment": ("얼음 결정 조각", "얼음의 돌을 만드는 재료입니다.", "재료"),
    "frost_core": ("빙결의 핵", "얼음 수호수가 남긴 핵입니다.", "재료"),
    "ice_stone": ("얼음의 돌", "잔영이 적을 얼리는 결정을 발사합니다.", "원소"),
    "heatproof_gloves": ("내열 장갑", "화염 지대의 피해를 줄입니다.", "장비"),
    "fur_leather_coat": ("모피 가죽 외투", "혹한 지역의 이동 방해를 막습니다.", "장비"),
    "magic_resist_amulet": ("마법 저항 부적", "마법 탄환의 피해를 줄입니다.", "장비"),
    "fortress_key": ("요새 열쇠", "불타는 요새로 들어가는 열쇠입니다.", "열쇠"),
    "throne_sigil": ("왕좌의 인장", "드래곤의 왕좌로 가는 문을 엽니다.", "열쇠"),
    "dragon_core": ("드래곤의 핵", "복수의 여정 끝에 남은 마법핵입니다.", "전리품"),
}
RECIPES = (
    {"result": "fire_stone", "element": "fire", "cost": {"ember_fragment": 3, "flame_core": 1}},
    {"result": "ice_stone", "element": "ice", "cost": {"ice_fragment": 3, "frost_core": 1}},
)
GEAR = ("heatproof_gloves", "fur_leather_coat", "magic_resist_amulet")


def name(key):
    return ITEMS[key][0]
