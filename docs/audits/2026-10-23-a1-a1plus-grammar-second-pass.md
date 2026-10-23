# A1 и A1+: повторный лингвистический проход — журнал, 23.10.2026

**Статус: частично выполнено. Это НЕ финальный сертификат качества курса.**
Исходный main: `8ebdd44b8f037ef04b143e75aeef2e4c70c2395e` (merge PR #101).
Рабочая ветка: `audit/a1-a1plus-grammar-second-pass-20261023`, от указанного main. Открытых PR на старте: 0.
Проверены AGENTS.md, CLAUDE.md, `content/manifests/weeks_plan.yaml`, реестр имен файлов уроков и механика `Exercise.is_correct()`.

## Инвентаризация и порядок

Файлов-уроков: **A1 — 28 (14 недель, по два), A1+ — 32 (16 недель, по два)**.
Таблица составлена по реальным именам `content/seed_lessons/` и темам действующего `weeks_plan.yaml`. Это **карта курса**, а не заявление о полном анализе содержания каждого файла.

| Уровень / неделя | Уроки, в порядке курса (имена файлов без .yaml) | Предусмотренная грамматика / цель |
|---|---|---|
| A1 · 1 | a1_w01_l01_nouns<br>a1_w01_l02_be | существительные; be: I'm, you're, it's |
| A1 · 2 | a1_w02_l03_determiners<br>a1_w02_l04_have_like_can | a / the, this / that, my / your; have, like, can; комнаты и предметы дома |
| A1 · 3 | a1_w03_l05_cafe<br>a1_w03_l06_numbers | Can I have…?; числа 1–20; please, thanks; I'd like и want |
| A1 · 4 | a1_w04_l07_family<br>a1_w04_l08_possession | his / her / their; 's (Tom's); we / they; возраст и числа до 100; вопросы с be |
| A1 · 5 | a1_w05_l09_there_is<br>a1_w05_l10_how_much | there is / there are; How much…?; some; цвета; cheap / expensive |
| A1 · 6 | a1_w06_l11_present_simple<br>a1_w06_l12_time | Present Simple: I / you; время (at seven) |
| A1 · 7 | a1_w07_l13_he_works<br>a1_w07_l14_jobs | Present Simple: he / she + -s; профессии |
| A1 · 8 | a1_w08_l15_where_is<br>a1_w08_l16_directions | предлоги места; Where is…?; Turn left |
| A1 · 9 | a1_w09_l17_do_does<br>a1_w09_l18_spelling | вопросы с do / does; диктовка по буквам |
| A1 · 10 | a1_w10_l19_always_never<br>a1_w10_l20_like_doing | always / never; like + действие; on + день недели, in + месяц; одежда для прогулки |
| A1 · 11 | a1_w11_l21_what_hurts<br>a1_w11_l22_cant | I have a headache; can't; …hurts; части тела, hurt / hurts; be / feel + самочувствие |
| A1 · 12 | a1_w12_l23_dont_doesnt<br>a1_w12_l24_address | don't / doesn't; город, штат и ZIP code; анкета и почта |
| A1 · 13 | a1_w13_l25_can_skills<br>a1_w13_l26_why_because | can / can't — умения; Why? Because…; учебные предметы, просьба повторить, easy / difficult |
| A1 · 14 | a1_w14_l27_bus<br>a1_w14_l28_review | повторение A1: билет, прибытие и отправление; транспорт, погода и вещи для поездки |
| A1+ · 1 | a1p_w01_l01_present_continuous<br>a1p_w01_l02_video_call | Present Continuous: I'm doing, he's doing, are you…?; now, right now |
| A1+ · 2 | a1p_w02_l03_was_were<br>a1p_w02_l04_there_was | was / were; there was / there were; yesterday, last night |
| A1+ · 3 | a1p_w03_l05_past_simple_ed<br>a1p_w03_l06_weekend_small_talk | Past Simple: правильные глаголы на -ed; last weekend |
| A1+ · 4 | a1p_w04_l07_irregular_past<br>a1p_w04_l08_paying_prices | Past Simple: неправильные глаголы (went, bought, saw) |
| A1+ · 5 | a1p_w05_l09_did_didnt<br>a1p_w05_l10_describe_things | did / didn't; вопросы в прошлом: Where did you…? |
| A1+ · 6 | a1p_w06_l11_object_pronouns<br>a1p_w06_l12_phone_feelings | me / him / her / them; повторение Past Simple |
| A1+ · 7 | a1p_w07_l13_some_any<br>a1p_w07_l14_restaurant_order | some / any; исчисляемые и неисчисляемые |
| A1+ · 8 | a1p_w08_l15_must_mustnt<br>a1p_w08_l16_first_day_work | must / must not |
| A1+ · 9 | a1p_w09_l17_have_to<br>a1p_w09_l18_home_repairs | have to / don't have to |
| A1+ · 10 | a1p_w10_l19_could_you<br>a1p_w10_l20_adverbs_ly | Could you…?; наречия образа действия: quietly, quickly |
| A1+ · 11 | a1p_w11_l21_how_often<br>a1p_w11_l22_at_the_pharmacy | How often…?; once / twice a day |
| A1+ · 12 | a1p_w12_l23_too_enough<br>a1p_w12_l24_weather_plans | прилагательные и их порядок; too / enough |
| A1+ · 13 | a1p_w13_l25_past_review<br>a1p_w13_l26_application_form | повторение Past Simple в анкете и рассказе |
| A1+ · 14 | a1p_w14_l27_movement_prepositions<br>a1p_w14_l28_city_directions | предлоги движения: across, past, to; первое if |
| A1+ · 15 | a1p_w15_l29_if_will<br>a1p_w15_l30_travel_packing | реальное if: If…, I will… |
| A1+ · 16 | a1p_w16_l31_review_a1plus<br>a1p_w16_l32_picnic_seasons | повторение A1+: прошедшее время, must / have to, if |

