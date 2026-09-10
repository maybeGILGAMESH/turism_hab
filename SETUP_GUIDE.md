# 🐍 Руководство по настройке Python окружения

## Создание виртуального окружения

### Шаг 1: Перейдите в директорию проекта

```bash
cd /home/ruslan/Downloads/sbermetro-main
```

### Шаг 2: Создайте виртуальное окружение

**Вариант A: Используя `venv` (рекомендуется для Python 3.3+)**

```bash
# Создание виртуального окружения
python3 -m venv venv

# Или если python3 не найден, попробуйте:
python -m venv venv
```

**Вариант B: Используя `virtualenv` (если venv недоступен)**

```bash
# Сначала установите virtualenv (если не установлен)
pip install virtualenv

# Создайте виртуальное окружение
virtualenv venv
```

### Шаг 3: Активируйте виртуальное окружение

**Для Linux/macOS:**
```bash
source venv/bin/activate
```

**Для Windows:**
```bash
venv\Scripts\activate
```

После активации вы увидите `(venv)` в начале командной строки:
```
(venv) user@computer:~/sbermetro-main$
```

### Шаг 4: Обновите pip (рекомендуется)

```bash
pip install --upgrade pip
```

### Шаг 5: Установите зависимости проекта

```bash
# Установка основных зависимостей
pip install -r requirements.txt

# Установка дополнительных зависимостей (если есть)
pip install -r requirements_new.txt
```

### Шаг 6: Проверьте установку

```bash
# Проверьте, что основные пакеты установлены
python -c "import fastapi; import streamlit; import torch; print('✅ Все зависимости установлены!')"
```

## Полная последовательность команд (для копирования)

```bash
# 1. Переход в директорию проекта
cd /home/ruslan/Downloads/sbermetro-main

# 2. Создание виртуального окружения
python3 -m venv venv

# 3. Активация окружения
source venv/bin/activate

# 4. Обновление pip
pip install --upgrade pip

# 5. Установка зависимостей
pip install -r requirements.txt
pip install -r requirements_new.txt

# 6. Проверка работоспособности
python test_system.py

# 7. Запуск системы
python run_system.py
```

## Деактивация окружения

Когда закончите работу, деактивируйте окружение:
```bash
deactivate
```

## Управление виртуальным окружением

### Просмотр установленных пакетов
```bash
pip list
```

### Сохранение списка зависимостей (если нужно обновить requirements.txt)
```bash
pip freeze > requirements_freeze.txt
```

### Удаление виртуального окружения
```bash
# Сначала деактивируйте
deactivate

# Затем удалите директорию
rm -rf venv
```

## Устранение проблем

### Проблема: "python3: command not found"
```bash
# Проверьте версию Python
python --version

# Если Python установлен, но команда называется по-другому, используйте:
python -m venv venv
```

### Проблема: "No module named 'venv'"
```bash
# Установите python3-venv (для Ubuntu/Debian)
sudo apt-get install python3-venv

# Или используйте virtualenv
pip install virtualenv
virtualenv venv
```

### Проблема: Ошибки при установке зависимостей
```bash
# Убедитесь, что pip обновлен
pip install --upgrade pip setuptools wheel

# Попробуйте установить зависимости по одной
pip install fastapi
pip install streamlit
pip install uvicorn
# и т.д.
```

### Проблема: Конфликты версий
```bash
# Используйте точные версии из requirements.txt
pip install -r requirements.txt --no-cache-dir

# Или создайте новое окружение с нуля
deactivate
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Проверка версии Python

Проект требует Python 3.11+. Проверьте версию:

```bash
python3 --version
# или
python --version
```

Если версия ниже 3.11, установите новую версию Python или используйте `pyenv` для управления версиями.

## Использование pyenv (опционально)

Если у вас несколько версий Python:

```bash
# Установка pyenv (если не установлен)
curl https://pyenv.run | bash

# Установка Python 3.11
pyenv install 3.11.0

# Установка как локальная версия для проекта
cd /home/ruslan/Downloads/sbermetro-main
pyenv local 3.11.0

# Затем создайте venv
python -m venv venv
```

## Структура после создания окружения

```
sbermetro-main/
├── venv/                    # Виртуальное окружение (не добавлять в git)
│   ├── bin/
│   ├── lib/
│   └── ...
├── artifacts/               # Данные проекта
├── data/
├── app.py
├── frontend.py
├── requirements.txt
├── requirements_new.txt
└── ...
```

## Дополнительные советы

1. **Добавьте venv в .gitignore** (если используете git):
   ```
   echo "venv/" >> .gitignore
   ```

2. **Используйте отдельное окружение для каждого проекта** - это хорошая практика

3. **Активируйте окружение перед каждой сессией работы** с проектом

4. **Проверяйте активацию** - команда `which python` должна показывать путь к venv:
   ```bash
   which python
   # Должно быть: /home/ruslan/Downloads/sbermetro-main/venv/bin/python
   ```

## Быстрый старт (одной командой)

Создайте скрипт `setup.sh`:

```bash
#!/bin/bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements_new.txt
echo "✅ Окружение готово! Активируйте его: source venv/bin/activate"
```

Затем:
```bash
chmod +x setup.sh
./setup.sh
```



