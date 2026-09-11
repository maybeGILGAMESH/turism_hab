# Android Emulator на диске E

Проект хранит Android SDK в `.runtime/android/sdk`, AVD в `.runtime/android/user/avd` и Gradle cache в `.cache/gradle`. Эти переменные выставляет `scripts/env.ps1`.

Из-за ограничения Android Emulator на кириллицу профиль создаёт junction
`E:\turism_hab_runtime` → `<project>\.runtime`. Это только ASCII-путь доступа:
все реальные файлы по-прежнему находятся в проекте на E.

1. Выполните `PowerShell -ExecutionPolicy Bypass -File .\install-android.ps1`.
2. Скрипт установит Temurin JDK 17, Platform 35, Build-Tools 35, Platform-Tools,
   Android Emulator и Google APIs x86_64, затем создаст `Khabarovsk_Pixel_7`.
3. Проверьте, что в BIOS включена виртуализация, а Windows Hypervisor Platform доступна.
4. Запустите API, затем `start-android.ps1`. Эмулятор обращается к Windows-хосту по `10.0.2.2:8000`.

Эмулятор запускается через SwiftShader для совместимости с видеодрайверами Windows.

Проверка:

```powershell
. .\scripts\env.ps1
adb devices
emulator -list-avds
```
