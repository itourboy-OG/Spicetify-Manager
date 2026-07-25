@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    echo Preparing Spicetify Manager for first use...
    python -m venv "%~dp0.venv"
    if errorlevel 1 goto :setup_error
)

"%PYTHON_EXE%" -c "import PySide6" >nul 2>&1
if errorlevel 1 (
    echo Installing Qt interface components...
    "%PYTHON_EXE%" -m pip install --disable-pip-version-check -r "%~dp0requirements.txt"
    if errorlevel 1 goto :setup_error
)

"%PYTHON_EXE%" "%~dp0spicetify_qt.py"
if errorlevel 1 (
    echo.
    echo Spicetify Manager exited with an error.
)
pause
exit /b

:setup_error
echo.
echo The Spicetify Manager setup could not be completed.
echo Check your internet connection and Python installation, then try again.
pause
exit /b 1
