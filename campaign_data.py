"""15개 라운드와 필수 재료 배치. 좌표는 게임 좌표(왼쪽 아래 원점)."""
from geometry import Arena, Rect, Vec

REGIONS = (
    {"name": "마족화된 숲", "start": 0, "end": 2, "icon": "map_forest", "pos": (235, 410)},
    {"name": "불타는 요새", "start": 3, "end": 6, "icon": "map_burned_fort", "pos": (520, 365)},
    {"name": "혹한의 땅", "start": 7, "end": 10, "icon": "map_frozen_land", "pos": (785, 470)},
    {"name": "용의 성", "start": 11, "end": 14, "icon": "map_dragon_castle", "pos": (990, 490)},
)


def chest(x, y, loot, required=False, jewel=False):
    return {"pos": [x, y], "loot": loot, "required": required, "jewel": jewel}


def stage(sid, title, region, background, enemies=(), boss=None, chests=(), **extra):
    return {"id": sid, "title": title, "region": region, "theme": ("forest", "fortress", "frozen", "sanctuary")[region],
            "background": background, "start": [560, 180], "exit": [560, 585], "walls": [],
            "waves": [[0, list(enemies)]] if enemies else [], "boss": boss, "chests": list(chests),
            "goal": len(enemies) + bool(boss), "tip": "F 검격 · Space 대시 · 좌클릭 잔영 스킬 · 우클릭 패링 · E 상호작용 · I 인벤토리", **extra}


