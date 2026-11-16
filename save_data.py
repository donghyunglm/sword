"""라운드 경계에서만 저장. 원본 라운드 설정을 수정하지 않는다."""

import json
import os
from pathlib import Path
import config as C

DEFAULT_PATH = Path(__file__).resolve().parent / "saves" / "progress.json"


def validate(data, stage_count=None):
    if stage_count is None:
        from stage import load_stages
        stage_count = len(load_stages())
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("지원하지 않는 저장 형식입니다.")
    index = data.get("stage")
    if type(index) is not int or not 0 <= index < stage_count:
        raise ValueError("라운드 번호가 잘못되었습니다.")
    upgrades = data.get("upgrades")
    if not isinstance(upgrades, dict) or set(upgrades) != set(C.UPGRADES):
        raise ValueError("강화 정보가 잘못되었습니다.")
    if any(type(v) is not int or not 0 <= v <= C.UPGRADE_LIMIT for v in upgrades.values()):
        raise ValueError("강화 단계가 잘못되었습니다.")
    if sum(upgrades.values()) > stage_count - 1:
        raise ValueError("강화 횟수가 잘못되었습니다.")
    if data.get("phase") not in ("play", "upgrade", "victory"):
        raise ValueError("진행 상태가 잘못되었습니다.")
    weapon = data.get("weapon", 1)
    if type(weapon) is not int or weapon not in (1, 2, 3):
        raise ValueError("무기 정보가 잘못되었습니다.")
    if (weapon == 2 and index < 8) or (weapon == 3 and index < 10):
        raise ValueError("획득하지 않은 무기가 저장되었습니다.")
    if type(data.get("hp")) is not int or not 1 <= data["hp"] <= C.MAX_HP:
        raise ValueError("체력 정보가 잘못되었습니다.")
    cleared = data.get("cleared")
    if not isinstance(cleared, list) or any(type(i) is not int or not 0 <= i < stage_count for i in cleared):
        raise ValueError("보상 정보가 잘못되었습니다.")
    if len(cleared) != len(set(cleared)):
        raise ValueError("보상이 중복되었습니다.")
    if any(i > index for i in cleared):
        raise ValueError("진행 순서가 잘못되었습니다.")
    if data["phase"] == "upgrade" and (index not in cleared or index >= stage_count - 1):
        raise ValueError("강화 화면 상태가 잘못되었습니다.")
    if data["phase"] == "victory" and index != stage_count - 1:
        raise ValueError("클리어 상태가 잘못되었습니다.")
    return data


def read_save(path=DEFAULT_PATH):
    path = Path(path)
    if not path.exists():
        return None, ""
    try:
        return validate(json.loads(path.read_text(encoding="utf-8"))), ""
    except (OSError, ValueError, TypeError):
        # 손상된 파일은 자동 삭제하지 않고 보존한다.
        return None, "저장을 읽지 못했습니다. 기존 파일은 보존됩니다. 새 모험을 시작할 수 있습니다."


def write_save(data, path=DEFAULT_PATH):
    validate(data)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)
