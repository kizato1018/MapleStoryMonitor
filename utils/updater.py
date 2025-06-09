import requests
from packaging import version
import os
import sys
import subprocess
import zipfile
import shutil
import tempfile
import json
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
from utils.log import get_logger

logger = get_logger(__name__)

def get_local_version():
    """讀取本地版本號"""
    try:
        version_file = Path(__file__).parent.parent / "version.txt"
        with open(version_file, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        return "0.0.0"

def get_remote_version():
    """從GitHub獲取遠端版本號"""
    try:
        url = "https://raw.githubusercontent.com/kizato1018/MapleStoryMonitor/master/version.txt"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text.strip()
    except requests.RequestException:
        return None

def download_update():
    """下載更新檔案"""
    try:
        url = "https://github.com/kizato1018/MapleStoryMonitor/archive/refs/heads/main.zip"
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, "update.zip")
        
        logger.info("正在下載更新...")
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return temp_dir, zip_path
    except requests.RequestException as e:
        logger.error(f"下載失敗: {e}")
        return None, None

def extract_and_replace(temp_dir, zip_path):
    """解壓縮並替換檔案"""
    try:
        extract_dir = os.path.join(temp_dir, "extracted")
        
        logger.info("正在解壓縮...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # 找到解壓縮後的主資料夾
        extracted_folders = [f for f in os.listdir(extract_dir) 
                           if os.path.isdir(os.path.join(extract_dir, f))]
        if not extracted_folders:
            raise Exception("解壓縮後找不到主資料夾")
        
        source_dir = os.path.join(extract_dir, extracted_folders[0])
        target_dir = Path(__file__).parent.parent
        
        logger.info("正在替換檔案...")
        # 備份重要檔案（如配置檔案）
        backup_files = []
        backups = {}
        
        for backup_file in backup_files:
            backup_path = target_dir / backup_file
            if backup_path.exists():
                with open(backup_path, 'r', encoding='utf-8') as f:
                    backups[backup_file] = f.read()
        
        # 複製新檔案
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                src_file = os.path.join(root, file)
                rel_path = os.path.relpath(src_file, source_dir)
                dst_file = target_dir / rel_path
                
                # 創建目標目錄
                dst_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, dst_file)
        
        # 恢復備份檔案
        for backup_file, content in backups.items():
            backup_path = target_dir / backup_file
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        return True
    except Exception as e:
        logger.error(f"檔案替換失敗: {e}")
        return False

def update_dependencies():
    """更新Python依賴"""
    try:
        logger.info("正在更新依賴...")
        requirements_path = Path(__file__).parent.parent / "requirements.txt"
        if requirements_path.exists():
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(requirements_path)], 
                         check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"依賴更新失敗: {e}")
        return False

def cleanup_temp_files(temp_dir):
    """清理臨時檔案"""
    try:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        logger.info("清理完成")
    except Exception as e:
        logger.error(f"清理失敗: {e}")

def restart_application():
    """重新啟動應用程式"""
    try:
        logger.info("正在重新啟動...")
        # 獲取主程式路徑
        main_script = Path(__file__).parent.parent / "main.py"
        if main_script.exists():
            subprocess.Popen([sys.executable, str(main_script)])
        sys.exit(0)
    except Exception as e:
        logger.error(f"重新啟動失敗: {e}")

def read_config():
    """讀取配置檔案"""
    try:
        config_file = Path(__file__).parent.parent / "game_monitor_config.json"
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('auto_update', False)
        return False
    except Exception as e:
        logger.error(f"讀取配置檔案失敗: {e}")
        return False

def update_config(auto_update):
    """更新配置檔案中的auto_update設定"""
    try:
        config_file = Path(__file__).parent.parent / "game_monitor_config.json"
        config = {}
        
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        
        config['auto_update'] = auto_update
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        
        logger.info(f"已更新auto_update設定為: {auto_update}")
    except Exception as e:
        logger.error(f"更新配置檔案失敗: {e}")

