# English Encyclopedia

Интерактивная энциклопедия и курс американского английского A0–B2+ для русскоязычных учеников.
Главный принцип: «Не зубри английский. Пойми его».

Стек: Django 5.2, PostgreSQL на Supabase (локально SQLite), шаблоны Django, чистые CSS и JS, GSAP. Шрифты и GSAP лежат в проекте.

## Запуск на своём компьютере (Windows)

Самый простой путь: дважды щёлкните `start.bat`. Он поставит uv (если его нет), установит зависимости, подготовит базу, загрузит уроки и откроет сайт. Администратора для `/admin/` создаёт `create_admin.bat`.

Вручную (PowerShell):


1. Установите [uv](https://docs.astral.sh/uv/): `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
2. В папке проекта:
   ```powershell
   uv sync
   copy .env.example .env
   uv run python manage.py migrate
   uv run python manage.py load_content
   uv run python manage.py createsuperuser
   uv run python manage.py runserver
   ```
3. Откройте http://127.0.0.1:8000

Без `DATABASE_URL` в `.env` используется локальная база SQLite: Supabase для первого запуска не нужен.

## Озвучка историй

Дважды щёлкните `generate_audio.bat`. Он ставит пакеты синтеза речи, один раз скачивает модель Kokoro (около 310 МБ, в папку `models/`), озвучивает все истории по ролям и обновляет сайт.

- Голоса ролей — `content/manifests/voices.yaml`: один герой = один голос на весь курс.
- Реплики истории — поле `script` в `content/seed_stories/*.yaml` (`speaker`, `kind`, `text` с разметкой).
- Результат — `static/audio/stories/sNN/`: медленная и обычная версии, тайминги реплик и `manifest.json`. Фон сцены лежит в `static/audio/ambience/`.
- Пока произношение не прослушано человеком, в `manifest.json` стоит `"verified": false`, и сайт об этом предупреждает.

## Подключение Supabase

1. Создайте проект на supabase.com.
2. Project Settings → Database → Connection string. Для сайта — адрес пулера (порт 6543), для миграций — прямой (порт 5432).
3. Пропишите `DATABASE_URL` в `.env` и выполните `uv run python manage.py migrate`.

После каждой миграции на PostgreSQL включается RLS на всех таблицах схемы `public`. Политик нет намеренно: Data API Supabase (роли anon и authenticated) не видит ничего, а Django работает владельцем таблиц и видит всё. Пароли, сессии и прогресс учеников не утекут через публичный API.

## Команды

| Команда | Что делает |
|---|---|
| `uv run python manage.py load_content` | Загружает слова, уроки и упражнения из `content/` (повторный запуск обновляет записи) |
| `uv run python manage.py audit_course` | Аудит: квоты 6200/60/60, реестр маркеров, разметка, незарегистрированные слова |
| `uv run pytest` | Тесты (или `uv run python manage.py test tests`) |

## Где что лежит

- `apps/taxonomy/registry.py` — неизменяемый реестр 11 категорий, маркеров, классов и 10 цветов.
- `apps/curriculum/registry.py` — количественный план: уровни, единицы, недели, истории, стихи.
- `content/seed_lexicon/` — пакеты лексики в YAML; `content/seed_lessons/` — уроки с семью слоями и упражнениями.
- `static/css/linguistic-markers.css` — маркеры; `static/css/design-tokens.css` — дизайн-токены.
- `docs/CONTEXT.md` — словарь проекта; `docs/adr/` — архитектурные решения; `docs/specs/` — спецификации.
- `.claude/skills/` — скиллы проекта (GSAP, Supabase, UI/UX Pro Max).

## Оформление «Студия»

Все публичные страницы, регистрация, вход и личный кабинет используют светлый каркас с боковой навигацией. Стиль находится в `static/css/studio.css`, поверх общих компонентов; шрифты Golos Text, Literata и Gentium Plus остаются локальными. В словаре есть поиск по английскому слову и русскому переводу (совместим с фильтрами уровня и категории). В уроке можно менять размер текста от 15 до 24 px. Цветные маркеры сохраняют существующую систему классов и линий; их переключатель работает как прежде.

## Формат разметки

`[S1]mother[/]` — буква категории и номер класса. Можно добавить цвет: `[S1-#d32f2f]mother[/]`. Цвет сверяется с реестром, и расхождение считается ошибкой контента.

## Скиллы проекта

Скиллы GSAP (8), Supabase (2) и UI/UX Pro Max лежат в репозитории в `.claude/skills/` и подхватываются автоматически.
