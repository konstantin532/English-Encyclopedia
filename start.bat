@echo off
chcp 65001 >nul
title English Encyclopedia
cd /d "%~dp0"

echo.
echo === English Encyclopedia: запуск ===
echo.

rem --- 0. Свежие изменения с GitHub (если папка связана через connect_github.bat) ---
if not exist ".git" goto no_git
where git >nul 2>nul
if not %errorlevel%==0 goto no_git
echo [0/5] Скачиваю свежие изменения с GitHub...
git pull --ff-only
if not %errorlevel%==0 echo Не удалось скачать изменения, запускаю то, что есть на компьютере.
goto uv_step
:no_git
echo [0/5] Папка не связана с GitHub: запустите один раз connect_github.bat.
:uv_step

rem --- 1. uv (менеджер Python) ---
where uv >nul 2>nul
if %errorlevel%==0 goto have_uv
if exist "%USERPROFILE%\.local\bin\uv.exe" goto add_path
echo [1/5] uv не найден, устанавливаю...
powershell -NoProfile -ExecutionPolicy ByPass -Command "irm https://astral.sh/uv/install.ps1 | iex"
:add_path
set "PATH=%USERPROFILE%\.local\bin;%PATH%"
where uv >nul 2>nul
if not %errorlevel%==0 goto fail_uv
:have_uv
echo [1/5] uv на месте.

rem --- 2. Зависимости (при первом запуске uv сам скачает Python) ---
echo [2/5] Устанавливаю зависимости...
uv sync
if not %errorlevel%==0 goto fail

rem --- 3. Файл настроек ---
if exist ".env" goto have_env
copy ".env.example" ".env" >nul
echo [3/5] Создан файл .env с настройками по умолчанию.
goto migrate
:have_env
echo [3/5] Файл .env уже есть.

rem --- 4. База данных и учебный контент ---
:migrate
echo [4/5] Обновляю базу и загружаю уроки...
uv run python manage.py migrate -v0
if not %errorlevel%==0 goto fail
uv run python manage.py load_content
if not %errorlevel%==0 goto fail

rem --- 5. Сервер ---
echo [5/5] Запускаю сайт: http://127.0.0.1:8000
echo Чтобы остановить сайт, закройте это окно или нажмите Ctrl+C.
echo.
start "" /b cmd /c "timeout /t 3 >nul & start http://127.0.0.1:8000"
uv run python manage.py runserver 127.0.0.1:8000
goto end

:fail_uv
echo.
echo Не удалось установить uv. Установите вручную: https://docs.astral.sh/uv/ и запустите этот файл снова.
goto end

:fail
echo.
echo Запуск остановлен из-за ошибки выше. Пришлите текст ошибки Claude.

:end
echo.
pause
