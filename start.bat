@echo off
chcp 866 >nul 2>&1
setlocal enabledelayedexpansion
cd /d "%~dp0"

title ДКП-бот

echo ============================================
echo   ДКП-бот - договор купли-продажи авто
echo ============================================
echo.

rem --- 1. Ищем рабочий Python (заглушка Microsoft Store не подходит) ---
if exist ".venv\Scripts\python.exe" goto have_venv

set "PYEXE="
for %%P in (
    "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe"
    "%LOCALAPPDATA%\Python\pythoncore-3.13-64\python.exe"
    "%LOCALAPPDATA%\Python\pythoncore-3.12-64\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "C:\Python314\python.exe"
    "C:\Python313\python.exe"
    "C:\Python312\python.exe"
    "C:\Python311\python.exe"
) do (
    if exist %%P if not defined PYEXE set "PYEXE=%%~P"
)

if not defined PYEXE (
    for /f "delims=" %%P in ('where python 2^>nul') do (
        if not defined PYEXE (
            echo %%P | find /i "WindowsApps" >nul || set "PYEXE=%%P"
        )
    )
)

if not defined PYEXE (
    echo [ОШИБКА] Python не найден.
    echo.
    echo Установите Python 3.11 или новее с сайта python.org
    echo При установке ОБЯЗАТЕЛЬНО отметьте "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

echo Найден Python: !PYEXE!
echo Создаю виртуальное окружение (один раз, может занять минуту)...
"!PYEXE!" -m venv .venv
if errorlevel 1 (
    echo [ОШИБКА] Не удалось создать окружение.
    pause
    exit /b 1
)

echo Устанавливаю зависимости...
".venv\Scripts\python.exe" -m pip install --upgrade pip -q
".venv\Scripts\python.exe" -m pip install -r requirements.txt -q
if errorlevel 1 (
    echo [ОШИБКА] Не удалось установить зависимости.
    pause
    exit /b 1
)

:have_venv

rem --- 2. Проверяем .env и токен ---
if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo.
    echo Создан файл .env
    echo Откроется блокнот - вставьте токен от @BotFather в строку BOT_TOKEN=
    echo Сохраните файл ^(Ctrl+S^) и закройте блокнот.
    echo.
    pause
    notepad .env
)

for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
    if /i "%%A"=="BOT_TOKEN" set "TOKEN=%%B"
)

if not defined TOKEN (
    echo [ОШИБКА] В файле .env не указан BOT_TOKEN.
    echo Откройте .env и добавьте строку: BOT_TOKEN=ваш_токен
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Бот запускается. Не закрывайте это окно!
echo   Остановить: Ctrl+C или закрыть окно.
echo ============================================
echo.

".venv\Scripts\python.exe" run.py

echo.
echo ============================================
echo   Бот остановлен.
echo ============================================
pause
