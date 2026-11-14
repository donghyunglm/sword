"""잔영 참격으로 작동하거나 파괴하는 라운드 목표물."""

from dataclasses import dataclass
from geometry import Vec


@dataclass
class Device:
    uid: int
    kind: str
    pos: Vec
    hp: int = 1
    radius: float = 22
    link: str = ""
    flash: float = 0

    @classmethod
    def make(cls, uid, kind, pos, link=""):
        return cls(uid, kind, pos, 2 if kind == "crystal" else 1,
                   27 if kind == "crystal" else 21, link)

    def receive_slash(self):
        self.hp -= 1
        self.flash = 0.2
        return True
