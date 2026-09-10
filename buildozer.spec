[app]
title = ELK LED
package.name = elkled
package.domain = org.akittyr

source.dir = .
source.include_exts = py

version = 0.1

requirements = python3,kivy,pyjnius

orientation = portrait
fullscreen = 0

# Права: BLUETOOTH_SCAN/CONNECT — Android 12+, ACCESS_FINE_LOCATION —
# нужен на более старых версиях для сканирования/подключения по BLE.
android.permissions = BLUETOOTH,BLUETOOTH_ADMIN,BLUETOOTH_SCAN,BLUETOOTH_CONNECT,ACCESS_FINE_LOCATION

android.api = 33
android.minapi = 24
android.archs = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1
