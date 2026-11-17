"""새 모험의 거점·대장간·지도·인벤토리 화면과 입력 영역."""
import math
import pico2d as p
from renderer import Renderer, rect, line, circle, polygon, WHITE, INK, GOLD, CYAN, MUTED
from geometry import Vec
from campaign import HUB_FACILITIES
from campaign_data import REGIONS
from items import RECIPES, ITEMS, name
from quickbar import slot_at, entry_position


class CampaignRenderer(Renderer):
    def image(self, key, x, y, w, h):
        return self.bank.draw_cell(key, 0, 0, Vec(x, y), w, h)

    def title(self, game):
        super().title(game)
        rect(80, 120, 980, 32, INK)
        self.text("4개 지역 · 재료 탐험 · 거점 제작 · 용을 향한 복수", 92, 137, 18, GOLD)

    def floor(self, game):
        rect(0, 0, 1120, 760, INK)
        self.image(game.stage['background'], 560, 366, 1040, 516)
        self.image('door', *game.stage['exit'], 76, 88)

    def hud(self, game):
        # 기존 하트·아이템 슬롯·쿨타임·패링·반격 HUD를 그대로 사용한다.
        super().hud(game)
        rect(780, 652, 340, 108, INK, 255)
        self.text('출구 개방' if game.gate_open else '적 처치 · 전리품 회수', 790, 722, 18, CYAN)
        self.text(f"{min(game.combat.kills, game.goal)} / {game.goal}", 965, 711, 26, GOLD)
        ratio = min(1, game.combat.kills / max(1, game.goal))
        self.ui('progress_frame', 925, 681, 290, 42)
        self.ui_fill('progress_fill', ratio, 925, 681, 290, 42, 24, 372)
        if game.combat.trail:
            self.text(f"잔영 {game.combat.trail.remaining:.1f}초", 790, 660, 16, CYAN)
        self.text(f"화살 {game.bag.get('arrow_bundle', 0)}", 35, 550, 16, GOLD)

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
            if game.forge_job: self.forging(game)
            if game.forge_drop:
                pos = Vec(370, 390)
                circle(pos, 24, GOLD, 70, True)
                self.image(game.forge_drop, pos.x, pos.y + 5 + math.sin(self.visual_time * 3) * 3, 48, 48)
                self.text('E ' + name(game.forge_drop), 335, 350, 16, GOLD)
            rect(0, 670, 1120, 90, INK, 225)
            self.center('여정의 거점', 720, 32, GOLD)
            for key, pos, label in HUB_FACILITIES:
                if game.mode == 'hub' and (key != 'map' or game.toast_left <= 0):
                    self.text(label + ' · E / 클릭', pos.x - 65, pos.y - (35 if key == 'map' else 70), 18, GOLD)
            self.center('WASD 이동 · 시설 가까이에서 E 또는 클릭 · I 인벤토리', 38, 18)
            if game.mode == 'hub' and game.toast_left > 0:
                self.center(game.toast, 85, 16, GOLD)
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

    def forging(self, game):
        elapsed = 5 - game.forge_job['remaining']
        phase = (elapsed * 2) % 1
        # 손에서 망치 머리까지 연결해 캐릭터가 직접 작업하는 모양을 표시한다.
        hand = game.combat.player.pos + Vec(-12, 22)
        angle = math.radians(100 + 70 * min(1, phase / .65))
        head = hand + Vec(math.cos(angle), math.sin(angle)) * 39
        for offset in (-1, 0, 1):
            line(hand + Vec(offset, 0), head + Vec(offset, 0), (170, 119, 67))
        circle(hand, 4, (226, 194, 151), 255, True)
        side = Vec(-math.sin(angle), math.cos(angle))
        along = Vec(math.cos(angle), math.sin(angle))
        polygon([head + side * a + along * b for a,b in ((-11,-6),(11,-6),(11,6),(-11,6))], (196, 207, 215))
        line(head - side * 10, head + side * 10, GOLD)
        if phase > .65:
            hit = Vec(306, 457)
            for i in range(7):
                angle2 = i * .8 + elapsed * 2
                end = hit + Vec(math.cos(angle2), abs(math.sin(angle2))) * (9 + (phase-.65)*45)
                line(hit, end, GOLD, int(255 * (1-phase)/.35))
        rect(310, 505, 140, 9, INK)
        rect(312, 507, 136 * elapsed / 5, 5, GOLD)
        self.text(f"제작 중 {game.forge_job['remaining']:.1f}초", 310, 533, 18, GOLD)

    def forge(self, game):
        self.shade()
        rect(50, 125, 635, 525, INK)
        rect(700, 125, 370, 525, INK)
        self.text('대장간 · 원소석 제작', 90, 605, 26, GOLD)
        self.text('인벤토리', 800, 605, 26, GOLD)
        for i, recipe in enumerate(RECIPES):
            y = 475 - i * 150
            rect(80, y - 55, 175, 120, CYAN if i == game.recipe_index else MUTED, 85)
            self.image(recipe['result'], 122, y + 10, 60, 60)
            self.text(f"{i+1}. {name(recipe['result'])}", 95, y - 35, 18)
        recipe = RECIPES[game.recipe_index]
        for i, (key, count) in enumerate(recipe['cost'].items()):
            x = 350 + i * 195
            self.image(key, x, 470, 70, 70)
            self.text(name(key), x - 55, 410, 18, WHITE)
            self.text(f"{game.bag.get(key, 0)} / {count}", x - 20, 380, 20, GOLD)
        self.text('망치질 5초 후 바닥에 생성', 290, 325, 20)
        self.text('완성된 원소석은 E로 획득', 290, 290, 18, MUTED)
        rect(290, 210, 350, 65, CYAN, 80)
        self.text('제작하기 · Enter', 355, 243, 26, GOLD)
        for i, (kind, key) in enumerate(game.inventory_entries()):
            x, y = 747 + i % 4 * 86, 515 - i // 4 * 80
            self.shortcut_image(kind + ':' + key, x, y, 42)
            label = name(key) if kind == 'item' else {'1': '기본 검', '2': '냉기 검', '3': '파쇄 검'}[key]
            self.text(label, x - 36, y - 30, 14, GOLD)
            if kind == 'item': self.text(str(game.bag[key]), x + 20, y - 8, 14)
        self.center('1 / 2 제작 선택 · Esc 거점으로', 165, 18)
        if game.toast_left > 0: self.center(game.toast, 90, 16, GOLD)

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

    def shortcut_image(self, token, x, y, size=40, skill_icon=False):
        if not token: return
        kind, key = token.split(':')
        if kind == 'weapon':
            self.ui({'1': 'weapon_basic', '2': 'weapon_frost', '3': 'weapon_shatter'}[key], x, y, size, size)
        elif skill_icon and key in ('ice_stone', 'fire_stone'):
            entry = self.bank.entries.get(key.removesuffix('_stone') + '_relic_test')
            if entry:
                image = entry[0]
                # 원본의 넓은 투명 여백만 제외해 기존 스킬 그림을 또렷하게 표시한다.
                image.clip_draw(int(image.w * .31), int(image.h * .08),
                                int(image.w * .38), int(image.h * .88),
                                x, y, size, size * 1.3)
        else:
            self.image(key, x, y, size, size)

    def item_bar(self, game):
        rect(32, 575, 294, 66, INK, 235)
        target = slot_at(game.pointer_pos) if game.drag else None
        for slot, token in enumerate(game.quickslots):
            x = 64 + slot * 58
            owned = game.can_use_shortcut(token)
            selected = token is not None and token == game.active_shortcut()
            self.ui('slot_selected' if selected or slot == target else 'slot_normal', x, 608, 54, 54)
            if token:
                if owned: self.shortcut_image(token, x + 6, 605, 28, skill_icon=True)
                else: self.ui('slot_locked', x + 6, 605, 28, 28)
            # 왼쪽 위 숫자 영역과 오른쪽 아이콘 영역을 분리한다.
            rect(x - 19, 612, 10, 13, INK, 255)
            self.text(str(slot + 1), x - 18, 618, 14, GOLD if selected else WHITE)
            if token == 'item:healing_potion':
                self.text(str(game.bag.get('healing_potion', 0)), x + 9, 592, 14, GOLD)

    def inventory(self, game):
        self.shade()
        rect(70, 110, 980, 445, INK)
        self.item_bar(game)
        self.text('아이템을 집어서 1~5 슬롯에 놓으세요', 355, 608, 23, GOLD)
        self.center('보관함 / 인벤토리', 523, 26, GOLD)
        for i, (kind, key) in enumerate(game.inventory_entries()):
            pos = entry_position(i)
            x, y = pos.x, pos.y
            rect(x - 52, y - 40, 104, 90, CYAN if i == game.inventory_selected else MUTED, 80)
            self.shortcut_image(kind + ':' + key, x, y + 5, 64)
            label = name(key) + ' ' + str(game.bag[key]) if kind == 'item' else {'1': '기본 검', '2': '냉기 검', '3': '파쇄 검'}[key]
            self.text(label, x - 55, y - 58, 14, GOLD)
        self.center('I / Esc 닫기 · 슬롯끼리 드래그하면 교환 · 슬롯 우클릭은 등록 해제', 145, 16)
        self.center('장비는 클릭해 착용 · 재료는 대장간에서 제작', 115, 16, MUTED)
        if game.drag:
            pos = game.pointer_pos
            self.ui('slot_selected', pos.x, pos.y, 60, 60)
            self.shortcut_image(game.drag['token'], pos.x, pos.y, 45, skill_icon=True)
        if game.toast_left > 0: self.center(game.toast, 85, 16, GOLD)

    def release(self, game, pos, button):
        if not game.inventory_open or button != 1: return False
        if game.drag:
            source = game.drag.get('entry')
            start = game.drag.get('start', pos)
            if source is not None and start.distance(pos) < 5 and slot_at(pos) is None:
                game.drag = None
                entry = game.inventory_entries()[source]
                if entry[0] == 'item' and entry[1] not in ('ice_stone', 'fire_stone'):
                    game.use_inventory(source)
            else:
                game.drop_shortcut(slot_at(pos))
        return True

    def click(self, game, pos, button):
        if game.inventory_open:
            slot = slot_at(pos)
            if button == 3 and slot is not None:
                game.quickslots[slot] = None
                game.persist()
                return True
            if button != 1: return True
            if slot is not None:
                if game.begin_drag(game.quickslots[slot], slot): game.drag['start'] = pos
                return True
            for i, entry in enumerate(game.inventory_entries()):
                point = entry_position(i)
                if abs(pos.x - point.x) < 55 and abs(pos.y - point.y) < 55:
                    game.inventory_selected = i
                    token = entry[0] + ':' + entry[1]
                    if game.begin_drag(token):
                        game.drag.update(entry=i, start=pos)
                    elif entry[0] == 'item' and entry[1] in ('heatproof_gloves', 'fur_leather_coat', 'magic_resist_amulet'):
                        game.use_inventory(i)
                    return True
            return True
        if button != 1: return False
        if game.mode == 'hub':
            for key, point, _ in HUB_FACILITIES:
                if pos.distance(point) < 95: game.open_facility(key)
            return True
        if game.mode == 'forge':
            if 80 < pos.x < 255 and 270 < pos.y < 540: game.recipe_index = 0 if pos.y > 400 else 1
            elif 290 < pos.x < 640 and 210 < pos.y < 275: game.craft()
            return True
        if game.mode == 'map':
            if 300 < pos.y < 520: game.map_region = max(0, min(3, round((pos.x - 180) / 250)))
            elif 110 < pos.y < 235: game.launch_region()
            return True
        return False
