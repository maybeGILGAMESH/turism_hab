# Исправление ошибки "Network request failed"

## Проблема
Ошибка `TypeError: Network request failed` при обработке запросов из очереди.

## Что было исправлено

1. ✅ **Добавлена проверка доступности сервера** - перед обработкой очереди проверяется, доступен ли сервер
2. ✅ **Улучшено логирование** - теперь видны подробные логи каждого шага
3. ✅ **Улучшена обработка ошибок** - более информативные сообщения об ошибках
4. ✅ **Валидация параметров** - проверяется наличие URL и imageUri перед запросом

## Диагностика проблемы

### Шаг 1: Проверьте логи в Metro bundler

Теперь в логах вы увидите подробную информацию:
- `🔄 Starting queue processing, API URL: ...` - начало обработки
- `✅ Internet connection available` - интернет доступен
- `✅ Server is healthy and reachable` - сервер доступен
- `❌ Server is not reachable: ...` - сервер недоступен
- `🌐 Network error for request ...` - детали сетевой ошибки

### Шаг 2: Проверьте, запущен ли сервер

```bash
# На компьютере выполните:
cd /home/ruslan/Downloads/turism
python app.py
```

Должно появиться:
```
✅ RAG searcher initialized successfully
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Шаг 3: Проверьте URL в настройках приложения

1. Откройте приложение на телефоне
2. Перейдите в раздел **"Настройки"**
3. Проверьте **"URL сервера"**
4. Должен быть указан IP адрес вашего компьютера, например: `http://192.168.0.102:8000`

**Узнать IP адрес компьютера:**
```bash
# Linux/Mac
hostname -I
# или
ip addr show | grep "inet " | grep -v 127.0.0.1

# Windows
ipconfig
```

### Шаг 4: Проверьте доступность сервера с телефона

Откройте в браузере телефона:
```
http://YOUR_IP:8000/health
```

Должен вернуться JSON ответ:
```json
{
  "status": "healthy",
  "rag_searcher": "initialized",
  "timestamp": "..."
}
```

Если не открывается:
- Проверьте, что телефон и компьютер в одной сети Wi-Fi
- Проверьте файрвол на компьютере (порт 8000 должен быть открыт)
- Убедитесь, что сервер запущен с `--host 0.0.0.0` (не `127.0.0.1`)

### Шаг 5: Проверьте настройки файрвола

```bash
# Linux (Ubuntu/Debian)
sudo ufw status
sudo ufw allow 8000/tcp

# Linux (если используете firewalld)
sudo firewall-cmd --list-ports
sudo firewall-cmd --add-port=8000/tcp --permanent
sudo firewall-cmd --reload
```

## Решение

### Если сервер недоступен

1. **Запустите сервер:**
   ```bash
   cd /home/ruslan/Downloads/turism
   python app.py
   ```

2. **Проверьте, что сервер запущен на всех интерфейсах:**
   Должно быть: `http://0.0.0.0:8000` (не `127.0.0.1:8000`)

3. **Обновите URL в настройках приложения:**
   - Откройте "Настройки" в приложении
   - Введите правильный IP адрес: `http://YOUR_IP:8000`
   - Сохраните настройки

### Если URL неправильный

1. Узнайте IP адрес компьютера
2. Откройте настройки приложения
3. Обновите URL сервера
4. Перезапустите приложение

### Если проблема сохраняется

1. Очистите очередь в приложении:
   - Откройте раздел "Очередь"
   - Нажмите "Очистить очередь" (если есть)

2. Проверьте логи сервера:
   - Посмотрите вывод в терминале, где запущен `app.py`
   - Должны быть логи запросов

3. Попробуйте распознать фото снова:
   - Теперь должны появиться подробные логи в Metro bundler
   - По логам можно определить точную причину проблемы

## Пример успешных логов

```
🔄 Starting queue processing, API URL: http://192.168.0.102:8000
✅ Internet connection available
✅ Server is healthy and reachable
📋 Processing 1 request(s) from queue
🔄 Processing request 1234567890 (attempt 1)
📤 Sending recognition request 1234567890 to: http://192.168.0.102:8000/api/recognize
📋 FormData created, sending request...
📥 Response received for request 1234567890, status: 200
✅ Request 1234567890 processed successfully
🗑️ Request 1234567890 removed from queue
```

## Пример логов при ошибке

```
🔄 Starting queue processing, API URL: http://192.168.0.102:8000
✅ Internet connection available
❌ Server is not reachable: Network request failed
   URL: http://192.168.0.102:8000/health
⚠️ Skipping queue processing - server unavailable
```

Это означает, что сервер недоступен. Проверьте:
- Запущен ли сервер
- Правильный ли IP адрес
- Доступен ли сервер с телефона

