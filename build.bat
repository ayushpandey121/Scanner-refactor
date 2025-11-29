@echo off
setlocal EnableExtensions EnableDelayedExpansion

echo ========================================
echo Building and Publishing Rice Quality App
echo ========================================

REM Check if GH_TOKEN is set
if "%GH_TOKEN%"=="" (
    echo ERROR: GH_TOKEN environment variable is not set!
    echo Please set your GitHub token:
    echo   set GH_TOKEN=your_github_token_here
    echo.
    echo Or run this script with: build-and-publish.bat YOUR_TOKEN
    pause
    exit /b 1
)

REM Allow passing token as argument
if not "%1"=="" (
    set "GH_TOKEN=%1"
    echo Using GitHub token from argument
)

pushd "%~dp0"
set "ROOT_DIR=%CD%"
set "BACKEND_DIR=%ROOT_DIR%\rice_webapp_backend"
set "FRONTEND_DIR=%ROOT_DIR%\rice_webapp_frontend"
set "RELEASE_DIR=%FRONTEND_DIR%\release"

REM Prefer the project virtualenv one level above this folder if it exists
if exist "%ROOT_DIR%\..\venv\Scripts\python.exe" (
    set "PYTHON_CMD=%ROOT_DIR%\..\venv\Scripts\python.exe"
) else if exist "%ROOT_DIR%\venv\Scripts\python.exe" (
    set "PYTHON_CMD=%ROOT_DIR%\venv\Scripts\python.exe"
) else (
    set "PYTHON_CMD=python"
)

echo Using Python interpreter: %PYTHON_CMD%

echo.
echo Step 1: Installing Python dependencies...
"%PYTHON_CMD%" -m pip install --upgrade pip
if errorlevel 1 goto :error

"%PYTHON_CMD%" -m pip install -r "%BACKEND_DIR%\requirements.txt"
if errorlevel 1 goto :error

"%PYTHON_CMD%" -m pip install pyinstaller pywin32
if errorlevel 1 goto :error

echo.
echo Step 2: Building backend executable...
"%PYTHON_CMD%" "%BACKEND_DIR%\build_backend.py"
if errorlevel 1 goto :error

if not exist "%BACKEND_DIR%\dist" (
    echo Backend dist folder was not created. Aborting.
    goto :error
)

echo Refreshing backend bundle for Electron...
if exist "%FRONTEND_DIR%\backend-dist" rmdir /S /Q "%FRONTEND_DIR%\backend-dist"
mkdir "%FRONTEND_DIR%\backend-dist"
xcopy "%BACKEND_DIR%\dist\*" "%FRONTEND_DIR%\backend-dist\" /E /I /Y >nul
if errorlevel 1 goto :error

echo.
echo Step 3: Building scanner service executable...
if exist "%FRONTEND_DIR%\scanner-dist" rmdir /S /Q "%FRONTEND_DIR%\scanner-dist"
if exist "%FRONTEND_DIR%\build\scanner" rmdir /S /Q "%FRONTEND_DIR%\build\scanner"
"%PYTHON_CMD%" -m PyInstaller ^
    "%FRONTEND_DIR%\scanner_service.py" ^
    --name scanner_service ^
    --onedir ^
    --noconsole ^
    --clean ^
    --distpath "%FRONTEND_DIR%\scanner-dist" ^
    --workpath "%FRONTEND_DIR%\build\scanner" ^
    --specpath "%FRONTEND_DIR%" ^
    --hidden-import flask ^
    --hidden-import flask_cors ^
    --hidden-import win32com.client ^
    --hidden-import pythoncom
if errorlevel 1 goto :error

echo.
echo Step 4: Installing frontend dependencies...
cd /d "%FRONTEND_DIR%"
call npm install
if errorlevel 1 goto :error

echo.
echo Step 5: Building and Publishing Electron app...
echo This will create a GitHub Release and upload the installer
call npm run electron:publish
if errorlevel 1 goto :error

echo.
echo ========================================
echo Build and Publish Complete!
echo ========================================
echo Your app has been published to GitHub Releases
echo Installer is in: %RELEASE_DIR%
echo.
echo Next steps:
echo 1. Go to your GitHub repository releases page
echo 2. Edit the release notes if needed
echo 3. Users can now download and install the update
pause
popd
exit /b 0

:error
echo.
echo Build failed (exit code %errorlevel%).
pause
popd
exit /b %errorlevel%