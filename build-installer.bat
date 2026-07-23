@echo off
setlocal
cd /d "%~dp0"

call "%~dp0build-release.bat"
if errorlevel 1 goto :error

call :sign_file "%~dp0dist\Spicetify Manager\Spicetify Manager.exe"
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

call :sign_file "%~dp0installer-output\Spicetify-Manager-v2.3.1-Setup.exe"
if errorlevel 1 goto :error

echo.
echo Installer build complete:
echo %~dp0installer-output\Spicetify-Manager-v2.3.1-Setup.exe
if not defined SIGN_CERT_SHA1 echo Note: build is unsigned because SIGN_CERT_SHA1 was not set.
exit /b 0

:sign_file
if not defined SIGN_CERT_SHA1 exit /b 0
set "SIGNTOOL_EXE=%SIGNTOOL_PATH%"
if not defined SIGNTOOL_EXE (
    for /f "delims=" %%I in ('where signtool.exe 2^>nul') do (
        if not defined SIGNTOOL_EXE set "SIGNTOOL_EXE=%%I"
    )
)
if not defined SIGNTOOL_EXE (
    echo SignTool was not found. Install the Windows SDK or set SIGNTOOL_PATH.
    exit /b 1
)
if not defined SIGN_TIMESTAMP_URL set "SIGN_TIMESTAMP_URL=http://timestamp.digicert.com"
echo Signing %~1
"%SIGNTOOL_EXE%" sign /sha1 "%SIGN_CERT_SHA1%" /fd SHA256 /tr "%SIGN_TIMESTAMP_URL%" /td SHA256 /v "%~1"
if errorlevel 1 exit /b 1
"%SIGNTOOL_EXE%" verify /pa /v "%~1"
exit /b %errorlevel%

:error
echo.
echo The installer build failed.
exit /b 1
