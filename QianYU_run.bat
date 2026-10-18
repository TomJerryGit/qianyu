@echo off
setlocal
cd /d "%~dp0"

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "QT_QPA_FONTDIR=%WINDIR%\Fonts"

set "VENV_PY=%~dp0tools\venv311\Scripts\python.exe"
set "APP=%~dp0run_dev.py"

if not exist "%APP%" goto no_app
if exist "%VENV_PY%" goto use_venv
set "PY=python"
goto run_app

:use_venv
set "PY=%VENV_PY%"

:run_app
"%PY%" -X utf8 -u "%APP%" %*
set "CODE=%ERRORLEVEL%"
if "%CODE%"=="0" goto done
echo.
echo [QianYu] exit code: %CODE%
pause

:done
exit /b %CODE%

:no_app
echo [QianYu] run_dev.py not found: %APP%
pause
exit /b 1
