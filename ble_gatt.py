"""
ble_gatt.py — прямой доступ к BLE через android.bluetooth.BluetoothGatt
(pyjnius), потому что bleak на Android не работает — там нет BlueZ/D-Bus.

Работает только внутри python-for-android сборки (Kivy/Buildozer),
на десктопном Python импорт jnius упадёт сразу — это ожидаемо.

Права, которые нужно прописать в buildozer.spec:
    android.permissions = BLUETOOTH, BLUETOOTH_ADMIN,
        BLUETOOTH_SCAN, BLUETOOTH_CONNECT, ACCESS_FINE_LOCATION
"""

from jnius import autoclass, PythonJavaClass, java_method

BluetoothAdapter = autoclass("android.bluetooth.BluetoothAdapter")
BluetoothProfile = autoclass("android.bluetooth.BluetoothProfile")
BluetoothGattCharacteristic = autoclass("android.bluetooth.BluetoothGattCharacteristic")
BluetoothDevice = autoclass("android.bluetooth.BluetoothDevice")
UUID = autoclass("java.util.UUID")
PythonActivity = autoclass("org.kivy.android.PythonActivity")

WRITE_UUID = UUID.fromString("0000fff3-0000-1000-8000-00805f9b34fb")
# У части клонов сервис/характеристика вложены в 0000fff0 — обычно
# discoverServices() сам находит характеристику по UUID независимо
# от родительского сервиса, так что искать по нему не нужно.


class _GattCallback(PythonJavaClass):
    """Прокси для android.bluetooth.BluetoothGattCallback.

    Сигнатуры методов ниже соответствуют "старым" (не-byte[]) перегрузкам,
    которые остаются рабочими на всех версиях Android, хотя часть из них
    formально deprecated начиная с API 33. Если на твоей версии Android
    коллбэки не вызываются — первое, что проверять.
    """

    __javainterfaces__ = ["android/bluetooth/BluetoothGattCallback"]

    def __init__(self, owner):
        super().__init__()
        self.owner = owner

    @java_method("(Landroid/bluetooth/BluetoothGatt;II)V")
    def onConnectionStateChange(self, gatt, status, new_state):
        if new_state == BluetoothProfile.STATE_CONNECTED:
            self.owner._on_connected(gatt)
        elif new_state == BluetoothProfile.STATE_DISCONNECTED:
            self.owner._on_disconnected()

    @java_method("(Landroid/bluetooth/BluetoothGatt;I)V")
    def onServicesDiscovered(self, gatt, status):
        self.owner._on_services_discovered(gatt, status)

    @java_method(
        "(Landroid/bluetooth/BluetoothGatt;"
        "Landroid/bluetooth/BluetoothGattCharacteristic;I)V"
    )
    def onCharacteristicWrite(self, gatt, characteristic, status):
        self.owner._on_write_complete(status)


class BleController:
    """Одно активное GATT-соединение с лентой.

    Использование:
        ble = BleController(on_status=lambda s: print(s))
        ble.connect("BE:27:51:00:0E:54")
        ...
        ble.write(protocol.cmd_color(255, 0, 128))
    """

    def __init__(self, on_status=None):
        self.on_status = on_status or (lambda s: None)
        self.gatt = None
        self.char = None
        self.connected = False
        self._write_queue = []
        self._writing = False
        self._callback = _GattCallback(self)

    def _log(self, msg):
        self.on_status(msg)

    def connect(self, address: str):
        adapter = BluetoothAdapter.getDefaultAdapter()
        if adapter is None:
            self._log("Bluetooth-адаптер не найден")
            return
        device = adapter.getRemoteDevice(address)
        activity = PythonActivity.mActivity
        # autoConnect=False — обычное активное подключение
        self.gatt = device.connectGatt(
            activity, False, self._callback, BluetoothDevice.TRANSPORT_LE
        )
        self._log(f"Подключаюсь к {address}...")

    def disconnect(self):
        if self.gatt is not None:
            self.gatt.disconnect()
            self.gatt.close()
        self.gatt = None
        self.char = None
        self.connected = False

    def _on_connected(self, gatt):
        self._log("Соединение установлено, ищу сервисы...")
        gatt.discoverServices()

    def _on_disconnected(self):
        self.connected = False
        self.char = None
        self._log("Отключено")

    def _on_services_discovered(self, gatt, status):
        char = gatt.getService(gatt.getServices().get(0).getUuid())
        # Ищем характеристику fff3 среди всех сервисов, не полагаясь
        # на конкретный родительский service UUID (у клонов отличается).
        found = None
        services = gatt.getServices()
        for i in range(services.size()):
            service = services.get(i)
            characteristic = service.getCharacteristic(WRITE_UUID)
            if characteristic is not None:
                found = characteristic
                break
        if found is None:
            self._log("Характеристика fff3 не найдена — не тот контроллер?")
            return
        self.char = found
        self.connected = True
        self._log("Готово к отправке команд")
        self._flush_queue()

    def _on_write_complete(self, status):
        self._writing = False
        self._flush_queue()

    def _flush_queue(self):
        if self._writing or not self._write_queue or self.char is None:
            return
        data = self._write_queue.pop(0)
        self.char.setValue(data)
        self.char.setWriteType(
            BluetoothGattCharacteristic.WRITE_TYPE_NO_RESPONSE
        )
        self._writing = True
        self.gatt.writeCharacteristic(self.char)

    def write(self, data: bytes):
        """Кладёт пакет в очередь на отправку (не блокирует UI-поток)."""
        java_bytes = bytes(data)
        self._write_queue.append(java_bytes)
        self._flush_queue()
