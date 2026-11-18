# Weather Forecast

Цей проєкт реалізує клієнт-серверний застосунок для отримання прогнозу погоди через OpenWeatherMap REST API, збереження нормалізованих даних у реляційній базі даних PostgreSQL та відображення результатів у нативному віджеті (Plasmoid) для робочого середовища KDE Plasma 6.

## Структура проєкту

Репозиторій складається з двох основних компонентів:

1. `backend/` — серверна частина на Python (FastAPI, `requests`, `psycopg2`), що відповідає за запити до зовнішнього API, валідацію відповідей, обробку помилок та збереження даних у PostgreSQL.
2. `plasmoid/tech.babych.owmforecast/` — графічний інтерфейс користувача на QML/Kirigami для KDE Plasma 6.

Основні файли:
* `backend/app/config.py`: завантаження змінних середовища та параметрів підключення з файлу `.env`.
* `backend/app/api.py`: клієнт OpenWeatherMap API (5-денний прогноз та геокодування) з обробкою мережевих і HTTP-помилок.
* `backend/app/db.py`: ініціалізація схеми БД  та параметризовані SQL-запити.
* `backend/app/server.py`: локальний HTTP-сервер для взаємодії віджета KDE Plasma 6 із базою даних та API.

## Опис API та схеми бази даних

### Зовнішнє API (OpenWeatherMap)

Застосунок використовує два ендпоінти OpenWeatherMap REST API:

1. **Прогноз погоди на 5 днів з кроком 3 години:**
   `GET https://api.openweathermap.org/data/2.5/forecast`
   * `q` або `lat`, `lon` — динамічні параметри запиту (назва міста або координати обраної області), які змінюють відповідь сервера.
   * `appid` — ключ доступу до API (передається зі змінних середовища, не зберігається в коді).
   * `units=metric` — отримання температури у градусах Цельсія.
   * `lang=uk` — українська локалізація погодних умов.

2. **Геокодування та пошук областей:**
   `GET https://api.openweathermap.org/geo/1.0/direct`
   * `q` — пошуковий рядок для отримання списку населених пунктів із зазначенням області (`state`) та країни (`country`).
   * `limit=5` — обмеження кількості підказок.

### Схема бази даних PostgreSQL

Дані зберігаються у двох таблицях, пов'язаних зовнішнім ключем (`Foreign Key`):

1. Таблиця `cities` (довідник міст):
   * `id` (`INTEGER PRIMARY KEY`) — унікальний ідентифікатор міста з OpenWeatherMap.
   * `name` (`VARCHAR(100) NOT NULL`) — назва міста (з областю за наявності).
   * `country` (`VARCHAR(10) NOT NULL`) — код країни.
   * `population` (`INTEGER DEFAULT 0`) — населення.
   * `timezone` (`INTEGER DEFAULT 0`) — зсув часового поясу.
   * `updated_at` (`TIMESTAMP DEFAULT CURRENT_TIMESTAMP`) — час останнього оновлення.

2. Таблиця `forecasts` (часові точки прогнозу):
   * `id` (`SERIAL PRIMARY KEY`) — первинний ключ запису.
   * `city_id` (`INTEGER NOT NULL REFERENCES cities(id) ON DELETE CASCADE`) — зовнішній ключ (`Foreign Key`) до таблиці `cities`.
   * `forecast_time` (`TIMESTAMP NOT NULL`) — дата й час прогнозу.
   * `temp` (`NUMERIC(5, 2) NOT NULL`) — температура повітря.
   * `feels_like` (`NUMERIC(5, 2) NOT NULL`) — відчувається як.
   * `humidity` (`INTEGER NOT NULL`) — вологість повітря у відсотках.
   * `description` (`VARCHAR(255) NOT NULL`) — текстовий опис погоди.
   * `wind_speed` (`NUMERIC(5, 2) NOT NULL`) — швидкість вітру.

### Безпека та обробка помилок

* **Параметризовані SQL-запити:** усі операції читання та запису виконуються через параметри `%s` драйвера `psycopg2`.
* **Захист від дублікатів:** таблиця `forecasts` має обмеження `UNIQUE (city_id, forecast_time)`, а збереження даних реалізовано через `INSERT ... ON CONFLICT DO UPDATE` (UPSERT). Повторні запити оновлюють наявні записи без дублювання рядків.
* **Ізоляція секретів:** ключ `OWM_API_KEY` та параметри БД винесені у файл `.env`, який додано до `.gitignore`. У репозиторії зберігається лише шаблон `.env.example`.
* **Обробка помилок API:** клієнт перехоплює статуси відповіді `!= 200` (`401`, `404`, `429`), відсутність мережевого з'єднання (`ConnectionError`, `Timeout`), порожні відповіді та помилки парсингу JSON.

## Встановлення та запуск

### 1. Підготовка конфігурації

Клонуйте репозиторій, створіть файл `.env` на основі шаблону та вкажіть власний ключ `OWM_API_KEY`:

```bash
cp .env.example .env
```

### 2. Запуск серверної частини та бази даних

#### Варіант А: Через Docker Compose (рекомендовано)

Запустіть контейнери PostgreSQL та FastAPI-сервера однією командою:

```bash
docker compose up -d --build
```

#### Варіант Б: Локальний запуск у віртуальному середовищі Python

Якщо база даних PostgreSQL вже запущена, створіть віртуальне середовище, встановіть залежності та запустіть сервер:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn app.server:app --app-dir backend --host 0.0.0.0 --port 8000
```

### 3. Встановлення та запуск віджета KDE Plasma 6

Встановіть пакет віджета в локальне середовище користувача:

```bash
kpackagetool6 -t Plasma/Applet --install plasmoid/tech.babych.owmforecast
```

Для оновлення вже встановленого віджета:

```bash
kpackagetool6 -t Plasma/Applet --upgrade plasmoid/tech.babych.owmforecast
systemctl --user restart plasma-plasmashell.service
```

Для запуску віджета в окремому тестовому вікні:

```bash
plasmoidviewer -a tech.babych.owmforecast
```