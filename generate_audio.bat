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
rem Неполный файл после оборванной загрузки удаляем, чтобы скачать заново.
for %%F in ("models\kokoro\kokoro-v1.0.onnx") do if exist "%%~F" if %%~zF LSS 300000000 (
  echo Файл модели неполный ^(%%~zF байт^), скачаю заново.
  del "%%~F"
)
for %%F in ("models\kokoro\voices-v1.0.bin") do if exist "%%~F" if %%~zF LSS 27000000 (
  echo Файл голосов неполный ^(%%~zF байт^), скачаю заново.
  del "%%~F"
)
if exist "models\kokoro\kokoro-v1.0.onnx" goto have_model
echo [2/4] Скачиваю модель голосов, около 310 МБ. Это делается один раз...
powershell -NoProfile -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx' -OutFile 'models\kokoro\kokoro-v1.0.onnx.part'"
if not %errorlevel%==0 goto fail_download
for %%F in ("models\kokoro\kokoro-v1.0.onnx.part") do if %%~zF LSS 300000000 goto fail_download
move /y "models\kokoro\kokoro-v1.0.onnx.part" "models\kokoro\kokoro-v1.0.onnx" >nul
:have_model
if exist "models\kokoro\voices-v1.0.bin" goto have_voices
powershell -NoProfile -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin' -OutFile 'models\kokoro\voices-v1.0.bin.part'"
if not %errorlevel%==0 goto fail_download
for %%F in ("models\kokoro\voices-v1.0.bin.part") do if %%~zF LSS 27000000 goto fail_download
move /y "models\kokoro\voices-v1.0.bin.part" "models\kokoro\voices-v1.0.bin" >nul
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
