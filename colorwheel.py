"""
colorwheel.py — круглый HSV-селектор цвета для Kivy.
Угол = оттенок (hue), расстояние от центра = насыщенность.
Яркость (value) держим на максимуме здесь — за реальную яркость лампы
отвечает отдельный слайдер, который шлёт cmd_brightness().
"""

import colorsys
import math

from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse, Rectangle
from kivy.graphics.texture import Texture
from kivy.event import EventDispatcher


WHEEL_RESOLUTION = 200  # пикселей текстуры на сторону, тоньше = плавнее, но дольше генерится


def _build_wheel_texture(size=WHEEL_RESOLUTION):
    texture = Texture.create(size=(size, size), colorfmt="rgba")
    buf = bytearray(size * size * 4)
    center = size / 2
    radius = size / 2
    for y in range(size):
        for x in range(size):
            dx = x - center
            dy = y - center
            dist = math.hypot(dx, dy)
            idx = (y * size + x) * 4
            if dist > radius:
                buf[idx:idx + 4] = (0, 0, 0, 0)
                continue
            angle = math.atan2(dy, dx)
            hue = (angle / (2 * math.pi)) % 1.0
            sat = min(dist / radius, 1.0)
            r, g, b = colorsys.hsv_to_rgb(hue, sat, 1.0)
            buf[idx] = int(r * 255)
            buf[idx + 1] = int(g * 255)
            buf[idx + 2] = int(b * 255)
            buf[idx + 3] = 255
    texture.blit_buffer(bytes(buf), colorfmt="rgba", bufferfmt="ubyte")
    texture.flip_vertical()
    return texture


class ColorWheel(Widget, EventDispatcher):
    """Использование:
        wheel = ColorWheel()
        wheel.bind(on_color_change=lambda inst, rgb: print(rgb))
    """

    __events__ = ("on_color_change",)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._texture = _build_wheel_texture()
        self._marker_pos = (0, 0)  # относительно центра виджета
        self.bind(pos=self._redraw, size=self._redraw)
        self._redraw()

    def _redraw(self, *args):
        self.canvas.clear()
        side = min(self.width, self.height)
        ox = self.x + (self.width - side) / 2
        oy = self.y + (self.height - side) / 2
        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(texture=self._texture, pos=(ox, oy), size=(side, side))
            # маркер выбранной точки
            mx, my = self._marker_pos
            marker_r = 8
            Color(0, 0, 0, 0.8)
            Ellipse(
                pos=(ox + side / 2 + mx - marker_r,
                     oy + side / 2 + my - marker_r),
                size=(marker_r * 2, marker_r * 2),
            )
            Color(1, 1, 1, 1)
            Ellipse(
                pos=(ox + side / 2 + mx - marker_r + 2,
                     oy + side / 2 + my - marker_r + 2),
                size=(marker_r * 2 - 4, marker_r * 2 - 4),
            )
        self._side = side
        self._origin = (ox, oy)

    def _pick(self, touch_x, touch_y):
        side = min(self.width, self.height)
        cx = self.center_x
        cy = self.center_y
        dx = touch_x - cx
        dy = touch_y - cy
        radius = side / 2
        dist = min(math.hypot(dx, dy), radius)
        angle = math.atan2(dy, dx)
        # ограничиваем маркер границей круга, даже если палец вышел за него
        if math.hypot(dx, dy) > radius:
            dx = math.cos(angle) * radius
            dy = math.sin(angle) * radius
        self._marker_pos = (dx, dy)

        hue = (angle / (2 * math.pi)) % 1.0
        sat = min(dist / radius, 1.0)
        r, g, b = colorsys.hsv_to_rgb(hue, sat, 1.0)
        rgb = (int(r * 255), int(g * 255), int(b * 255))
        self._redraw()
        self.dispatch("on_color_change", rgb)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._pick(*touch.pos)
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self.collide_point(*touch.pos) or touch.grab_current is self:
            self._pick(*touch.pos)
            return True
        return super().on_touch_move(touch)

    def on_color_change(self, rgb):
        """Пустой дефолтный хендлер — обязателен для кастомного события Kivy."""
        pass
