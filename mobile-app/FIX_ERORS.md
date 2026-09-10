# Исправление ошибок

## Проблемы

1. `Cannot find module 'babel-preset-expo'` - хотя пакет установлен
2. `Unable to resolve asset "./assets/icon.png"` - уже исправлено в app.json
3. `TypeError: route is not a function` - проблема с зависимостями

## Решение

### Шаг 1: Очистите кэш и переустановите зависимости

```bash
cd mobile-app

# Удалите node_modules и lock файлы
rm -rf node_modules package-lock.json

# Очистите кэш npm
npm cache clean --force

# Установите зависимости заново
npm install
```

### Шаг 2: Обновите все пакеты до совместимых версий для SDK 54

```bash
# Это автоматически установит правильные версии
npx expo install --fix
```

### Шаг 3: Очистите кэш Metro bundler

```bash
# Остановите Metro (Ctrl+C если запущен)

# Очистите кэш
npx expo start --clear
# или
npx react-native start --reset-cache
```

### Шаг 4: Перезапустите приложение

```bash
npm start
```

## Если проблема остаётся

### Вариант A: Использовать правильную версию babel-preset-expo для SDK 54

```bash
npm install --save-dev babel-preset-expo@~12.0.0
```

Или удалите babel-preset-expo из devDependencies - Expo SDK 54 включает свою версию.

### Вариант B: Проверить версии React

Для Expo SDK 54 нужны:
- `react`: `18.3.1` (не 19.1.0!)
- `react-native`: `0.76.5` (не 0.81.5!)

Исправьте в package.json:

```json
"react": "18.3.1",
"react-native": "0.76.5",
```

Затем:
```bash
npm install
npx expo install --fix
```

### Вариант C: Полная переустановка

```bash
cd mobile-app
rm -rf node_modules package-lock.json .expo
npm cache clean --force
npm install
npx expo install --fix
npx expo start --clear
```

## Проверка

После выполнения всех шагов:
1. Должен запуститься Metro bundler без ошибок
2. Должен появиться QR код
3. В Expo Go должно загрузиться приложение

Если всё ещё есть ошибки, покажите полный вывод терминала.

