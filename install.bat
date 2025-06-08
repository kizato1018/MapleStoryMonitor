@echo off
setlocal EnableDelayedExpansion
echo ================================================
echo   MapleStory Monitor �۰ʦw�˸}�� (Windows)
echo ================================================
echo.

@REM :: �ˬd�޲z���v��
@REM net session >nul 2>&1
@REM if errorlevel 1 (
@REM     echo [ĵ�i] ��ĳ�H�t�κ޲z���������榹�}��
@REM     echo �p�J�v�����D�A�Хk���I�����ɮרÿ�ܥH�u�H�t�κ޲z����������v
@REM     echo.
@REM     echo �����N���~��A�Ϋ� Ctrl+C ����...
@REM     pause >nul
@REM )

:: �ˬd Python �O�_�w�w��
python --version >nul 2>&1
if errorlevel 1 (
    echo [���~] ����� Python�A�Х��w�� Python 3.8 �Χ�s����
    echo �U�����}: https://www.python.org/downloads/
    echo �w�ˮɽаȥ��Ŀ� "Add Python to PATH"
    pause
    exit /b 1
)

echo [1/7] �ˬd Python ����...
for /f "tokens=2" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo �w��� Python %PYTHON_VERSION%

:: �ˬd pip
echo [2/7] �ˬd pip...
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo [���~] pip �����T�w��
    pause
    exit /b 1
)
echo pip �ˬd����

:: �M�z�ª���������
echo [3/7] �M�z������...
if exist "venv" (
    echo.
    echo �������ª��������ҡI
    echo.
    echo ��ܾާ@�G
    echo   1. ���s�w�� - �R�������Ҩí��s�إ� ^(��ĳ^)
    echo   2. �O�d�{������ - ���L�������ҫإ�
    echo   3. �����w��
    echo.
    set /p choice="�п�J��� (1/2/3): "
    
    if "!choice!"=="1" (
        echo.
        echo ���b�R���ª���������...
        
        :: ���ե��`�R��
        rmdir /s /q venv >nul 2>&1
        
        :: �p�G�R�����ѡA���ձj��R��
        if exist "venv" (
            echo ���b�j��M�z������...
            timeout /t 2 /nobreak >nul
            
            :: �����uŪ�ݩ�
            attrib -R venv\*.* /S /D >nul 2>&1
            
            :: �A�����էR��
            rmdir /s /q venv >nul 2>&1
            
            :: �p�G�٬O�s�b�A���ܥΤ�
            if exist "venv" (
                echo [ĵ�i] �L�k�����M�z�����ҡA�i�঳�ɮ׳Q��w
                echo �������Ҧ������{�ǫ᭫�s����w�˸}��
                echo �Τ�ʧR�� venv ��Ƨ�
                pause
                exit /b 1
            )
        )
        echo �����ҲM�z����
    ) else if "!choice!"=="2" (
        echo.
        echo �O�d�{���������ҡA����̿�M��w��...
        goto install_packages
    ) else if "!choice!"=="3" (
        echo.
        echo �w�ˤw����
        pause
        exit /b 0
    ) else (
        echo.
        echo �L�Ī���ܡA�w�]�i�歫�s�w��...
        goto :reinstall_env
    )
) else (
    echo ���o�{������
)

:: �Ыص�������
echo [4/7] �Ыص�������...
:reinstall_env
python -m venv venv
if errorlevel 1 (
    echo [���~] �Ыص������ҥ���
    echo �i�઺�ѨM��סG
    echo 1. �T�O���������ϺЪŶ�
    echo 2. �ˬd���r�n��O�_����
    echo 3. �H�t�κ޲z����������
    pause
    exit /b 1
)

:: �����ɮרt�ΦP�B
timeout /t 2 /nobreak >nul
echo �������ҳЫئ��\

:: �ˬd�������ҬO�_���`
echo [5/7] �ˬd��������...
if not exist "venv\Scripts\python.exe" (
    echo [���~] �������ҫإߤ�����
    echo ���ˬd���r�n��]�w�ι��եH�޲z���v������
    pause
    exit /b 1
)

:: �Ұʵ������Ҩäɯ� pip
echo [6/7] �Ұʵ������Ҩäɯ� pip...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [���~] �L�k�Ұʵ�������
    echo ���ժ����ϥε������Ҥ��� Python...
    venv\Scripts\python.exe -m pip install --upgrade pip
) else (
    python -m pip install --upgrade pip
)

:: �w�˨̿�M��
:install_packages
echo [7/7] �w�˨̿�M��...
echo �o�i��ݭn�X�����ɶ��A�Э@�ߵ���...

:: �T�O�b���T���ؿ�
cd /d "%~dp0"

:: ���ըϥοE�������Ҧw��
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ĵ�i] �ϥοE�����Ҧw�˥��ѡA���ժ����ϥε�������...
    venv\Scripts\python.exe -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [���~] �w�˨̿�M�󥢱�
        echo �i�઺�ѨM��סG
        echo 1. �ˬd�����s�u
        echo 2. �ˬd������]�w
        echo 3. ���ըϥΤ�����I
        echo 4. ��ʦw�ˡGvenv\Scripts\python.exe -m pip install -r requirements.txt
        pause
        exit /b 1
    )
)

