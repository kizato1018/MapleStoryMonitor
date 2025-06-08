"""
Main Window Module
主視窗模組
"""

import tkinter as tk
from tkinter import ttk
import threading
import time
from typing import Dict, Any
import os

from gui.widgets.window_selection import WindowSelectionWidget
from gui.widgets.frequency_control import FrequencyControlWidget
from gui.widgets.exp_calculator import EXPCalculatorWidget
from gui.monitor_tab import GameMonitorTab
from config.config_manager import ConfigManager
from ocr.ocr_engine import OCREngine
from module.hpmp_manager import HPMPManager
from module.exp_manager import EXPManager
from utils.common import FrequencyController
from utils.log import get_logger

logger = get_logger(__name__)


class GameMonitorMainWindow:
    """遊戲監控主視窗"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("遊戲狀態監控")
        self.root.geometry("800x600")
          # 配置管理器
        self.config_manager = ConfigManager()
        
        # 數據管理器
        self.hpmp_manager = HPMPManager()
        self.exp_manager = EXPManager()
        
        # 標記是否正在載入配置（防止觸發保存）
        self.is_loading_config = True
        
        # 共享的FPS變數
        self.shared_fps_var = None
        
        # OCR引擎
        self.ocr_engine = OCREngine()
        self.ocr_frequency_controller = FrequencyController(2.0)  # OCR較低頻率
        
        # 監控標籤頁
        self.tabs = {}
        
        # 共享的視窗選擇
        self.shared_window_widget = None
        
        self._create_gui()
        self._init_ocr()
        # 載入配置移到GUI創建後
        self._load_config()
        # 配置載入完成後，啟用配置保存
        self.is_loading_config = False
        # 延遲啟動監控，確保配置載入完成
        self._start_monitoring()
        # 延遲自動選擇視窗，確保GUI完全初始化
        self._auto_select_window()
    
    def _create_gui(self):
        """創建GUI"""
        self.shared_fps_var = tk.StringVar(value="5.0")

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 先創建設定標籤頁，確保 shared_window_widget 先初始化
        self.setting_frame = ttk.Frame(self.notebook)
        self._create_setting_tab()

        # 創建總覽標籤頁
        self.overview_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.overview_frame, text="總覽")
        self._create_overview_tab()

        # 創建HP、MP、EXP標籤頁（現在 shared_window_widget 已經存在）
        tab_names = ["HP", "MP", "EXP"]
        for tab_name in tab_names:
            self._create_monitor_tab(tab_name)

        # 最後添加設定標籤頁到最右邊
        self.notebook.add(self.setting_frame, text="設定")

        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _create_setting_tab(self):
        """創建設定標籤頁，包含視窗選擇與全域設定"""
        # 視窗選擇
        window_frame = ttk.LabelFrame(self.setting_frame, text="目標視窗選擇", padding=10)
        window_frame.pack(fill=tk.X, padx=20, pady=10)
        self.shared_window_widget = WindowSelectionWidget(window_frame, None)
        from capture.base_capture import CaptureFactory
        shared_capture_engine = CaptureFactory.create_capture_engine()
        self.shared_window_widget.set_capture_engine(shared_capture_engine)
        self.shared_window_widget.pack(fill=tk.X)

        # 全域FPS控制
        fps_frame = ttk.LabelFrame(self.setting_frame, text="全域設定", padding=10)
        fps_frame.pack(fill=tk.X, padx=20, pady=10)
        fps_control_frame = ttk.Frame(fps_frame)
        fps_control_frame.pack(fill=tk.X, pady=5)
        ttk.Label(fps_control_frame, text="擷取頻率 (FPS):").grid(row=0, column=0, padx=5, sticky='w')
        ttk.Entry(fps_control_frame, textvariable=self.shared_fps_var, width=10).grid(row=0, column=1, padx=5)
        self.global_fps_label = ttk.Label(fps_frame, text="")
        self.global_fps_label.pack(anchor=tk.W, pady=(5, 0))
        self._update_global_fps_label()

    def _create_overview_tab(self):
        """創建總覽標籤頁"""
        # 標題
        title_label = tk.Label(
            self.overview_frame,
            text="遊戲狀態總覽",
            font=('Arial', 16, 'bold')
        )
        title_label.pack(pady=10)
        
        # 結果顯示框架
        results_frame = ttk.LabelFrame(self.overview_frame, text="當前狀態", padding=20)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # 創建結果顯示標籤
        self.overview_labels = {}
        for i, stat_name in enumerate(["HP", "MP", "EXP"]):
            stat_frame = ttk.Frame(results_frame)
            stat_frame.pack(fill=tk.X, pady=5)
            
            ttk.Label(stat_frame, text=f"{stat_name}:", font=('Arial', 12, 'bold')).pack(side=tk.LEFT, padx=10)
            
            # 設定 HP 紅色, MP 藍色, EXP 黑色
            color = "black"
            if stat_name == "HP":
                color = "red"
            elif stat_name == "MP":
                color = "blue"
            value_label = tk.Label(
                stat_frame,
                text="N/A",
                font=('Arial', 12),
                fg=color,
                width=20
            )
            value_label.pack(side=tk.LEFT, padx=10)
            
            self.overview_labels[stat_name] = value_label
          # OCR狀態顯示
        status_frame = ttk.Frame(results_frame)
        status_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(status_frame, text="OCR狀態:", font=('Arial', 12)).pack(side=tk.LEFT)
        self.ocr_status_label = tk.Label(
            status_frame,
            text="初始化中...",
            font=('Arial', 12),
            fg='orange'
        )
        self.ocr_status_label.pack(side=tk.LEFT, padx=10)
        
        # EXP計算器
        exp_calc_frame = ttk.LabelFrame(self.overview_frame, text="經驗值計算器", padding=10)
        exp_calc_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.exp_calculator = EXPCalculatorWidget(exp_calc_frame, self.exp_manager)
        self.exp_calculator.pack(fill=tk.X)
    
    def _update_global_fps_label(self, *args):
        """更新全域FPS標籤"""
        try:
            fps = float(self.shared_fps_var.get())
            interval = 1.0 / fps if fps > 0 else 0
            self.global_fps_label.config(text=f"當前頻率: {fps:.1f} FPS (間隔: {interval:.3f}秒)")
        except ValueError:
            self.global_fps_label.config(text="請輸入有效的數值")
    
    def _create_monitor_tab(self, tab_name: str):
        """創建監控標籤頁"""
        # 創建標籤頁（暫時不綁定config_callback）
        tab = GameMonitorTab(
            self.notebook, 
            tab_name, 
            None,  # 暫時不綁定config_callback
            self.shared_fps_var, 
            self.shared_window_widget
        )
        
        self.tabs[tab_name] = tab
        frame = tab._create_tab()
        self.notebook.add(frame, text=tab_name)
        
        return tab
    
    def _init_ocr(self):
        """初始化OCR"""
        def update_status():
            status = self.ocr_engine.get_status()
            self.ocr_status_label.config(text=status)
            
            if status == "運行中":
                self.ocr_status_label.config(fg='green')
            elif status == "初始化中...":
                self.ocr_status_label.config(fg='orange')
            else:
                self.ocr_status_label.config(fg='red')
            
            # 每秒更新一次狀態
            self.root.after(1000, update_status)
        
        # 設定OCR結果回調
        self.ocr_engine.set_result_callback(self._update_ocr_result)
        
        # 初始化OCR引擎
        self.ocr_engine.initialize()
        self.ocr_engine.start_ocr_loop()
          # 開始OCR處理迴圈
        self._start_ocr_processing()
        
        # 開始狀態更新
        update_status()

    def _start_ocr_processing(self):
        """開始OCR處理"""
        def ocr_loop():
            while True:
                try:
                    if self.ocr_frequency_controller.should_process():
                        # 收集所有標籤頁的圖像
                        images_dict = {}
                        for tab_name, tab in self.tabs.items():
                            image = tab.get_latest_image()
                            if image:
                                images_dict[tab_name] = image
                        logger.debug(f"[OCR DEBUG] images_dict keys: {list(images_dict.keys())}")  # <--- debug

                        # 處理OCR
                        if images_dict:
                            logger.debug("[OCR DEBUG] 呼叫 process_images")
                            self.ocr_engine.process_images(images_dict)
                        else:
                            logger.debug("[OCR DEBUG] 沒有可用的圖像進行OCR")
                            pass
                    
                    time.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"OCR處理錯誤: {e}")
                    time.sleep(1.0)
        threading.Thread(target=ocr_loop, daemon=True).start()

    def _update_ocr_result(self, tab_name: str, result: str):
        """更新OCR結果"""
        logger.debug(f"[OCR DEBUG] set_ocr_result({tab_name}, {result})")  # <--- debug
        
        # 將辨識結果傳送到對應的管理器
        if tab_name == "HP" or tab_name == "MP":
            # 獲取當前HP和MP值
            current_hp = self.tabs["HP"].get_ocr_result() if "HP" in self.tabs else "N/A"
            current_mp = self.tabs["MP"].get_ocr_result() if "MP" in self.tabs else "N/A"
            
            # 如果當前更新的是HP，使用新結果
            if tab_name == "HP":
                current_hp = result
            elif tab_name == "MP":
                current_mp = result
                
            # 更新HP/MP管理器
            self.hpmp_manager.update(current_hp, current_mp)
            
            # 獲取格式化的結果（附加百分比）
            hp_formatted = self.hpmp_manager.get_formatted_hp()
            mp_formatted = self.hpmp_manager.get_formatted_mp()
            
            # Debug parse 結果
            logger.debug(f"[PARSE DEBUG] HP parse: {hp_formatted}, MP parse: {mp_formatted}")
            
            # 更新對應標籤頁的結果（使用原始OCR結果）
            if tab_name == "HP" and "HP" in self.tabs:
                self.tabs["HP"].set_ocr_result(result)
            elif tab_name == "MP" and "MP" in self.tabs:
                self.tabs["MP"].set_ocr_result(result)
            
            # 更新總覽頁面（使用格式化結果）
            if "HP" in self.overview_labels:
                self.overview_labels["HP"].config(text=hp_formatted)
            if "MP" in self.overview_labels:
                self.overview_labels["MP"].config(text=mp_formatted)
                
        elif tab_name == "EXP":
            # 更新EXP管理器
            self.exp_manager.update(result)
            
            # 取得格式化EXP顯示 - 使用有效的經驗值
            exp_status = self.exp_manager.get_status()
            exp_formatted = None
            if exp_status:
                exp_val = exp_status.get("current_exp_value")
                exp_percent = exp_status.get("current_exp_percent")
                if exp_val is not None:
                    exp_val_str = f"{exp_val:,}"
                else:
                    exp_val_str = "N/A"
                if exp_percent is not None:
                    exp_formatted = f"{exp_val_str} [{exp_percent:.2f}%]"
                else:
                    exp_formatted = exp_val_str
                # Debug parse 結果
                logger.debug(f"[PARSE DEBUG] EXP parse: {exp_formatted}")
            else:
                exp_formatted = "N/A"
            
            # 更新對應標籤頁的結果（使用原始OCR結果）
            if tab_name in self.tabs:
                self.tabs[tab_name].set_ocr_result(result)
            
            # 更新總覽頁面（使用格式化的有效結果）
            if tab_name in self.overview_labels:
                self.overview_labels[tab_name].config(text=exp_formatted)
        else:
            # 其他標籤頁直接更新
            if tab_name in self.tabs:
                self.tabs[tab_name].set_ocr_result(result)
            
            # 更新總覽頁面
            if tab_name in self.overview_labels:
                self.overview_labels[tab_name].config(text=result)
    
    def _start_monitoring(self):
        """開始監控"""
        for tab in self.tabs.values():
            tab.start_capture()
    
    def _stop_monitoring(self):
        """停止監控"""
        for tab in self.tabs.values():
            tab.stop_capture()
        self.ocr_engine.stop_ocr_loop()
    
    def _load_config(self):
        """載入配置"""
        success = self.config_manager.load_config()
        if success:
            logger.info(f"成功載入配置檔案: {self.config_manager.config_file}")
            
            # 載入全域配置
            global_config = self.config_manager.get_global_config()
            
            # 處理FPS配置（支援舊格式）
            fps = global_config.get('fps', self.config_manager.config_data.get('global_fps', 5.0))
            self.shared_fps_var.set(str(fps))
            # 立即更新所有tab的frequency_controller
            self._update_global_fps_label()
            
            # 設定視窗標題（支援舊格式）
            window_title = global_config.get('window_title', '')
            if not window_title:
                # 檢查舊格式的shared_window配置
                shared_window = self.config_manager.config_data.get('shared_window', {})
                window_title = shared_window.get('window_title', '')
            
            if self.shared_window_widget:
                self.shared_window_widget.set_window_title(window_title)
            
            # 載入各標籤頁配置（支援舊格式）
            for tab_name, tab in self.tabs.items():
                # 優先從tabs結構載入
                tab_config = self.config_manager.get_tab_config(tab_name)
                if not tab_config:
                    # 檢查根層級的舊格式配置
                    tab_config = self.config_manager.config_data.get(tab_name)
                
                if tab_config:
                    logger.info(f"載入 {tab_name} 配置: {tab_config}")
                    tab.load_config(tab_config)
                else:
                    logger.warning(f"未找到 {tab_name} 的配置")
            
            # 設定OCR允許字符列表
            allow_list = global_config.get('ocr_allow_list', '0123456789.[]/%')
            self.ocr_engine.set_allow_list(allow_list)
        
        # 配置載入完成後，綁定回調函數
        self._bind_config_callbacks()

    def _bind_config_callbacks(self):
        """綁定配置回調函數"""
        # 綁定FPS變數的回調
        self.shared_fps_var.trace('w', lambda *args: self._save_config_if_ready())
        self.shared_fps_var.trace('w', self._update_global_fps_label)
        
        # 綁定視窗選擇控件的回調
        if self.shared_window_widget:
            self.shared_window_widget.config_callback = self._save_config_if_ready
            self.shared_window_widget.window_title_var.trace('w', lambda *args: self._save_config_if_ready())
        
        # 綁定各標籤頁的回調
        for tab in self.tabs.values():
            tab.config_callback = self._save_config_if_ready
            # 為每個輸入框重新綁定trace
            if hasattr(tab, 'region_widget'):
                for var in [tab.region_widget.x_var, tab.region_widget.y_var, 
                           tab.region_widget.w_var, tab.region_widget.h_var]:
                    var.trace('w', lambda *args: self._save_config_if_ready())

    def _save_config_if_ready(self):
        """只有在配置載入完成後才保存配置"""
        if not self.is_loading_config:
            self._save_config()

    def _save_config(self):
        """儲存配置"""
        # 儲存全域配置
        try:
            fps = float(self.shared_fps_var.get())
            self.config_manager.set_fps(fps)
        except ValueError:
            pass
        
        if self.shared_window_widget:
            window_title = self.shared_window_widget.window_title_var.get()
            self.config_manager.set_window_title(window_title)
        
        # 儲存各標籤頁配置
        for tab_name, tab in self.tabs.items():
            tab_config = tab.get_config()
            if tab_config:
                self.config_manager.set_tab_config(tab_name, tab_config)
        
        # 儲存到檔案
        self.config_manager.save_config()
    
    def _on_closing(self):
        """視窗關閉事件處理"""
        self._save_config()
        self._stop_monitoring()
        self.root.destroy()
    
    def _auto_select_window(self):
        """自動選擇目標視窗"""
        if self.shared_window_widget:
            window_title = self.shared_window_widget.window_title_var.get().strip()
            if window_title:
                success = self.shared_window_widget._auto_search_and_select()
                if success:
                    logger.info(f"成功自動選擇視窗: {window_title}")
                else:
                    logger.warning(f"未找到視窗: {window_title}")


    def run(self):
        """運行主程式"""
        self.root.mainloop()
