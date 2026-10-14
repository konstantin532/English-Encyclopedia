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

if not exist "models\kokoro" mkdir "models\kokoro"
if exist "models\kokoro\kokoro-v1.0.onnx" goto have_model
echo [2/4] Скачиваю модель голосов, около 310 МБ. Это делается один раз...
powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx' -OutFile 'models\kokoro\kokoro-v1.0.onnx'"
if not %errorlevel%==0 goto fail
:have_model
if exist "models\kokoro\voices-v1.0.bin" goto have_voices
powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin' -OutFile 'models\kokoro\voices-v1.0.bin'"
if not %errorlevel%==0 goto fail
:have_voices
echo [2/4] Модель на месте.

echo [3/4] Озвучиваю истории по ролям...
uv run python scripts\generate_story_audio.py --all
if not %errorlevel%==0 goto fail

echo [4/4] Обновляю сайт...
uv run python manage.py load_content
if not %errorlevel%==0 goto fail
echo.
echo Готово. Запустите start.bat и откройте Истории — История 1.
goto end

:fail
echo.
echo Озвучка остановлена из-за ошибки выше. Пришлите текст ошибки Claude.
:end
echo.
pause
