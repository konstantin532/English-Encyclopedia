@echo off
chcp 65001 >nul
title English Encyclopedia — подключение к GitHub
cd /d "%~dp0"

echo.
echo === Подключение папки к GitHub ===
echo Репозиторий: https://github.com/konstantin532/English-Encyclopedia
echo.

where git >nul 2>nul
if %errorlevel%==0 goto have_git
echo Git не установлен. Устанавливаю через winget...
winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements
echo.
echo Закройте это окно и запустите connect_github.bat ещё раз — чтобы Windows увидела Git.
goto end

:have_git
if exist ".git" goto already
git init -b main
git remote add origin https://github.com/konstantin532/English-Encyclopedia.git
:already
git fetch origin main
if not %errorlevel%==0 goto fail
rem Файлы проекта становятся версией из GitHub. Не тронуты: .env, база db.sqlite3,
rem модель голосов models\ и озвучка static\audio\ — они не хранятся в GitHub.
git reset --hard origin/main
if not %errorlevel%==0 goto fail
git branch --set-upstream-to=origin/main main >nul 2>nul
echo.
git log --oneline -3
echo.
echo Готово: папка связана с GitHub. Скиллы появились в .claude\skills.
goto end

:fail
echo.
echo Не получилось. Пришлите Claude текст ошибки выше.
:end
echo.
pause
