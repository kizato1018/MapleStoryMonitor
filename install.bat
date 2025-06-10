@echo off
setlocal EnableDelayedExpansion
echo ================================================
echo   MapleStory Monitor Auto Install Script (Windows)
echo ================================================
echo.

@REM :: Check administrator privileges
@REM net session >nul 2>&1
@REM if errorlevel 1 (
@REM     echo [Warning] Recommend running this script as administrator
@REM     echo If you encounter permission issues, right-click this file and select "Run as administrator"
@REM     echo.
@REM     echo Press any key to continue, or press Ctrl+C to cancel...
@REM     pause >nul
@REM )

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [Error] Python not found, please install Python 3.8 or newer version
    echo Download URL: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

echo [1/8] Checking Python version...
for /f "tokens=2" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo Found Python %PYTHON_VERSION%

:: Check pip
echo [2/8] Checking pip...
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo [Error] pip is not properly installed
    pause
    exit /b 1
)
echo pip check completed

:: Clean old virtual environment
echo [3/8] Cleaning old environment...
if exist "venv" (
    echo.
    echo Old virtual environment detected!
    echo.
    echo Choose action:
    echo   1. Reinstall - Delete old environment and create new one ^(Recommended^)
    echo   2. Keep existing environment - Skip virtual environment creation
    echo   3. Cancel installation
    echo.
    set "choice=1"
    set /p choice="Please enter your choice (1/2/3): "
    
    if "!choice!"=="1" (
        echo.
        echo Deleting old virtual environment...
        
        :: Try normal deletion
        rmdir /s /q venv >nul 2>&1
        
        :: If deletion fails, try force deletion
        if exist "venv" (
            echo Force cleaning old environment...
            timeout /t 2 /nobreak >nul
            
            :: Remove read-only attributes
            attrib -R venv\*.* /S /D >nul 2>&1
            
            :: Try deleting again
            rmdir /s /q venv >nul 2>&1
            
            :: If still exists, prompt user
            if exist "venv" (
                echo [Warning] Cannot completely clean old environment, some files may be locked
                echo Please close all related programs and run the install script again
                echo Or manually delete the venv folder
                pause
                exit /b 1
            )
        )
        echo Old environment cleanup completed
    ) else if "!choice!"=="2" (
        echo.
        echo Keeping existing virtual environment, jumping to package installation...
        goto install_packages
    ) else if "!choice!"=="3" (
        echo.
        echo Installation cancelled
        pause
        exit /b 0
    ) else (
        echo.
        echo Invalid choice, defaulting to reinstall...
        goto :reinstall_env
    )
) else (
    echo No old environment found
)

:: Create virtual environment
echo [4/8] Creating virtual environment...
:reinstall_env
python -m venv venv
if errorlevel 1 (
    echo [Error] Failed to create virtual environment
    echo Possible solutions:
    echo 1. Ensure sufficient disk space
    echo 2. Check if antivirus software is blocking
    echo 3. Run as administrator
    pause
    exit /b 1
)

:: Wait for file system sync
timeout /t 2 /nobreak >nul
echo Virtual environment created successfully

:: Check if virtual environment is normal
echo [5/8] Checking virtual environment...
if not exist "venv\Scripts\python.exe" (
    echo [Error] Virtual environment creation incomplete
    echo Please check antivirus settings or try running with administrator privileges
    pause
    exit /b 1
)

:: Activate virtual environment and upgrade pip
echo [6/8] Activating virtual environment and upgrading pip...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [Error] Cannot activate virtual environment
    echo Trying to use Python directly from virtual environment...
    venv\Scripts\python.exe -m pip install --upgrade pip
) else (
    python -m pip install --upgrade pip
)

:: Install dependencies
:install_packages
echo [7/8] Installing dependencies...
echo This may take a few minutes, please be patient...

:: Ensure in correct directory
cd /d "%~dp0"

:: Try installing using activated environment
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [Warning] Installation failed with activated environment, trying direct virtual environment...
    venv\Scripts\python.exe -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [Error] Failed to install dependencies
        echo Possible solutions:
        echo 1. Check network connection
        echo 2. Check firewall settings
        echo 3. Try using mobile hotspot
        echo 4. Manual installation: venv\Scripts\python.exe -m pip install -r requirements.txt
        pause
        exit /b 1
    )
)

:: Create launch script
echo [8/8] Creating launch script...

:: Create VBS script to generate shortcut
(
echo Set oWS = WScript.CreateObject^("WScript.Shell"^)
echo sLinkFile = "%~dp0run.lnk"
echo Set oLink = oWS.CreateShortcut^(sLinkFile^)
echo oLink.TargetPath = "%~dp0venv\Scripts\pythonw.exe"
echo oLink.Arguments = "main.py"
echo oLink.WorkingDirectory = "%~dp0"
echo oLink.Description = "MapleStory Monitor"
echo oLink.IconLocation = "%~dp0icon\icon.ico"
echo oLink.Save
) > create_shortcut.vbs

:: Execute VBS script to create shortcut
cscript //nologo create_shortcut.vbs

:: Delete temporary VBS file
del create_shortcut.vbs

:: Rename shortcut to run.lnk (actually .lnk file, but displays as run)
if exist "run.lnk" (
    echo Shortcut created successfully
) else (
    echo [Warning] Shortcut creation failed, creating backup batch file...
    :: If shortcut creation fails, create backup batch file
    (
    echo @echo off
    echo cd /d "%~dp0"
    echo if not exist "venv\Scripts\pythonw.exe" ^(
    echo     echo [Error] Virtual environment does not exist, please run install.bat again
    echo     pause
    echo     exit /b 1
    echo ^)
    echo venv\Scripts\pythonw.exe main.py
    ) > run.bat
)



echo.
echo ================================================
echo           Installation Complete!
echo ================================================
echo.
echo Usage:
if exist "run.lnk" (
    echo   Double-click the run shortcut to start the program
) else (
    echo   Double-click run.bat to start the program
)
echo.
echo Notes:
echo   Make sure MapleStory game is running
echo   First use requires window selection and monitoring area setup
echo   If you encounter problems, use run_debug.bat to view error messages
echo   Detailed logs are located in the Log folder
echo.
echo Troubleshooting:
echo   If startup fails, check antivirus software settings
echo   Ensure the venv folder is not quarantined by antivirus
echo   Try adding the program folder to antivirus whitelist
echo   Use run_debug.bat to see detailed error messages
echo.
echo Press any key to exit...
pause >nul