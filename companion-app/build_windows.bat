@echo off
rem Builds Quick-Key for Windows in one go:
rem   1. a private Python environment (.venv) with everything the app needs
rem   2. dist\QuickKey.exe            (the app, with Python bundled inside)
rem   3. installer\Output\QuickKeySetup.exe   (only if Inno Setup is installed)
rem
rem Double-click it, or run it from a terminal opened in this folder.
rem Needs Python 3.10+ (installed with "Add python.exe to PATH" ticked).

setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo.
    echo Python was not found. Install it from https://www.python.org/downloads/
    echo and tick "Add python.exe to PATH" on the first screen, then run this again.
    goto :fail
)

echo.
echo === 1/3  Setting up the build environment ===
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
    if errorlevel 1 goto :fail
)
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :fail
".venv\Scripts\python.exe" -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto :fail

echo.
echo === 2/3  Building dist\QuickKey.exe ===
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean quickkey.spec
if errorlevel 1 goto :fail
if not exist "dist\QuickKey.exe" goto :fail

echo.
echo === 3/3  Building the installer ===
set "ISCC="
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if "%ISCC%"=="" (
    echo Inno Setup is not installed, so no installer was made.
    echo The app itself is ready: dist\QuickKey.exe
    echo To also build QuickKeySetup.exe, install Inno Setup 6 from
    echo https://jrsoftware.org/isdl.php and run this again.
    goto :done
)
"%ISCC%" "installer\quickkey_installer.iss"
if errorlevel 1 goto :fail

:done
echo.
echo ===================== DONE =====================
echo   App:        %~dp0dist\QuickKey.exe
if exist "installer\Output\QuickKeySetup.exe" echo   Installer:  %~dp0installer\Output\QuickKeySetup.exe
echo ================================================
pause
exit /b 0

:fail
echo.
echo ===================== BUILD FAILED =====================
echo Scroll up for the first error message, and send it along.
pause
exit /b 1