def show_update_dialog(remote_ver):
    """顯示更新對話框"""
    def on_update():
        auto_update = auto_update_var.get()
        update_config(auto_update)
        result.append(True)
        root.destroy()
    
    def on_cancel():
        auto_update = auto_update_var.get()
        update_config(auto_update)
        result.append(False)
        root.destroy()
    
    result = []
    
    # 創建主視窗
    root = tk.Tk()
    root.title("發現新版本")
    root.geometry("350x200")
    root.resizable(False, False)
    root.withdraw()  # 先隱藏視窗
    try:
        import platform
        import ctypes
        if platform.system() == "Windows":
            myappid = 'mycompany.myapp.subapp.1.0'  # 任意唯一值
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "images", "icon.ico")
            if os.path.exists(icon_path):
                root.iconbitmap(icon_path)
                logger.debug(f"成功設定視窗圖標: {icon_path}")
            else:
                logger.warning(f"視窗圖標檔案不存在: {icon_path}")
        else:
            icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "images", "icon.png")
            if os.path.exists(icon_path):
                root.iconphoto(True, tk.Image("photo", file=icon_path)) # you may also want to try this.
                logger.debug(f"成功設定視窗圖標: {icon_path}")
            else:
                logger.warning(f"視窗圖標檔案不存在: {icon_path}")
        
    except Exception as e:
        logger.warning(f"設定視窗圖標失敗: {e}")
    
    # 置中顯示
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (350 // 2)
    y = (root.winfo_screenheight() // 2) - (150 // 2)
    root.geometry(f"350x200+{x}+{y}")
    root.deiconify()  # 顯示視窗
    
    # 主要訊息
    message_frame = tk.Frame(root)
    message_frame.pack(pady=15)
    
    tk.Label(message_frame, text="發現新版本", font=("Arial", 12, "bold")).pack()
    tk.Label(message_frame, text=f"版本 {remote_ver} 可供下載", font=("Arial", 9)).pack(pady=3)
    tk.Label(message_frame, text="是否立即更新？", font=("Arial", 9)).pack()
    # 警告訊息 (紅色小字)
    warning_frame = tk.Frame(root)
    warning_frame.pack(pady=5)

    warning_label = tk.Label(warning_frame, 
                            text="⚠️ 警告：更新將覆蓋所有自行修改的程式內容", 
                            font=("Arial", 8), 
                            fg="red")
    warning_label.pack()
    # 按鈕框架
    button_frame = tk.Frame(root)
    button_frame.pack(pady=5)
    
    # 更新按鈕 (顯眼的綠色)
    update_btn = tk.Button(button_frame, text="立即更新", command=on_update,
                          bg="#4CAF50", fg="white", font=("Arial", 9, "bold"),
                          width=10, height=1)
    update_btn.pack(side=tk.LEFT, padx=8)
    
    # 取消按鈕
    cancel_btn = tk.Button(button_frame, text="稍後更新", command=on_cancel,
                          bg="#757575", fg="white", font=("Arial", 9),
                          width=10, height=1)
    cancel_btn.pack(side=tk.LEFT, padx=8)
    
    # 自動更新勾選框 (左下角)
    checkbox_frame = tk.Frame(root)
    checkbox_frame.pack(side=tk.BOTTOM, anchor=tk.W, padx=15, pady=5)
    
    auto_update_var = tk.BooleanVar(value=read_config())
    auto_update_cb = tk.Checkbutton(checkbox_frame, text="自動更新",
                                   variable=auto_update_var,
                                   font=("Arial", 8))
    auto_update_cb.pack(anchor=tk.W)
    
    # 等待對話框關閉
    root.mainloop()
    
    return result[0] if result else False

def check_and_update():
    """檢查並執行自動更新"""
    logger.info("檢查更新中...")
    
    local_ver = get_local_version()
    remote_ver = get_remote_version()
    
    if remote_ver is None:
        logger.warning("無法獲取遠端版本資訊")
        return False
    
    logger.info(f"本地版本: {local_ver}")
    logger.info(f"遠端版本: {remote_ver}")
    
    try:
        if version.parse(remote_ver) > version.parse(local_ver):
            logger.info(f"發現新版本 {remote_ver}")
            
            # 檢查自動更新設定
            auto_update = read_config()
            should_update = auto_update
            
            if not auto_update:
                # 顯示更新對話框
                should_update = show_update_dialog(remote_ver)
            
            if should_update:
                logger.info("開始更新...")
                
                # 下載更新
                temp_dir, zip_path = download_update()
                if not temp_dir or not zip_path:
                    return False
                
                try:
                    # 解壓縮並替換檔案
                    if not extract_and_replace(temp_dir, zip_path):
                        return False
                    
                    # 更新依賴
                    if not update_dependencies():
                        logger.warning("依賴更新失敗，但程式碼已更新")
                    
                    # 清理臨時檔案
                    cleanup_temp_files(temp_dir)
                    
                    logger.info("更新完成！正在重新啟動...")
                    restart_application()
                    
                except Exception as e:
                    logger.error(f"更新過程中發生錯誤: {e}")
                    cleanup_temp_files(temp_dir)
                    return False
            else:
                logger.info("使用者選擇稍後更新")
                return False
        else:
            logger.info("已是最新版本")
            return True
            
    except Exception as e:
        logger.error(f"版本比較失敗: {e}")
        return False
    
    return True
