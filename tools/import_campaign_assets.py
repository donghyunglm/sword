"""사용자가 제공한 원본 PNG를 프로젝트 안으로 복사하고 로더에 등록한다."""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESKTOP = Path("C:/Users/tgc05/OneDrive/Desktop")
GROUPS = ("1_hub", "2_forge_ui", "3_inventory_ui", "4_items", "5_chests_gates",
          "6_combat_vfx", "7_burned_fortress", "8_frozen_land", "10_world_map")


def main():
    manifest_path = ROOT / "assets/sprites.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    count = 0
    for group in GROUPS:
        for source in (DESKTOP / group).glob("*.png"):
            target = ROOT / "assets/campaign" / group / source.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            entry = {"file": target.relative_to(ROOT / "assets").as_posix()}
            if source.stem.startswith(("fortress_burned_", "frozen_land_")):
                entry.update(draw_width=1040, draw_height=516, offset_y=0)
            manifest[source.stem] = entry
            count += 1
    source_dir = Path("C:/Users/tgc05/Downloads/boss_animations (1)")
    for boss in ("fire_guardian", "ice_guardian"):
        for state, frames, fps in (("idle", 4, 5), ("tell", 3, 4), ("charge", 4, 12),
                                   ("stun", 2, 4), ("death", 4, 7)):
            name = f"{boss}_{state}"
            target = ROOT / "assets/campaign/bosses" / (name + ".png")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_dir / target.name, target)
            manifest[name] = {"file": target.relative_to(ROOT / "assets").as_posix(),
                              "frame_width": 256, "frame_height": 256, "frames": frames,
                              "fps": fps, "draw_width": 94, "draw_height": 94, "offset_y": 15,
                              "direction_rows": {"down": 0, "left": 1, "right": 2, "up": 3},
                              "loop": state not in ("tell", "death")}
            count += 1
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Imported {count} assets")


if __name__ == "__main__":
    main()
