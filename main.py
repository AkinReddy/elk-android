"""
main.py — Kivy-приложение для ELK-BLEDDM.

Важно: на обычном ПК (без Android) BLE-модуль pyjnius недоступен —
в этом случае приложение работает в режиме отладки UI: команды не
шлются на ленту, но печатаются в консоль. Это позволяет крутить
интерфейс на слабом ноутбуке без пересборки под Android каждый раз.
Реальная отправка команд появится только после сборки buildozer'ом
на телефоне.
"""

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.slider import Slider
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView

import protocol
import presets
from colorwheel import ColorWheel

try:
    from ble_gatt import BleController
    HAS_BLE = True
except Exception:
    HAS_BLE = False

    class BleController:
        """Заглушка для отладки UI на десктопе без Android/pyjnius."""

        def __init__(self, on_status=None):
            self.on_status = on_status or (lambda s: None)
            self.connected = True  # чтобы кнопки в UI не блокировались

        def connect(self, address):
            self.on_status(f"[DEBUG] connect({address}) — BLE недоступен на этой платформе")

        def disconnect(self):
            self.on_status("[DEBUG] disconnect()")

        def write(self, data: bytes):
            self.on_status(f"[DEBUG] -> {data.hex().upper()}")


class RootLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)

        self.ble = BleController(on_status=self._set_status)

        # --- строка подключения ---
        top = BoxLayout(size_hint=(1, None), height=48, spacing=6, padding=6)
        self.address_input = TextInput(
            text="BE:27:51:00:0E:54", multiline=False, size_hint=(0.6, 1)
        )
        connect_btn = Button(text="Подключить", size_hint=(0.4, 1))
        connect_btn.bind(on_release=self._connect)
        top.add_widget(self.address_input)
        top.add_widget(connect_btn)
        self.add_widget(top)

        self.status_label = Label(
            text="Не подключено" + ("" if HAS_BLE else "  [режим отладки UI]"),
            size_hint=(1, None), height=28,
        )
        self.add_widget(self.status_label)

        # --- вкл/выкл + яркость ---
        power_row = BoxLayout(size_hint=(1, None), height=48, spacing=6, padding=6)
        on_btn = Button(text="Включить")
        off_btn = Button(text="Выключить")
        on_btn.bind(on_release=lambda *_: self.ble.write(protocol.cmd_power(True)))
        off_btn.bind(on_release=lambda *_: self.ble.write(protocol.cmd_power(False)))
        power_row.add_widget(on_btn)
        power_row.add_widget(off_btn)
        self.add_widget(power_row)

        brightness_row = BoxLayout(size_hint=(1, None), height=48, spacing=6, padding=6)
        brightness_row.add_widget(Label(text="Яркость", size_hint=(0.3, 1)))
        brightness_slider = Slider(min=0, max=255, value=180, size_hint=(0.7, 1))
        brightness_slider.bind(
            value=lambda inst, val: self.ble.write(protocol.cmd_brightness(int(val)))
        )
        brightness_row.add_widget(brightness_slider)
        self.add_widget(brightness_row)

        # --- вкладки: колесо / пресеты / эффекты ---
        tabs = TabbedPanel(do_default_tab=False, size_hint=(1, 1))

        wheel_tab = TabbedPanelItem(text="Колесо")
        self.wheel = ColorWheel()
        self.wheel.bind(on_color_change=self._on_wheel_color)
        wheel_tab.add_widget(self.wheel)
        tabs.add_widget(wheel_tab)

        presets_tab = TabbedPanelItem(text="Пресеты")
        presets_tab.add_widget(self._build_presets_grid())
        tabs.add_widget(presets_tab)

        effects_tab = TabbedPanelItem(text="Эффекты")
        effects_tab.add_widget(self._build_effects_list())
        tabs.add_widget(effects_tab)

        tabs.default_tab = wheel_tab
        self.add_widget(tabs)

    def _set_status(self, text):
        self.status_label.text = text

    def _connect(self, *_):
        self.ble.connect(self.address_input.text.strip())

    def _on_wheel_color(self, instance, rgb):
        r, g, b = rgb
        self.ble.write(protocol.cmd_color(r, g, b))

    def _build_presets_grid(self):
        scroll = ScrollView()
        grid = GridLayout(cols=3, size_hint=(1, None), spacing=4, padding=4)
        grid.bind(minimum_height=grid.setter("height"))
        for name, hex_color in presets.PURPLE_PRESETS:
            r, g, b = protocol.parse_hex_color(hex_color)
            btn = Button(
                text=name,
                background_color=(r / 255, g / 255, b / 255, 1),
                size_hint_y=None,
                height=64,
            )
            btn.bind(
                on_release=lambda inst, rr=r, gg=g, bb=b: self.ble.write(
                    protocol.cmd_color(rr, gg, bb)
                )
            )
            grid.add_widget(btn)
        scroll.add_widget(grid)
        return scroll

    def _build_effects_list(self):
        scroll = ScrollView()
        grid = GridLayout(cols=1, size_hint=(1, None), spacing=4, padding=4)
        grid.bind(minimum_height=grid.setter("height"))

        for index, label in presets.BUILTIN_MODES:
            btn = Button(text=label, size_hint_y=None, height=48)
            btn.bind(
                on_release=lambda inst, i=index: self.ble.write(protocol.cmd_preset(i))
            )
            grid.add_widget(btn)

        for name, label in presets.STROBE_LABELS:
            btn = Button(text=label, size_hint_y=None, height=48)
            btn.bind(
                on_release=lambda inst, n=name: self.ble.write(protocol.cmd_strobe(n))
            )
            grid.add_widget(btn)

        scroll.add_widget(grid)
        return scroll


class ElkLedApp(App):
    def build(self):
        return RootLayout()


if __name__ == "__main__":
    ElkLedApp().run()
