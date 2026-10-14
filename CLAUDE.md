# English Encyclopedia — правила для агентов

- Общение с автором — на простом русском.
- Реестры `apps/taxonomy/registry.py` и `apps/curriculum/registry.py` — источник истины. Не менять смысл занятых ID классов, маркеров и цветов.
- Новая лексика — только YAML-пакетами в `content/seed_lexicon/` с новыми ID `LX-xxxxx`. Не выдумывать подтверждение CEFR: без сверки ставить `cefr: unverified`.
- После изменений контента: `load_content`, `audit_course`, тесты.
- Перед завершением работы: `uv run python manage.py test tests` и проверка страниц в браузере.
- Скиллы проекта лежат в `.claude/skills/` (GSAP, Supabase, UI/UX Pro Max).
