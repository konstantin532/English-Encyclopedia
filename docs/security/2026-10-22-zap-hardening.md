# ZAP hardening — 22 октября 2026

Исходная версия: main, 6e96df2 (уже включает django-axes 8.3.1).

## Причины ошибки входа

1. Вошедший пользователь отправляет POST /accounts/login/ с next=/accounts/login/.
   Стандартный LoginView с redirect_authenticated_user=True выбрасывает ValueError
   о цикле перенаправления. Регрессионный тест воспроизвёл 500 до исправления.
   EmailLoginView теперь игнорирует next, ведущий на ту же страницу входа;
   внешние адреса по-прежнему проверяет стандартный механизм Django.
2. AuthenticationForm выставляет max_length=254 после создания EmailField,
   однако валидатор поля остаётся с исходным пределом EmailField (320).
   Поэтому синтаксически корректный email из 260 символов проходит проверку
   и может попасть в axes.AccessAttempt.username с пределом VARCHAR(255).
   PostgreSQL отвергнет такую запись; SQLite не воспроизводит ограничение длины.
   Тест до исправления доказал отсутствие ValidationError, после — ошибку поля
   username и отсутствие записи axes. Теперь предел задан при создании поля.
3. Unicode lower() может увеличить строку: проверенный адрес из 164 символов
   после нормализации превращался в 256. Валидаторы повторяются для нормализованного
   адреса до authenticate. Этот случай также прошёл цикл RED → GREEN.

Остальные гостевые сценарии не воспроизвели 500 на исходном main: блокировка после
5 ошибок, пустые/не-email/10000 символов, повторяющиеся поля username, внешние и
кривые next, лишние поля, отсутствие CSRF. Они закреплены тестами; источник
конкретного локального ZAP-ответа без его HTTP-транзакции не приписывается axes.
Регистрация с явным ModelBackend и axes_reset сохранены и проверяются.

## Content-Security-Policy

Выбран django-csp >=4,<5 (lock: 4.0), потому что он поддерживает генерацию nonce
на запрос и два режима заголовка. Свой middleware потребовал бы самостоятельно
поддерживать этот жизненный цикл. Django 5.2 не предоставляет встроенную CSP.

Только production подключает CSPMiddleware после SecurityMiddleware, перед
WhiteNoise и axes; axes остаётся последним. Local и test не включают CSP по
умолчанию. Два синхронных скрипта в head base.html используют request.csp_nonce,
без defer и без unsafe-inline в script-src. json_script не изменён.

Политика (nonce меняется на каждом ответе, где используется):

```text
default-src 'self'; script-src 'self' 'nonce-<random>';
style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self';
media-src 'self' blob:; connect-src 'self'; object-src 'none';
base-uri 'self'; form-action 'self'; frame-ancestors 'none'
```

style-src разрешает существующие style-атрибуты и изменения GSAP. media-src blob:
необходим для локального воспроизведения записи MediaRecorder. Внешние CDN,
unsafe-eval, strict-dynamic и исключения для admin не добавлены.

DJANGO_CSP_REPORT_ONLY=1 в окружении процесса выбирает исключительно
Content-Security-Policy-Report-Only; 0 или отсутствие переменной — enforce.
В режиме наблюдения браузер сообщает о нарушениях в консоли; серверный сборщик
отчётов и внешние адреса отправки не добавлены. При смене режима нужен перезапуск
Django-процесса. .env в этой задаче не изменяется.

## Страницы ошибок

404.html и 500.html автономны, используют локальные CSS и обычные ссылки.
500 не расширяет base.html, не использует URL reverse, static manifest или
request context processors и не выполняет запросы к БД. Исключения, traceback
и технические данные пользователю не показываются. SimpleTestCase дополнительно
проверяет рендер при отказе reverse, site context и staticfiles storage.

## Браузерная проверка

Временный localhost-стенд использует настоящую production CSP и отдельную
work/zap-preview.sqlite3. Production-база и db.sqlite3 проекта не меняются.
Проверены главная, неделя A1/1, урок a1-verb-be (speech studio), история 1,
стихотворение 1, cafe lab, cafe mission, практика A1/2, dashboard после входа,
admin (обзор и список уроков), страницы 404 и 500. В проверенных консолях CSP
нарушений нет. Страница 500 проверена также на ширине 390 px и с клавиатуры.

Обычный плеер недели воспроизвёл локальную синтетическую WAV-дорожку; таймер
продвинулся и динамический --audio-progress изменился. Тестовый манифест записан
только в preview-базу. Запись на неделе и уроке проверена через синтетический
MediaStream: настоящий MediaRecorder создал blob, браузер его декодировал и
воспроизвёл (readyState=4, без ошибки), затем запись удалена. Звук настоящего
микрофона не захватывался. Это проверка совместимости CSP, не качества озвучки.

## Проверки

Связанные тесты: tests.test_login_zap, tests.test_login_protection,
tests.test_csp, tests.test_error_pages, AccountTests, test_motion_system,
test_public_metadata, test_admin_studio. Полный набор запускается один раз
перед PR: uv run python manage.py test tests --parallel auto
--settings=config.settings.test. Точные итоговые результаты указаны в PR.

Lib/ и Scripts/ в корне игнорируются, не удаляются. .env, db.sqlite3,
db.sqlite3.before-zap, zap-report.html и security-report.txt не включаются в PR.
SECURE_HSTS_INCLUDE_SUBDOMAINS и SECURE_HSTS_PRELOAD не включаются.

Источники: [django-csp 4 configuration](https://django-csp.readthedocs.io/en/latest/configuration.html),
[nonce](https://django-csp.readthedocs.io/en/latest/nonce.html),
[Django json_script](https://docs.djangoproject.com/en/5.2/ref/templates/builtins/#json-script),
[Django 500 view](https://docs.djangoproject.com/en/5.2/ref/views/#the-500-server-error-view).
