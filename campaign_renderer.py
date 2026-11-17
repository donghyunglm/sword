"""새 모험의 거점·대장간·지도·인벤토리 화면과 입력 영역."""
import pico2d as p
from renderer import Renderer, rect, WHITE, INK, GOLD, CYAN, MUTED
from geometry import Vec
from campaign import HUB_FACILITIES
from campaign_data import REGIONS
from items import RECIPES, ITEMS, name


class CampaignRenderer(Renderer):
    def image(self, key, x, y, w, h):
        return self.bank.draw_cell(key, 0, 0, Vec(x, y), w, h)

    def title(self, game):
        super().title(game)
        rect(80, 120, 980, 32, INK)
        self.text("4개 지역 · 재료 탐험 · 거점 합성 · 용을 향한 복수", 92, 137, 18, GOLD)

    def floor(self, game):
        rect(0, 0, 1120, 760, INK)
        self.image(game.stage['background'], 560, 366, 1040, 516)
        self.image('door', *game.stage['exit'], 76, 88)

    def hud(self, game):
        rect(0, 650, 1120, 110, INK)
        self.text(f"HP {game.combat.player.hp}/{6}   {game.stage['id']}  {game.stage['title']}", 35, 716, 26, GOLD)
        self.text('출구 개방' if game.gate_open else '적 처치 · 상자와 전리품 회수', 650, 715, 20, CYAN)
        rect(0, 0, 1120, 95, INK)
        self.text('Space 대시   좌클릭 잔영 발동   우클릭 패링   F 평타   E 획득   I 인벤토리', 40, 63, 18)
        self.text(f"장착: {game.combat.element or '기본 검'}    화살: {game.bag.get('arrow_bundle', 0)}    휠: 장착 변경", 40, 30, 18, CYAN)
        if game.toast_left > 0: self.center(game.toast, 125, 16, GOLD)

    def draw(self, game):
        if game.mode in ('title', 'select'):
            return super().draw(game)
        if game.mode in ('hub', 'forge', 'map'):
            p.clear_canvas()
            self.image('hub_room', 560, 380, 1120, 760)
            self.image('hub_forge', 265, 465, 170, 160)
            self.image('hub_storage_closed', 850, 355, 120, 105)
            self.actor('player', game.combat.player.pos, game.combat.player.facing,
                       'walk' if game.combat.player.moving else 'idle')
            rect(0, 670, 1120, 90, INK, 225)
            self.center('여정의 거점', 720, 32, GOLD)
            for key, pos, label in HUB_FACILITIES:
                self.text(label + ' · E / 클릭', pos.x - 65, pos.y - (35 if key == 'map' else 70), 18, GOLD)
            self.center('WASD 이동 · 시설 가까이에서 E 또는 클릭 · I 인벤토리', 38, 18)
            if game.mode == 'forge': self.forge(game)
            if game.mode == 'map': self.world_map(game)
        elif game.mode == 'transit':
            self.floor(game)
            self.center('다음 길로 · W를 눌러 전진', 390, 32, GOLD)
        else:
            self.floor(game)
            for box in game.chests:
                key = ('jewel' if box.get('jewel') else 'supply') + '_chest_'
                self.image(key + ('open' if box['id'] in game.opened else 'closed'), *box['pos'], 70, 65)
            for drop in game.drops:
                self.image(next(iter(drop['loot']), 'dragon_core'), drop['pos'].x, drop['pos'].y, 65, 65)
            if game.frozen_gate:
                self.image('thawed_gate' if game.frozen_gate.opened else 'frozen_gate', game.frozen_gate.pos.x, game.frozen_gate.pos.y, 140, 100)
            self.scene(game)
            self.hud(game)
            if game.mode == 'victory':
                self.shade()
                self.center('마룡 격파 · 복수의 여정 완료', 420, 32, GOLD)
                self.center('Enter 타이틀로', 335, 23)
            elif game.mode == 'defeat': self.menu(game)
            elif game.paused and not game.inventory_open:
                self.shade()
                self.center('일시 정지 · Enter 계속 · R 재도전 · Q 타이틀', 380, 23)
        if game.inventory_open: self.inventory(game)

    def forge(self, game):
        self.shade()
        rect(65, 125, 990, 525, INK)
        self.center('대장간 · 모은 재료로 원소석 합성', 610, 32, GOLD)
        for i, recipe in enumerate(RECIPES):
            y = 475 - i * 160
            rect(100, y - 60, 260, 125, CYAN if i == game.recipe_index else MUTED, 100)
            self.image(recipe['result'], 155, y, 70, 70)
            self.text(f"{i+1}. {name(recipe['result'])}", 205, y, 23)
        recipe = RECIPES[game.recipe_index]
        for i, (key, count) in enumerate(recipe['cost'].items()):
            self.image(key, 460 + i * 235, 460, 85, 85)
            self.text(f"{name(key)} {game.bag.get(key, 0)}/{count}", 400 + i * 235, 390, 20, GOLD)
        self.text('잔영에서 원거리 공격을 발사합니다.', 410, 310, 20)
        rect(425, 200, 390, 65, CYAN, 80)
        self.text('합성하기 · Enter', 500, 236, 26, GOLD)
        self.center('1 / 2 선택 · Esc 거점으로', 165, 18)
        if game.toast_left > 0: self.center(game.toast, 90, 18, GOLD)

    def world_map(self, game):
        self.shade()
        self.image('world_map', 560, 400, 1040, 610)
        for i, region in enumerate(REGIONS):
            x = 180 + i * 250
            self.image(region['icon'], x, 420, 150, 150)
            self.text(f"{i+1}. {region['name']}", x - 90, 305, 20, CYAN if i == game.map_region else WHITE)
        rect(80, 110, 960, 125, INK, 240)
        self.center(game.region_reason(game.map_region) or '출발 가능 · Enter / 아래 버튼 클릭', 205, 23, GOLD)
        self.center('출발하기', 155, 26, CYAN)
        self.center('1~4 지역 선택 · Esc 거점으로', 65, 18)

    def inventory(self, game):
        self.shade()
        rect(70, 115, 980, 535, INK)
        self.center('보관함 / 인벤토리 · 클릭으로 장착 또는 사용', 610, 26, GOLD)
        for i, (kind, key) in enumerate(game.inventory_entries()):
            x, y = 155 + (i % 6) * 145, 505 - (i // 6) * 120
            rect(x - 52, y - 40, 104, 90, CYAN if i == game.inventory_selected else MUTED, 80)
            if kind == 'item':
                self.image(key, x, y + 5, 64, 64)
                label = name(key) + ' ' + str(game.bag[key])
            else:
                self.ui('weapon_' + key, x, y, 60, 60)
                label = '검 ' + key
            self.text(label, x - 55, y - 58, 14, GOLD)
        self.center('I / Esc 닫기 · 장비는 다시 클릭하면 해제', 145, 18)

    def click(self, game, pos, button):
        if button != 1: return False
        if game.inventory_open:
            for i in range(len(game.inventory_entries())):
                x, y = 155 + i % 6 * 145, 505 - i // 6 * 120
                if abs(pos.x - x) < 55 and abs(pos.y - y) < 55: game.use_inventory(i)
            return True
        if game.mode == 'hub':
            for key, point, _ in HUB_FACILITIES:
                if pos.distance(point) < 95: game.open_facility(key)
            return True
        if game.mode == 'forge':
            if 100 < pos.x < 360: game.recipe_index = 0 if pos.y > 395 else 1
            elif 425 < pos.x < 815 and 200 < pos.y < 265: game.craft()
            return True
        if game.mode == 'map':
            if 300 < pos.y < 520: game.map_region = max(0, min(3, round((pos.x - 180) / 250)))
            elif 110 < pos.y < 235: game.launch_region()
            return True
        return False
