@echo off
chcp 65001 >nul
title English Encyclopedia
set "START_EXIT=0"
cd /d "%~dp0"

echo.
echo === English Encyclopedia: запуск ===
echo.


rem --- 1. uv (менеджер Python) ---
where uv >nul 2>nul
if %errorlevel%==0 goto have_uv
if exist "%USERPROFILE%\.local\bin\uv.exe" goto add_path
echo [1/6] uv не найден, устанавливаю...
powershell -NoProfile -ExecutionPolicy ByPass -Command "irm https://astral.sh/uv/install.ps1 | iex"
:add_path
set "PATH=%USERPROFILE%\.local\bin;%PATH%"
where uv >nul 2>nul
if not %errorlevel%==0 goto fail_uv
:have_uv
echo [1/6] uv на месте.

echo [2/6] Проверяю версию сайта и порт 8000...
uv run python scripts/local_start.py sync
if not %errorlevel%==0 goto fail


rem --- 2. Зависимости (при первом запуске uv сам скачает Python) ---
echo [3/6] Устанавливаю зависимости...
uv sync
if not %errorlevel%==0 goto fail

rem --- 3. Файл настроек ---
if exist ".env" goto have_env
copy ".env.example" ".env" >nul
echo [4/6] Создан файл .env с настройками по умолчанию.
goto migrate
:have_env
echo [4/6] Файл .env уже есть.

rem --- 4. База данных и учебный контент ---
:migrate
echo [5/6] Обновляю базу и загружаю уроки...
uv run python manage.py migrate -v0
if not %errorlevel%==0 goto fail
uv run python manage.py load_content --preserve-admin-edits
if not %errorlevel%==0 goto fail

rem --- 5. Сервер ---
echo [6/6] Запускаю сайт: http://127.0.0.1:8000
echo Чтобы остановить сайт, закройте это окно или нажмите Ctrl+C.
echo.
uv run python scripts/local_start.py serve
if not %errorlevel%==0 goto fail
goto end

:fail_uv
set "START_EXIT=1"
echo.
echo Не удалось установить uv. Установите вручную: https://docs.astral.sh/uv/ и запустите этот файл снова.
goto end

:fail
set "START_EXIT=1"
echo.
echo Запуск остановлен из-за ошибки выше. Пришлите текст ошибки Claude.

:end
echo.
pause
exit /b %START_EXIT%