:: �ЫرҰʸ}��
echo �ЫرҰʸ}��...

:: �Ы� VBS �}���ӥͦ����|
(
echo Set oWS = WScript.CreateObject^("WScript.Shell"^)
echo sLinkFile = "%~dp0run.lnk"
echo Set oLink = oWS.CreateShortcut^(sLinkFile^)
echo oLink.TargetPath = "%~dp0venv\Scripts\pythonw.exe"
echo oLink.Arguments = "main.py"
echo oLink.WorkingDirectory = "%~dp0"
echo oLink.Description = "MapleStory Monitor"
echo oLink.Save
) > create_shortcut.vbs

:: ���� VBS �}���Ыر��|
cscript //nologo create_shortcut.vbs

:: �R���{�� VBS �ɮ�
del create_shortcut.vbs

:: ���R�W���|�� run.lnk�]��ڤW�O .lnk �ɮסA����ܬ� run�^
if exist "run.lnk" (
    echo ���|�Ыئ��\
) else (
    echo [ĵ�i] ���|�Ыإ��ѡA�ЫسƥΧ妸��...
    :: �p�G���|�Ыإ��ѡA�ЫسƥΪ��妸��
    (
    echo @echo off
    echo cd /d "%~dp0"
    echo if not exist "venv\Scripts\pythonw.exe" ^(
    echo     echo [���~] �������Ҥ��s�b�A�Э��s���� install.bat
    echo     pause
    echo     exit /b 1
    echo ^)
    echo venv\Scripts\pythonw.exe main.py
    ) > run.bat
)



echo.
echo ================================================
echo           ? �w�˧����I ?
echo ================================================
echo.
echo �ϥΤ�k�G
if exist "run.lnk" (
    echo   ? ���� run ���|�Ұʵ{��
) else (
    echo   ? ���� run.bat �Ұʵ{��
)
echo.
echo �`�N�ƶ��G
echo   ? �нT�O MapleStory �C���w�Ұ�
echo   ? �����ϥλݭn�]�w������ܩM�ʱ��ϰ�
echo   ? �p�J���D�Шϥ� run_debug.bat �d�ݿ��~�T��
echo   ? �ԲӰO���ɦ�� Log ��Ƨ���
echo.
echo �����ƸѡG
echo   ? �p�G�Ұʥ��ѡA���ˬd���r�n��]�w
echo   ? �T�O venv ��Ƨ��S���Q���r�n��j��
echo   ? �i���ձN�{�Ǹ�Ƨ��[�J���r�n��զW��
echo   ? �ϥ� run_debug.bat �i�H�ݨ�ԲӪ����~�T��
echo.
echo �����N��h�X...
pause >nul