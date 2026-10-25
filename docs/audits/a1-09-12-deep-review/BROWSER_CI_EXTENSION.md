# Дополнение реальной браузерной проверки

author: Codex; reviewed_by: existing CI route inspection and pending new Chromium execution; verification_status: technical_review; date:2026-10-25
source_notes: existing Atlas workflow and actual lesson templates/routes; no production code or CI configuration changes

Исходная Atlas acceptance успешно прошла на67785cb, но проверяет home/catalog/week13 и загрузку14обложек при390px. Она не подтверждает чтение изменённых lesson9–12/story2/poem3. Дополнен scripts/verify_atlas.cjs: реальные12сочетаний страниц/ширины1440и390, reduced-motion, проверка конечного route/заголовка/overflow, семь видимых слоёв и открытие трёхшагового пояснения клавиатурой. Снимки обоих состояний сохраняются в существующий artifact. Все прежние before/after geometry checks оставлены неизменными. Это дополнительная поведенческая проверка; она не заменяет человеческую оценку понятности и прослушивание аудио. Локальная установка Chromium всё ещё BLOCKED; новый результат берётся из CI этого коммита, не из предыдущего запуска.
