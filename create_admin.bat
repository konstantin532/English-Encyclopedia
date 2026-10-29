@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "PATH=%USERPROFILE%\.local\bin;%PATH%"
echo Создание администратора (вход в http://127.0.0.1:8000/admin/)
echo Сначала один раз запустите start.bat.
echo.
uv run python manage.py createsuperuser
echo.
pause