STAGES = [
    stage("1-1", "숲의 입구", 0, "forest", [("wolf", 350, 470), ("wolf", 740, 470), ("wolf", 560, 520)],
          chests=[chest(270, 290, {"healing_potion": 1})],
          story="부모를 죽인 용의 흔적은 이 숲을 지나 성으로 이어진다."),
    stage("1-2", "뒤틀린 숲길", 0, "forest", [("wolf", 330, 460), ("boar", 770, 470), ("wolf", 590, 520)],
          chests=[chest(840, 260, {"healing_potion": 1})], walls=[[260, 330, 75, 55], [760, 340, 85, 55]],
          story="마족화된 짐승들을 지나면 용이 불태운 요새가 나온다."),
    stage("1-3", "숲의 길목", 0, "forest", boss="boar_lord", boss_pos=[560, 450],
          boss_loot={"fortress_key": 1}, story="길목의 거대한 멧돼지에게서 요새의 열쇠를 되찾아라."),
    stage("2-1", "불타는 외곽", 1, "fortress_burned_outer",
          [("mage", 350, 480), ("wolf", 730, 440), ("sentinel", 850, 490)],
          chests=[chest(270, 250, {"ember_fragment": 1, "arrow_bundle": 24}, True)],
          walls=[[100, 445, 180, 65], [800, 130, 200, 65]],
          story="성벽에는 아직 용의 불씨가 남아 있다. 상자에서 불씨와 화살을 모으자."),
    stage("2-2", "무너진 병영", 1, "fortress_burned_barracks",
          [("mage", 560, 490), ("sentinel", 820, 365), ("wolf", 300, 365)],
          chests=[chest(360, 380, {"ember_fragment": 1, "arrow_bundle": 24}, True),
                  chest(820, 220, {"arrow_bundle": 18, "healing_potion": 1}, jewel=True)],
          walls=[[240, 435, 20, 145], [240, 435, 120, 20], [765, 435, 20, 145], [765, 435, 120, 20],
                 [240, 130, 20, 160], [240, 290, 120, 20], [765, 130, 20, 160], [765, 290, 120, 20]],
          story="병영의 옆길에는 남겨진 보석함이 있다."),
    stage("2-3", "잿빛 안뜰", 1, "fortress_burned_courtyard",
          [("mage", 330, 490), ("sentinel", 730, 470), ("mage", 880, 350), ("wolf", 450, 450)],
          chests=[chest(300, 250, {"ember_fragment": 1, "heatproof_gloves": 1}, True)],
          hazards="fire", walls=[[460, 360, 65, 55], [725, 300, 60, 50]],
          story="지킴이에게 닿기 전에 내열 장갑을 확보하고 I에서 착용하자."),
    stage("2-4", "불타는 지킴이", 1, "fortress_burned_boss", boss="fire_guardian", boss_pos=[560, 455],
          boss_loot={"flame_core": 1},
          story="용의 화염에 잠식된 지킴이. 돌진을 패링하고 핵을 회수하자."),
    stage("3-1", "혹한의 입구", 2, "frozen_land_entrance",
          [("wolf", 390, 450), ("sentinel", 750, 470)],
          chests=[chest(360, 260, {"fur_leather_coat": 1, "arrow_bundle": 24}, True)],
          frozen_gate=[560, 455], story="불의 돌로 잔영 불화살을 발사해 얼어붙은 문을 녹이자."),
    stage("3-2", "얼음 계곡", 2, "frozen_land_valley",
          [("wolf", 400, 355), ("mage", 820, 420), ("sentinel", 675, 325)],
          start=[120, 470], exit=[990, 470],
          chests=[chest(680, 300, {"ice_fragment": 2, "arrow_bundle": 24}, True)],
          walls=[[425, 445, 300, 170], [405, 110, 210, 95]],
          story="얼음 절벽을 돌아 계곡의 결정 조각을 모으자."),
    stage("3-3", "눈보라의 길", 2, "frozen_land_blizzard",
          [("wolf", 320, 390), ("mage", 680, 445), ("sentinel", 850, 340)],
          start=[110, 410], exit=[990, 355],
          chests=[chest(520, 470, {"ice_fragment": 1, "healing_potion": 1}, True)],
          corridor=[[90, 410], [315, 390], [500, 480], [690, 445], [850, 340], [1020, 355]],
          corridor_width=90, story="모피 외투는 눈보라 속 이동 방해를 막아준다."),
    stage("3-4", "얼음 수호수", 2, "frozen_land_boss", boss="ice_guardian", boss_pos=[560, 455],
          boss_loot={"frost_core": 1}, story="불화살로 얼음 갑주를 깨고 수호수의 빙결핵을 회수하자."),
    stage("4-1", "용의 성 외벽", 3, "fortress",
          [("mage", 320, 480), ("sentinel", 780, 470), ("wolf", 540, 520)],
          chests=[chest(300, 260, {"magic_resist_amulet": 1, "arrow_bundle": 24}, True)],
          walls=[[300, 350, 85, 55], [750, 350, 85, 55]],
          story="용의 성문을 넘었다. 원소와 장비를 점검하자."),
    stage("4-2", "마법 회랑", 3, "sanctuary",
          [("mage", 310, 470), ("sentinel", 790, 470), ("mage", 560, 530), ("wolf", 430, 410)],
          chests=[chest(280, 260, {"healing_potion": 2, "arrow_bundle": 24})],
          hazards="magic", walls=[[410, 360, 65, 70], [645, 360, 65, 70]],
          story="얼음으로 적을 묶고 불화살로 멀리 있는 마법사를 공격하자."),
    stage("4-3", "성문 수호기사", 3, "fortress", boss="knight", boss_pos=[560, 460],
          boss_loot={"throne_sigil": 1, "arrow_bundle": 36, "healing_potion": 2},
          story="돌진 패링과 배후 검격으로 왕좌의 인장을 얻자."),
    stage("4-4", "드래곤의 왕좌", 3, "sanctuary", boss="final_dragon", boss_pos=[560, 465],
          boss_loot={"dragon_core": 1}, hazards="magic",
          story="부모를 죽인 용이 기다린다. 방어막의 속성과 돌진의 빈틈을 노려라."),
]


class CampaignArena(Arena):
    def __init__(self, data):
        super().__init__([Rect(*wall) for wall in data.get("walls", [])])
        self.route = [Vec(*p) for p in data.get("corridor", [])]
        self.half_width = data.get("corridor_width", 90)

    def valid(self, pos, radius):
        if not super().valid(pos, radius):
            return False
        if not self.route:
            return True
        for a, b in zip(self.route, self.route[1:]):
            ab, ap = b - a, pos - a
            length2 = ab.x * ab.x + ab.y * ab.y
            t = max(0, min(1, (ap.x * ab.x + ap.y * ab.y) / length2))
            if pos.distance(a + ab * t) <= self.half_width - radius:
                return True
        return False
