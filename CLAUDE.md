# English Encyclopedia — правила для агентов

- Общение с автором — на простом русском.
- Реестры `apps/taxonomy/registry.py` и `apps/curriculum/registry.py` — источник истины. Не менять смысл занятых ID классов, маркеров и цветов.
- Новая лексика — только YAML-пакетами в `content/seed_lexicon/` с новыми ID `LX-xxxxx`. Не выдумывать подтверждение CEFR: без сверки ставить `cefr: unverified`.
- После изменений контента: `load_content`, `audit_course`, тесты.
- Перед завершением работы: `uv run python manage.py test tests` и проверка страниц в браузере.
- Скиллы проекта лежат в `.claude/skills/` (GSAP, Supabase, UI/UX Pro Max).
- Русская транскрипция строится автоматически из IPA (`apps/lexicon/phonetics.py`, одна таблица на весь курс). Ручной вариант — поле `ipa_ru` у слова или ключ `ru` в `sound_notes` и `pronunciation` стихов. Новый символ IPA добавлять в таблицу, а не обходить вручную.
