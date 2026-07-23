@echo off
setlocal
cd /d "%~dp0"

call "%~dp0build-release.bat"
if errorlevel 1 goto :error

set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
    echo.
    echo Inno Setup 6 was not found.
    echo Install it with: winget install --id JRSoftware.InnoSetup --exact
    goto :error
)

"%ISCC%" "%~dp0SpicetifyManager.iss"
if errorlevel 1 goto :error

echo.
echo Installer build complete:
echo %~dp0installer-output\Spicetify-Manager-v2.2.0-Setup.exe
exit /b 0

:error
echo.
echo The installer build failed.
exit /b 1
