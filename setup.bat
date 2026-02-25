@echo off
cd /d "%~dp0"

echo.
echo ============================================================
echo Open Video Transcribe - Installation
echo ============================================================
echo.
echo Python 3.11, 3.12, or 3.13 is required.
echo.

:menu
echo Select Python version:
echo   [1] Python 3.12 (py -3.12 or common paths)
echo   [2] Python 3.11 (py -3.11 or common paths)
echo   [3] Default (python from PATH)
echo   [4] Enter custom path
echo   [5] Search for Python 3.11/3.12 on this computer
echo   [0] Auto (try 3.12, then 3.11, then default)
echo.
set /p choice="Enter choice [0-5] (default 0): "
if "%choice%"=="" set choice=0

if "%choice%"=="0" goto auto
if "%choice%"=="1" goto use312
if "%choice%"=="2" goto use311
if "%choice%"=="3" goto use_default
if "%choice%"=="4" goto use_custom
if "%choice%"=="5" goto search_python
goto menu

:auto
echo.
echo Auto-selecting Python...
where py >nul 2>&1
if %errorlevel% equ 0 (
    py -3.12 -c "import sys; exit(0)" 2>nul
    if %errorlevel% equ 0 (
        echo Using Python 3.12 (via py launcher)
        py -3.12 install.py
        goto end
    )
)
where py >nul 2>&1
if %errorlevel% equ 0 (
    py -3.11 -c "import sys; exit(0)" 2>nul
    if %errorlevel% equ 0 (
        echo Using Python 3.11 (via py launcher)
        py -3.11 install.py
        goto end
    )
)
call :find_python312
if defined PY312_PATH (
    echo Using Python 3.12: %PY312_PATH%
    "%PY312_PATH%" install.py
    goto end
)
call :find_python311
if defined PY311_PATH (
    echo Using Python 3.11: %PY311_PATH%
    "%PY311_PATH%" install.py
    goto end
)
echo Python Launcher (py) not found or no 3.11/3.12 installed. Trying default...
goto use_default

:use312
echo.
where py >nul 2>&1
if %errorlevel% equ 0 (
    py -3.12 -c "import sys; exit(0)" 2>nul
    if %errorlevel% equ 0 (
        py -3.12 install.py
        goto end
    )
)
call :find_python312
if defined PY312_PATH (
    "%PY312_PATH%" install.py
    goto end
)
echo Error: Python 3.12 not found.
echo.
echo Try option [4] to enter path, or option [5] to search for Python.
pause
exit /b 1

:use311
echo.
where py >nul 2>&1
if %errorlevel% equ 0 (
    py -3.11 -c "import sys; exit(0)" 2>nul
    if %errorlevel% equ 0 (
        py -3.11 install.py
        goto end
    )
)
call :find_python311
if defined PY311_PATH (
    "%PY311_PATH%" install.py
    goto end
)
echo Error: Python 3.11 not found. Try option [4] with path to python.exe
pause
exit /b 1

:use_default
echo.
python install.py
goto end

:use_custom
echo.
set /p py_path="Enter full path to python.exe (e.g. C:\Python312\python.exe): "
if "%py_path%"=="" (
    echo No path entered.
    goto menu
)
if not exist "%py_path%" (
    echo File not found: %py_path%
    pause
    goto menu
)
"%py_path%" install.py
goto end

:search_python
echo.
echo Searching common locations for Python 3.11 and 3.12...
powershell -NoProfile -Command "$paths = @('%%LocalAppData%%\\Programs\\Python\\Python312\\python.exe', '%%LocalAppData%%\\Programs\\Python\\Python311\\python.exe', 'C:\\Python312\\python.exe', 'C:\\Python311\\python.exe', '%%ProgramFiles%%\\Python312\\python.exe', '%%ProgramFiles%%\\Python311\\python.exe', '%%UserProfile%%\\AppData\\Local\\Programs\\Python\\Python312\\python.exe', '%%UserProfile%%\\AppData\\Local\\Programs\\Python\\Python311\\python.exe'); foreach ($p in $paths) { $exp = [Environment]::ExpandEnvironmentVariables($p); if (Test-Path $exp) { try { $v = & $exp -c 'import sys; print(sys.version_info.minor)' 2>$null; if ($v -match '^(11|12)$') { Write-Host 'FOUND:' $exp } } catch {} } }"
echo.
echo If found above, use option [4] and paste the path.
echo.
goto menu

:end
pause
exit /b 0

:find_python312
set PY312_PATH=
if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
    set "PY312_PATH=%LocalAppData%\Programs\Python\Python312\python.exe"
    goto :eof
)
if exist "C:\Python312\python.exe" (
    set "PY312_PATH=C:\Python312\python.exe"
    goto :eof
)
if exist "%ProgramFiles%\Python312\python.exe" (
    set "PY312_PATH=%ProgramFiles%\Python312\python.exe"
    goto :eof
)
if exist "%UserProfile%\AppData\Local\Programs\Python\Python312\python.exe" (
    set "PY312_PATH=%UserProfile%\AppData\Local\Programs\Python\Python312\python.exe"
    goto :eof
)
goto :eof

:find_python311
set PY311_PATH=
if exist "%LocalAppData%\Programs\Python\Python311\python.exe" (
    set "PY311_PATH=%LocalAppData%\Programs\Python\Python311\python.exe"
    goto :eof
)
if exist "C:\Python311\python.exe" (
    set "PY311_PATH=C:\Python311\python.exe"
    goto :eof
)
if exist "%ProgramFiles%\Python311\python.exe" (
    set "PY311_PATH=%ProgramFiles%\Python311\python.exe"
    goto :eof
)
goto :eof
