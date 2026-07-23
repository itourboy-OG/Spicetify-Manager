@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    python -m venv "%~dp0.venv"
    if errorlevel 1 goto :error
)

"%PYTHON_EXE%" -m pip install --disable-pip-version-check -r "%~dp0requirements.txt"
if errorlevel 1 goto :error

"%PYTHON_EXE%" -m pip install --disable-pip-version-check "pyinstaller==6.21.0"
if errorlevel 1 goto :error

"%PYTHON_EXE%" -m PyInstaller --noconfirm --clean "%~dp0SpicetifyManager.spec"
if errorlevel 1 goto :error

echo.
echo Build complete:
echo %~dp0dist\Spicetify Manager\Spicetify Manager.exe
exit /b 0

:error
echo.
echo The release build failed.
exit /b 1
