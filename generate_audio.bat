@echo off
chcp 65001 >nul
title English Encyclopedia — озвучка
cd /d "%~dp0"
set "PATH=%USERPROFILE%\.local\bin;%PATH%"

echo.
echo === Озвучка историй нейросетевыми голосами (Kokoro) ===
echo.
echo [1/4] Ставлю пакеты для синтеза речи...
uv sync --group audio
if not %errorlevel%==0 goto fail

echo [2/4] Проверяю модель и голоса, повреждённые файлы скачаю заново...
uv run python scripts\prepare_audio_models.py
if not %errorlevel%==0 goto fail

echo [3/4] Озвучиваю истории по ролям...
uv run python scripts\generate_story_audio.py --all
if not %errorlevel%==0 goto fail

echo [4/4] Обновляю сайт...
uv run python manage.py load_content
if not %errorlevel%==0 goto fail
echo.
echo Готово. Запустите start.bat и откройте Истории — История 1.
goto end

:fail_download
echo.
echo Загрузка модели оборвалась. Проверьте интернет и запустите generate_audio.bat ещё раз — неполный файл скачается заново.
del "models\kokoro\*.part" 2>nul
goto end

:fail
echo.
echo Озвучка остановлена из-за ошибки выше. Пришлите текст ошибки Claude.
:end
echo.
pause
