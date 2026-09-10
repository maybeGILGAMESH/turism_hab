# Исправление ошибки TurboModuleRegistry / PlatformConstants

## Ошибка
```
[runtime not ready]: Invariant Violation:
TurboModuleRegistry.getEnforcing(...):
'PlatformConstants' could not be found.
```

## Решение (выполните команды по порядку)

### Вариант 1: Автоматический скрипт (рекомендуется)

```bash
cd mobile-app
chmod +x FIX_DEPENDENCIES.sh
./FIX_DEPENDENCIES.sh
```

### Вариант 2: Ручное выполнение

#### Шаг 1: Удалите старые зависимости
```bash
cd mobile-app
rm -rf node_modules package-lock.json yarn.lock .expo
```

#### Шаг 2: Очистите кэш npm (уже выполнено)
```bash
npm cache clean --force
```

#### Шаг 3: Установите зависимости
```bash
npm install
```

#### Шаг 4: Исправьте версии через Expo (ВАЖНО!)
```bash
npx expo install --fix
```

Эта команда автоматически установит совместимые версии всех пакетов для Expo SDK 54.

#### Шаг 5: Запустите с очисткой кэша Metro
```bash
npx expo start --clear
```

Или если Metro уже запущен:
- Нажмите `Ctrl+C` чтобы остановить
- Нажмите `R` дважды в терминале Metro для перезагрузки
- Или перезапустите: `npx expo start --clear`

## Если ошибка остаётся

### Дополнительные шаги:

1. **Очистите кэш Expo Go на телефоне:**
   - Запустите Expo Go
   - Перезагрузите приложение (потяните вниз на главном экране)
   - Или переустановите Expo Go

2. **Проверьте версию Expo CLI:**
   ```bash
   npm install -g expo-cli@latest
   ```

3. **Убедитесь, что все пакеты установлены через expo install:**
   ```bash
   npx expo install @react-native-async-storage/async-storage
   npx expo install @react-native-community/netinfo
   npx expo install react-native-safe-area-context
   npx expo install react-native-screens
   ```

## Примечание

Команда `npx expo install --fix` автоматически установит правильные версии для Expo SDK 54, включая:
- React и React Native
- Все Expo пакеты
- Нативные модули

Это важно, потому что некоторые пакеты должны быть установлены через `expo install`, а не `npm install`, чтобы обеспечить совместимость с нативными модулями.
