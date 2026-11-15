"""프로토타입용 짧은 합성 효과음. 오디오 장치가 없으면 조용히 비활성화."""

from array import array
import math
from pathlib import Path
import wave


class Audio:
    def __init__(self, pico, enabled=True):
        self.enabled = enabled
        self.sounds = {}
        directory = Path(__file__).resolve().parent / ".cache" / "sounds"
        tones = {"dash": (520, 220, 0.08), "slash": (850, 190, 0.10),
                 "hit": (240, 80, 0.07), "hurt": (130, 60, 0.18),
                 "recharge": (540, 1100, 0.16), "open": (440, 880, 0.35),
                 "boss_impact": (110, 42, 0.24), "boss_breath": (180, 80, 0.32),
                 "boss_hit": (360, 95, 0.2)}
        if not enabled:
            return
        try:
            directory.mkdir(parents=True, exist_ok=True)
            for name, (start, end, length) in tones.items():
                path = directory / (name + ".wav")
                if not path.exists():
                    samples = array("h")
                    phase, rate = 0.0, 22050
                    count = int(rate * length)
                    for i in range(count):
                        phase += math.tau * (start + (end - start) * i / count) / rate
                        envelope = min(1, i / 70) * (1 - i / count) ** 1.5
                        samples.append(int(math.sin(phase) * 4200 * envelope))
                    with wave.open(str(path), "wb") as wav:
                        wav.setnchannels(1)
                        wav.setsampwidth(2)
                        wav.setframerate(rate)
                        wav.writeframes(samples.tobytes())
                self.sounds[name] = pico.load_wav(str(path))
                self.sounds[name].set_volume(32)
        except (OSError, ValueError):
            self.enabled = False

    def play(self, name):
        if self.enabled and name in self.sounds:
            self.sounds[name].play()
