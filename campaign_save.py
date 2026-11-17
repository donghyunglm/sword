"""새 이야기 전용 저장. 구버전 progress.json은 수정하지 않는다."""
import json
import os
from pathlib import Path
from items import ITEMS, GEAR
from quickbar import ASSIGNABLE

DEFAULT_PATH = Path(__file__).resolve().parent / "saves/campaign_progress.json"


def validate(data):
    if not isinstance(data, dict) or data.get("version") != 2:
        raise ValueError("지원하지 않는 새 모험 저장입니다.")
    for key, maximum in (("stage", 14), ("next_stage", 15), ("hp", 6), ("weapon", 3)):
        value = data.get(key)
        if type(value) is not int or not 0 <= value <= maximum or (key in ("hp", "weapon") and value < 1):
            raise ValueError("진행 정보가 올바르지 않습니다.")
    if data.get("phase") not in ("hub", "play", "transit", "victory"):
        raise ValueError("장면 정보가 올바르지 않습니다.")
    bag = data.get("bag")
    products = ('fire_stone', 'ice_stone')
    job = data.get('forge_job')
    if job is not None and (not isinstance(job, dict) or job.get('result') not in products
                            or type(job.get('remaining')) not in (int, float)
                            or not 0 <= job['remaining'] <= 5):
        raise ValueError("제작 정보가 올바르지 않습니다.")
    if data.get('forge_drop') is not None and data['forge_drop'] not in products:
        raise ValueError("제작 전리품 정보가 올바르지 않습니다.")
    slots = data.get('quickslots')
    if slots is not None and (not isinstance(slots, list) or len(slots) != 5
                              or any(token is not None and token not in ASSIGNABLE for token in slots)
                              or len([s for s in slots if s]) != len(set(s for s in slots if s))):
        raise ValueError("숫자 슬롯 정보가 올바르지 않습니다.")
    if not isinstance(bag, dict) or any(k not in ITEMS or type(v) is not int or not 0 <= v <= 9999 for k, v in bag.items()):
        raise ValueError("소지품 정보가 올바르지 않습니다.")
    equipped = data.get("equipped", [])
    if not isinstance(equipped, list) or len(equipped) != len(set(equipped)) or any(k not in GEAR or not bag.get(k) for k in equipped):
        raise ValueError("장착 정보가 올바르지 않습니다.")
    element = data.get("element")
    if element not in (None, "ice", "fire") or (element and not bag.get(element + "_stone")):
        raise ValueError("원소 정보가 올바르지 않습니다.")
    for key in ("collected", "opened"):
        values = data.get(key)
        if not isinstance(values, list) or len(values) != len(set(values)) or any(not isinstance(v, str) for v in values):
            raise ValueError("획득 기록이 올바르지 않습니다.")
    cleared = data.get("cleared")
    if not isinstance(cleared, list) or len(cleared) != len(set(cleared)) or any(type(i) is not int or not 0 <= i < 15 for i in cleared):
        raise ValueError("라운드 기록이 올바르지 않습니다.")
    return data


def read(path=DEFAULT_PATH):
    try:
        return validate(json.loads(Path(path).read_text(encoding="utf-8"))), ""
    except FileNotFoundError:
        return None, ""
    except (OSError, ValueError, TypeError):
        return None, "진행 기록을 읽지 못했습니다. 원본 파일은 보존됩니다."


def write(data, path=DEFAULT_PATH):
    validate(data)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)
