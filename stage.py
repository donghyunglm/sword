import json
from pathlib import Path
from geometry import Arena, Rect, Vec

ROOT = Path(__file__).resolve().parent


def load_stages():
    stages = json.loads((ROOT / "data" / "stages.json").read_text(encoding="utf-8"))
    for stage in stages:
        count = sum(len(wave[1]) for wave in stage["waves"])
        if stage.get("boss"):
            count += 1
        count += len(stage.get("devices", []))
        if stage["goal"] != count:
            raise ValueError(f"{stage['id']}: 처치 목표와 생성 수가 다릅니다.")
        arena = make_arena(stage)
        if not arena.valid(Vec(*stage["start"]), 14):
            raise ValueError("플레이어 시작 위치가 벽과 겹칩니다.")
        for _, enemies in stage["waves"]:
            for kind, x, y in enemies:
                if not arena.valid(Vec(x, y), 20 if kind in ("boar", "sentinel") else 16):
                    raise ValueError(f"{stage['id']}: 적 생성 위치가 유효하지 않습니다.")
        for device in stage.get("devices", []):
            kind, x, y = device[:3]
            if not arena.valid(Vec(x, y), 27 if kind == "crystal" else 21):
                raise ValueError(f"{stage['id']}: 장치 위치가 유효하지 않습니다.")
    return stages


def make_arena(stage):
    return Arena([Rect(*wall) for wall in stage["walls"]])
