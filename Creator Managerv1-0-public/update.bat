@echo off
REM ============================================================
REM   Creator Manager v1.0 Beta — Auto-updater
REM   Checks GitHub releases for new versions and updates.
REM ============================================================
setlocal enabledelayedexpansion

cd /d "%~dp0"

REM ═══════════════════════════════════════════════════════════
REM  EDIT THIS: Set your GitHub repository (USER/REPO):
REM  Example: set REPO=johndoe/creator-manager
REM ═══════════════════════════════════════════════════════════
set REPO=https://github.com/juanvarlozada-coder/Creator-Manager
REM ═══════════════════════════════════════════════════════════

set VERSION=v1.0-beta

echo.
echo =============================================
echo   Creator Manager - Updater
echo   Current version: %VERSION%
echo =============================================
echo.

where powershell >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] PowerShell not found. Updates require PowerShell.
    pause
    exit /b 1
)

echo Checking GitHub for updates (repo: %REPO%)...
echo.

REM ── Fetch latest release info via PowerShell (single call) ──
for /f "delims=" %%a in ('
    powershell -ExecutionPolicy Bypass -Command ^
        "$u='https://api.github.com/repos/%REPO%/releases/latest';" ^
        "$c=New-Object System.Net.WebClient;" ^
        "$c.Headers.Add('User-Agent','Creator-Manager-Updater');" ^
        "try { $j=$c.DownloadString($u); $d=$j^|ConvertFrom-Json;" ^
        "if ($d.tag_name -gt '%VERSION%') {" ^
        "  Write-Host ('UPDATE^|'+$d.tag_name+'^|'+$d.zipball_url)" ^
        "} else { Write-Host 'CURRENT' } }" ^
        "catch { Write-Host ('ERROR^|'+$_.Exception.Message) }"
') do set "result=%%a"

REM Parse result
for /f "tokens=1,2,* delims=|" %%a in ("!result!") do (
    set "status=%%a"
    set "latest_ver=%%b"
    set "zip_url=%%c"
)

if "!status!"=="CURRENT" (
    echo You already have the latest version (%VERSION%).
    echo.
    pause
    exit /b 0
)
if "!status!"=="ERROR" (
    echo Could not check for updates.
    echo - Check your internet connection.
    echo - Verify REPO is set correctly in update.bat.
    echo.
    pause
    exit /b 1
)
if "!status!"=="UPDATE" (
    echo New version found: !latest_ver!
    echo.
    set /p confirm="Download and install now? (Y/N): "
    if /i "!confirm!"=="Y" (
        echo.
        echo Downloading update...
        set TEMP_DIR=%TEMP%\creator-manager-update
        set ZIP_FILE=%TEMP%\creator-manager-update.zip
        if exist "!TEMP_DIR!" rmdir /s /q "!TEMP_DIR!"
        if exist "!ZIP_FILE!" del /q "!ZIP_FILE!"

        powershell -ExecutionPolicy Bypass -Command ^
            "$c=New-Object System.Net.WebClient;" ^
            "$c.Headers.Add('User-Agent','Creator-Manager-Updater');" ^
            "try { $c.DownloadFile('!zip_url!', '!ZIP_FILE!');" ^
            "Expand-Archive -Path '!ZIP_FILE!' -DestinationPath '!TEMP_DIR!' -Force;" ^
            "$src=Get-ChildItem -Path '!TEMP_DIR!' -Directory ^| Select-Object -First 1;" ^
            "if ($src) { Copy-Item -Recurse -Force \"$($src.FullName)\\*\" -Destination '%CD%';" ^
            "Write-Host 'OK' } else { Write-Host 'FAIL' } }" ^
            "catch { Write-Host 'ERROR: '+$_.Exception.Message }"

        echo.
        echo Update installed! Please restart the application.
    ) else (
        echo Update cancelled.
    )
)

echo.
pause
exit /b 0
