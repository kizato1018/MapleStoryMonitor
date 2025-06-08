@echo off
setlocal EnableDelayedExpansion
echo ================================================
echo   MapleStory Monitor 自動安裝腳本 (Windows)
echo ================================================
echo.

@REM :: 檢查管理員權限
@REM net session >nul 2>&1
@REM if errorlevel 1 (
@REM     echo [警告] 建議以系統管理員身分執行此腳本
@REM     echo 如遇權限問題，請右鍵點擊此檔案並選擇以「以系統管理員身分執行」
@REM     echo.
@REM     echo 按任意鍵繼續，或按 Ctrl+C 取消...
@REM     pause >nul
@REM )

:: 檢查 Python 是否已安裝
python --version >nul 2>&1
if errorlevel 1 (
    echo [錯誤] 未找到 Python，請先安裝 Python 3.8 或更新版本
    echo 下載網址: https://www.python.org/downloads/
    echo 安裝時請務必勾選 "Add Python to PATH"
    pause
    exit /b 1
)

echo [1/7] 檢查 Python 版本...
for /f "tokens=2" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo 已找到 Python %PYTHON_VERSION%

:: 檢查 pip
echo [2/7] 檢查 pip...
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo [錯誤] pip 未正確安裝
    pause
    exit /b 1
)
echo pip 檢查完成

:: 清理舊的虛擬環境
echo [3/7] 清理舊環境...
if exist "venv" (
    echo.
    echo 偵測到舊的虛擬環境！
    echo.
    echo 選擇操作：
    echo   1. 重新安裝 - 刪除舊環境並重新建立 ^(建議^)
    echo   2. 保留現有環境 - 跳過虛擬環境建立
    echo   3. 取消安裝
    echo.
    set /p choice="請輸入選擇 (1/2/3): "
    
    if "!choice!"=="1" (
        echo.
        echo 正在刪除舊的虛擬環境...
        
        :: 嘗試正常刪除
        rmdir /s /q venv >nul 2>&1
        
        :: 如果刪除失敗，嘗試強制刪除
        if exist "venv" (
            echo 正在強制清理舊環境...
            timeout /t 2 /nobreak >nul
            
            :: 移除只讀屬性
            attrib -R venv\*.* /S /D >nul 2>&1
            
            :: 再次嘗試刪除
            rmdir /s /q venv >nul 2>&1
            
            :: 如果還是存在，提示用戶
            if exist "venv" (
                echo [警告] 無法完全清理舊環境，可能有檔案被鎖定
                echo 請關閉所有相關程序後重新執行安裝腳本
                echo 或手動刪除 venv 資料夾
                pause
                exit /b 1
            )
        )
        echo 舊環境清理完成
    ) else if "!choice!"=="2" (
        echo.
        echo 保留現有虛擬環境，跳到依賴套件安裝...
        goto install_packages
    ) else if "!choice!"=="3" (
        echo.
        echo 安裝已取消
        pause
        exit /b 0
    ) else (
        echo.
        echo 無效的選擇，預設進行重新安裝...
        goto :reinstall_env
    )
) else (
    echo 未發現舊環境
)

:: 創建虛擬環境
echo [4/7] 創建虛擬環境...
:reinstall_env
python -m venv venv
if errorlevel 1 (
    echo [錯誤] 創建虛擬環境失敗
    echo 可能的解決方案：
    echo 1. 確保有足夠的磁碟空間
    echo 2. 檢查防毒軟體是否阻擋
    echo 3. 以系統管理員身分執行
    pause
    exit /b 1
)

:: 等待檔案系統同步
timeout /t 2 /nobreak >nul
echo 虛擬環境創建成功

:: 檢查虛擬環境是否正常
echo [5/7] 檢查虛擬環境...
if not exist "venv\Scripts\python.exe" (
    echo [錯誤] 虛擬環境建立不完整
    echo 請檢查防毒軟體設定或嘗試以管理員權限執行
    pause
    exit /b 1
)

:: 啟動虛擬環境並升級 pip
echo [6/7] 啟動虛擬環境並升級 pip...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [錯誤] 無法啟動虛擬環境
    echo 嘗試直接使用虛擬環境中的 Python...
    venv\Scripts\python.exe -m pip install --upgrade pip
) else (
    python -m pip install --upgrade pip
)

:: 安裝依賴套件
:install_packages
echo [7/7] 安裝依賴套件...
echo 這可能需要幾分鐘時間，請耐心等待...

:: 確保在正確的目錄
cd /d "%~dp0"

:: 嘗試使用激活的環境安裝
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [警告] 使用激活環境安裝失敗，嘗試直接使用虛擬環境...
    venv\Scripts\python.exe -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [錯誤] 安裝依賴套件失敗
        echo 可能的解決方案：
        echo 1. 檢查網路連線
        echo 2. 檢查防火牆設定
        echo 3. 嘗試使用手機熱點
        echo 4. 手動安裝：venv\Scripts\python.exe -m pip install -r requirements.txt
        pause
        exit /b 1
    )
)

:: 創建啟動腳本
echo 創建啟動腳本...

:: 創建 VBS 腳本來生成捷徑
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

:: 執行 VBS 腳本創建捷徑
cscript //nologo create_shortcut.vbs

:: 刪除臨時 VBS 檔案
del create_shortcut.vbs

:: 重命名捷徑為 run.lnk（實際上是 .lnk 檔案，但顯示為 run）
if exist "run.lnk" (
    echo 捷徑創建成功
) else (
    echo [警告] 捷徑創建失敗，創建備用批次檔...
    :: 如果捷徑創建失敗，創建備用的批次檔
    (
    echo @echo off
    echo cd /d "%~dp0"
    echo if not exist "venv\Scripts\pythonw.exe" ^(
    echo     echo [錯誤] 虛擬環境不存在，請重新執行 install.bat
    echo     pause
    echo     exit /b 1
    echo ^)
    echo venv\Scripts\pythonw.exe main.py
    ) > run.bat
)



echo.
echo ================================================
echo           ? 安裝完成！ ?
echo ================================================
echo.
echo 使用方法：
if exist "run.lnk" (
    echo   ? 雙擊 run 捷徑啟動程序
) else (
    echo   ? 雙擊 run.bat 啟動程序
)
echo.
echo 注意事項：
echo   ? 請確保 MapleStory 遊戲已啟動
echo   ? 首次使用需要設定視窗選擇和監控區域
echo   ? 如遇問題請使用 run_debug.bat 查看錯誤訊息
echo   ? 詳細記錄檔位於 Log 資料夾中
echo.
echo 疑難排解：
echo   ? 如果啟動失敗，請檢查防毒軟體設定
echo   ? 確保 venv 資料夾沒有被防毒軟體隔離
echo   ? 可嘗試將程序資料夾加入防毒軟體白名單
echo   ? 使用 run_debug.bat 可以看到詳細的錯誤訊息
echo.
echo 按任意鍵退出...
pause >nul