# Открой Хабаровский край

Локальный потребительский стенд для распознавания достопримечательностей по фотографии, просмотра каталога и построения маршрутов. Проект полностью отделён от исходного прототипа и хранит runtime, Python, кэши, Android SDK и данные на диске E.

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

## GitHub

Репозиторий: <https://github.com/maybeGILGAMESH/turism_hab> (публичный, права на фотографии оформлены).

| Ветка / тег | Что внутри |
|---|---|
| `v2.0.0-demo-stable` | зафиксированная стабильная демо-версия 2.0.0 |
| `main` | версия 2.0.0 и актуальная документация |
| `feature/v3-tour-guide` | версия 3.0: карточки мест, расчёт маршрутов, локальный ИИ-гид, новый интерфейс |

В Git попадают код, каталог, воспроизводимый manifest, lock-файлы и отчёты.
Фотографии, модель CLIP, FAISS, `.env`, SQLite, Android SDK, `.venv`, `node_modules`
и пользовательские загрузки исключены. После клонирования положите исходный набор
в путь выше и выполните `bootstrap.ps1`, `collect-data.ps1` и `build-index.ps1`.

### Клонирование

```powershell
git clone https://github.com/maybeGILGAMESH/turism_hab.git
cd turism_hab
git checkout v2.0.0-demo-stable        # стабильная версия
git checkout feature/v3-tour-guide     # версия 3.0
```

### Отправка изменений по HTTPS с токеном

Токен вводится при каждом `git push` и нигде не сохраняется.

1. Один раз в папке репозитория отключите сохранение учётных данных:

   ```powershell
   git config --local credential.helper ""
   ```

2. Создайте токен: **Settings → Developer settings → Personal access tokens →
   Fine-grained tokens → Generate new token**. Укажите срок действия, в
   **Repository access** выберите только `turism_hab`, в **Repository permissions**
   выставьте **Contents** и **Workflows** в **Read and write** (Workflows нужен из-за
   `.github/workflows/ci.yml`). Токен показывается один раз.

3. Рабочий цикл:

   ```powershell
   git status
   git add .
   git commit -m "описание изменений"
   git push                     # для новой ветки: git push -u origin <ветка>
   ```

   На запрос `Username` введите логин GitHub, на запрос `Password` — токен
   (в PowerShell вставка правой кнопкой мыши, символы не отображаются).

Ошибка `Invalid username or token` означает, что вместо токена введён пароль,
токен истёк или у него нет доступа к репозиторию и прав Contents/Workflows.
Не добавляйте токен в адрес remote — он сохранится открытым текстом в `.git/config`.
Ненужный токен удаляется на странице **Fine-grained tokens → Delete**.
