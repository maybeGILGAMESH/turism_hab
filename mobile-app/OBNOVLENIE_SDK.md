# Обновление Expo SDK

## Проблема

Ошибка: "Project is incompatible with this version of Expo Go. The installed version of Expo Go is for SDK 54. The project you opened uses SDK 49."

## Решение

Проект обновлен до SDK 54. Теперь нужно обновить зависимости.

### Шаги:

1. **Удалите node_modules и package-lock.json:**
   ```bash
   cd mobile-app
   rm -rf node_modules package-lock.json
   ```

2. **Установите зависимости:**
   ```bash
   npm install
   ```

3. **Обновите все пакеты до совместимых версий для SDK 54:**
   ```bash
   npx expo install --fix
   ```
   
   Это автоматически установит правильные версии всех пакетов для SDK 54.

4. **Если есть конфликты, обновите пакеты вручную:**
   ```bash
   npx expo install expo-image-picker@latest @react-native-async-storage/async-storage@latest @react-native-community/netinfo@latest
   ```

5. **Запустите приложение:**
   ```bash
   npm start
   ```

## Что было изменено

- `expo`: `~49.0.0` → `~54.0.0`
- `react`: `18.2.0` → `18.3.1`
- `react-native`: `0.72.10` → `0.76.5`
- Все остальные зависимости обновлены до совместимых версий

## Альтернативное решение (если не хотите обновлять)

Если по каким-то причинам не хотите обновлять проект, можно установить старую версию Expo Go:

1. Удалите текущую Expo Go с телефона
2. Установите Expo Go для SDK 49:
   - Android: Найдите старую версию в Google Play или скачайте APK
   - iOS: Сложнее, нужно использовать старую версию через TestFlight

**Рекомендуется:** Обновить проект до SDK 54 (как сделано выше), так как это более новая и стабильная версия.

