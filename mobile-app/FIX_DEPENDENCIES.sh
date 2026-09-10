#!/bin/bash

echo "🔧 Исправление зависимостей для Expo (TurboModuleRegistry fix)..."
echo ""

# Шаг 1: Удаление старых зависимостей и кэшей
echo "🗑️  Удаление node_modules и lock файлов..."
rm -rf node_modules package-lock.json yarn.lock .expo

# Шаг 2: Очистка кэшей
echo "🧹 Очистка кэшей npm и Expo..."
npm cache clean --force

# Шаг 3: Установка зависимостей
echo "📦 Установка зависимостей..."
npm install

# Шаг 4: Исправление версий через Expo
echo "🔧 Исправление версий через Expo..."
npx expo install --fix

echo ""
echo "✅ Готово! Теперь запустите с очисткой кэша:"
echo "   npx expo start --clear"
echo ""
echo "Или если приложение уже запущено, нажмите 'R' дважды для перезагрузки"

