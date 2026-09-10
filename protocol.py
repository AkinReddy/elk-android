"""
protocol.py — сборка пакетов для ELK-BLEDDM / ELK-BLEDOM.
Логика идентична elk_led.py, вынесена отдельно, чтобы использовать
и в CLI-скрипте, и в Kivy-приложении.
"""

CHAR_UUID_WRITE = "0000fff3-0000-1000-8000-00805f9b34fb"
CHAR_UUID_NOTIFY = "0000fff4-0000-1000-8000-00805f9b34fb"

STROBE_CODES = {
    "white": 0x9C,
    "blue": 0x98,
    "green": 0x97,
    "red": 0x96,
    "color": 0x95,
}


def pkt(byte2: int, byte3: int, p1: int = 0xFF, p2: int = 0xFF,
        p3: int = 0xFF, p4: int = 0xFF, byte8: int = 0x00) -> bytes:
    return bytes([0x7E, byte2 & 0xFF, byte3 & 0xFF,
                  p1 & 0xFF, p2 & 0xFF, p3 & 0xFF, p4 & 0xFF,
                  byte8 & 0xFF, 0xEF])


def cmd_power(on: bool) -> bytes:
    if on:
        return bytes.fromhex("7E0404F00001FF00EF")
    return bytes.fromhex("7E0404000000FF00EF")


def cmd_color(r: int, g: int, b: int) -> bytes:
    return pkt(0x00, 0x05, 0x03, r, g, b, byte8=0x00)


def cmd_brightness(level: int, light_mode: int = 0xFF) -> bytes:
    return pkt(0x00, 0x01, level, light_mode, 0x00, 0x00, byte8=0x00)


def cmd_temp(warm: int) -> bytes:
    cold = 100 - warm
    return pkt(0x00, 0x05, 0x02, warm, cold, 0x00, byte8=0x10)


def cmd_preset(color_index: int) -> bytes:
    """Встроенный анимированный режим по индексу (0-20ish, зависит от клона)."""
    return pkt(0x00, 0x05, 0x01, color_index, 0x00, 0x00, byte8=0x10)


def cmd_preset_speed(speed: int) -> bytes:
    """Скорость анимации пресета, обычно 0-255 (0 = самая быстрая)."""
    return pkt(0x00, 0x02, speed, 0x00, 0x00, 0x00, byte8=0x00)


def cmd_strobe(name: str) -> bytes:
    code = STROBE_CODES[name]
    return bytes([0x7E, 0x05, 0x03, code, 0x03, 0xFF, 0xFF, 0x00, 0xEF])


def parse_hex_color(s: str):
    s = s.strip().lstrip("#")
    if len(s) != 6:
        raise ValueError("Цвет должен быть в формате RRGGBB")
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