## Карта ключевых зависимостей (проверять при построчном проходе)

- A1 1–5: существительные / be → определители и простые глаголы → вежливые просьбы → притяжательность → there is/are и количество.
- A1 6–9: Present Simple с I/you → 3-е лицо -s → местоположение и повелительное наклонение → do/does в вопросах.
- A1 10–14: частотность, like + -ing (последовательно, в соседних уроках) → здоровье и can/can't → don't/doesn't → объяснение причины → закрепление.
- A1+ 1–5: Present Continuous (только после A1) → was/were, there was/were → регулярный Past Simple → неправильные формы → did/didn't.
- A1+ 6–10: объектные местоимения → some/any → must/mustn't → have to / don't have to → вежливые просьбы и наречия.
- A1+ 11–16: частотность → too/enough → Past Simple в связном рассказе → направления и первое if → if + Present Simple с will в главной части → повторение.

Карта предварительная: фактическую первую встречу каждой конструкции во **всех диалогах, историях, JSON-тренажёрах и словаре** здесь ещё не проверили.

## Точно подтверждённые/обоснованные адресные изменения

| ID / место | Было | Стало и зачем |
|---|---|---|
| A1 урок 19, `contractions.note_ru` | `don't` трактовалось как «не гуляю (сейчас, обычно)» | Разведены регулярность Present Simple и процесс прямо сейчас; отдельный контраст `don't` / `never` с пояснением степени категоричности |
| EX-00106, A1 урок 19 | В объяснении допускалось `Sometimes I play the guitar`, но ключ имел только `I sometimes play the guitar` | Добавлен `accepted` для варианта с наречием в начале; неверное `I plays` не добавлено |
| EX-00058, A1 урок 11 | Объяснение допускало `At seven, I drink coffee`, ключ содержал только порядок со временем в конце | Добавлен `accepted` для исходного времени; неверное `I drinks` не добавлено |
| A1+ урок 3, `you were` | `you` объявлялось «всегда формой множественного числа» | Теперь объясняется, что адресат может быть один или несколько, но форма `were` одна для обоих контекстов |
| A1+ урок 4, `It was...` | «Без it по-английски нельзя» | Ограничено полным сообщением о впечатлении; оговорено существование коротких самостоятельных реплик |
| A1+ урок 21, `once/twice a day` | `a` механически переводился как «каждый», `once` — как «однажды» | Объяснена частота «раз / два раза за период», отдельное значение `once` и сравнение `twice a day` / `twice in one day` |
| A1+ урок 29, EX-00332 | `will` «только во второй части» | Привязано к **изучаемой модели реального условия**, без ложного запрета для всех предложений с if |

**Классы изменений:** 2 ошибки согласованности ключа и пояснения; 4 методически опасных обобщения/неверных смысловых акцента. Не утверждаем, что встретившиеся ранее конструкции грамматически ошибочны во всех контекстах.

## Источники редакторских решений

- Cambridge Dictionary, *Present simple or present continuous?*: https://dictionary.cambridge.org/us/grammar/british-grammar/present-simple-present-continuous
- Cambridge Dictionary, *Pronouns: personal*: https://dictionary.cambridge.org/us/grammar/british-grammar/pronouns-personal-i-me-you-him-it-they-
- Cambridge Dictionary, *Subject–verb agreement*: https://dictionary.cambridge.org/us/grammar/british-grammar/verb-agreement
- Внутренние механизмы проекта: `apps/drills/models.py` (`Exercise.is_correct`, `accepted`), `tests/test_grammar_answer_integrity.py`, `tests/test_a1_translation.py`.

## Проверки и степень достоверности

- **DONE, структурное чтение:** исходный SHA, инструкции агента, перечень 60 YAML, план 30 недель и работа ключей `accepted`.
- **DONE, ограниченный семантический просмотр:** выборочный поиск категоричных формулировок во всех 60 lesson YAML с ручным чтением релевантных фрагментов. Это НЕ полный построчный аудит.
- **DONE, реализация:** точечные исправления в 6 YAML; регрессионные проверки в `tests/test_grammar_answer_integrity.py` и `tests/test_a1_a1plus_semantic_regressions.py`.
- **BLOCKED в рабочем окружении:** локальный clone (нет DNS-доступа к github.com), запуск Django, `load_content`, `audit_course`, `uv run python manage.py test tests --parallel auto`, проверка страниц на 390 px. GitHub Actions проверяется отдельно; не подменять им ручной аудит.
- **Аудио:** сценарные реплики `seed_weeks/` и файлы звукозаписи не изменялись; реальное соответствие имеющейся озвучки тексту не проверялось.

## Что осталось для завершения исходного задания

1. Построчно прочитать и отредактировать все 60 уроков, сохранив контекст, проверив CEFR/лексические ограничения, порядок грамматики и ID.
2. Перекрёстно проверить все 30 недель `content/seed_weeks/`, 11 историй `content/seed_stories/`, словарь `content/seed_lexicon/`, `content/active_a1/`, шаблоны и программные подсказки.
3. Сверить каждый вопрос с эталоном, допустимыми альтернативами и механизмом проверки через реальный HTTP API; отдельно проверить произвольные ответы и пограничные случаи.
4. Запустить загрузку, `audit_course`, тесты и браузерный smoke test десктоп/390px; проверить аудио при изменении озвучиваемых реплик.
5. Только после полного сквозного прохода перевести работу из частичного статуса в выполненную; не считать наличие PR доказательством полноты.

Слияние в main не разрешено. Все следующие правки задачи следует делать **в этой ветке и одном PR**.
