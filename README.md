# Открой Хабаровский край

Локальный потребительский стенд для распознавания достопримечательностей по фотографии, просмотра каталога и построения маршрутов. Проект полностью отделён от исходного прототипа и хранит runtime, Python, кэши, Android SDK и данные на диске E.

## Версия 3.0 (этот клон)

`turism_hab_v3`, ветка `feature/v3-tour-guide`, версия `3.0.0-dev.1`. Добавлены расширенные карточки 44 мест,
расчёт времени маршрутов, локальный ИИ-гид на Ollama (`qwen2.5:1.5b-instruct`, CPU) и обновлённый интерфейс
веба, Expo-приложения и Streamlit. Stable 2.0.0 заморожена в `..\turism_hab` и `..\backups`.

```powershell
.\scripts\install-ollama.ps1   # один раз
.\start-v3.ps1 -WithExpo       # API/веб :8100, Streamlit :8601, Expo Web :8082
```

Подробности, проверки целостности и ограничения гида — в [docs/V3.md](docs/V3.md), отчёт — в
[reports/IMPLEMENTATION_V3.md](reports/IMPLEMENTATION_V3.md). Разделы ниже описывают базовую версию;
для v3 замените порты 8000/8501/8081 на 8100/8601/8082.

## Быстрый запуск на Windows

```powershell
cd "E:\_main\проект хабаровский край туризм\turism_hab"
PowerShell -ExecutionPolicy Bypass -File .\bootstrap.ps1
. .\scripts\env.ps1
. .\.venv\Scripts\Activate.ps1
python app.py
```

Интерфейсы:

- потребительский web: <http://localhost:8000>;
- OpenAPI: <http://localhost:8000/docs>;
- Streamlit и админка: `streamlit run frontend.py`, <http://localhost:8501>;
- Expo Web: `./start-mobile-web.ps1`;
- Android Emulator: `./start-android.ps1`.

Администратор при первом локальном запуске создаётся из `ADMIN_EMAIL` и `ADMIN_PASSWORD` в `.env`. Перед демонстрацией замените значения из `.env.example`.

## Данные и индекс

```powershell
# Импорт вручную проверенного набора из dataset\datasets_clear и аугментация index
.\collect-data.ps1

# Индексация на CUDA при доступности, иначе на CPU
.\build-index.ps1 auto

# Проверка согласованности и качества
python check_index.py
```

`catalog/objects.json` содержит 44 объекта. Исходный набор ожидается в
`dataset/datasets_clear/khabarovsk_tourism_44/work/khabarovsk_tourism_44`.
Сетевой поиск при сборке не выполняется. Скрипт проверяет фактически оставшиеся
файлы, нормализует EXIF, создаёт независимые source groups и доводит только
`index` до 12 изображений на класс мягкими аугментациями. Проверочные оригиналы
никогда не аугментируются и не попадают в собственный fold.

`dataset/manifest.csv` — источник истины для происхождения, прав, хешей,
родительского изображения, аугментации и split. Публичный экспорт включает
только `open` и `cleared`:

```powershell
python data_pipeline.py export-cleared
```

> **Права на фотографии оформлены.** По состоянию на 15 сентября 2026 года права на все
> фотографии датасета оформлены. Значения `pending_purchase` в `dataset/manifest.csv`
> остались от импорта: manifest входит в SHA-256-версию FAISS-индекса, поэтому статусы
> будут обновлены на `cleared` вместе со следующей пересборкой индекса.

## Мобильное приложение

Expo SDK 54 автоматически выбирает API:

- web — `http://localhost:8000`;
- Android Emulator — `http://10.0.2.2:8000`;
- телефон — значение `EXPO_PUBLIC_API_BASE_URL` или URL из настроек.

Подробная установка Android SDK на E описана в [docs/ANDROID.md](docs/ANDROID.md).

На проверенной машине драйвер NVIDIA 522.06 несовместим с актуальным CUDA 13 runtime,
поэтому выбран гарантированный CPU-профиль. `DEVICE=auto` автоматически задействует CUDA
после обновления драйвера и установки CUDA-сборки PyTorch; без неё ничего менять не нужно.

## Docker

Docker Desktop должен быть запущен. Файл `.env` обязателен.

```powershell
.\start-docker.ps1
docker compose ps
```

Compose поднимает `api:8000` и `streamlit:8501`. Датасет, индекс, модель, SQLite и загрузки остаются в каталогах проекта на E и подключаются как volumes.

## Критерии релиза

- все 44 класса имеют ≥8 index-векторов и ≥1 независимый оригинал для проверки;
- macro top-1 accuracy ≥85%;
- false accept rate ≤5%; без отдельного negative-набора используется явно
  помеченный proxy по самому похожему неверному классу;
- recall каждого опубликованного класса ≥70%;
- индекс, manifest и каталог имеют совпадающие SHA-256 версии.

Отчёты создаются в `reports/dataset_report.json`,
`reports/quality_report.json`, а реестр правообладателей — в `reports/rights_registry.csv`.

## Текущий quality gate

Ручной набор импортирован: 309 оригиналов и 303 index-аугментации. Групповая
leave-one-source-out проверка по всем оригиналам дала top-1 `87.38%`, macro
recall `85.20%`, proxy FAR `4.85%`; recall не ниже 70% у 39 классов.
`/health` возвращает `status=ready`. Права на все фотографии оформлены; до обновления
статусов в manifest `export-cleared` по-прежнему их не включает. Подробности — в
[`reports/IMPLEMENTATION.md`](reports/IMPLEMENTATION.md).

## Подготовка к GitHub

В Git попадают код, каталог, воспроизводимый manifest, lock-файлы и отчёты.
Фотографии, модель, FAISS, `.env`, Android SDK, `.venv`, `node_modules`, SQLite
и пользовательские загрузки исключены. После клонирования положите разрешённый
исходный набор в путь выше, затем выполните `bootstrap.ps1`,
`collect-data.ps1` и `build-index.ps1`.

Репозиторий публичный: права на фотографии оформлены, секреты (`.env`), SQLite,
модель, FAISS и сами изображения в Git не попадают.

Стабильная демо-версия зафиксирована тегом `v2.0.0-demo-stable`; версия 3.0
разрабатывается в ветке `feature/v3-tour-guide`.
