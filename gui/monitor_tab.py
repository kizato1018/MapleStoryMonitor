"""
Monitor Tab Module
監控標籤頁模組
"""

import tkinter as tk
from tkinter import ttk
import threading
import time
from typing import Optional, Callable, Dict, Any
from PIL import Image

from gui.widgets.region_selection import RegionSelectionWidget
from gui.widgets.preview_widget import PreviewWidget
from capture.base_capture import CaptureFactory
from utils.common import FrequencyController
from utils.log import get_logger

logger = get_logger(__name__)


class GameMonitorTab:
    """單個監控標籤頁類別"""
    
    def __init__(self, parent, tab_name: str, config_callback: Optional[Callable] = None, 
                 shared_frequency_var: Optional[tk.StringVar] = None, 
                 shared_window_widget=None):
        self.parent = parent
        self.tab_name = tab_name
        self.config_callback = config_callback
        self.latest_image = None
        self.ocr_result = "N/A"
        self.ocr_allow_list = '0123456789.[]/%'
        self.is_capturing = False
        self.capture_thread = None
        self.shared_frequency_var = shared_frequency_var
        self.shared_window_widget = shared_window_widget
        
        # 捕捉引擎
        self.capture_engine = CaptureFactory.create_capture_engine()
        # 預設5.0，啟動時同步shared_frequency_var
        init_fps = 5.0
        if self.shared_frequency_var:
            try:
                init_fps = float(self.shared_frequency_var.get())
            except Exception:
                pass
        self.frequency_controller = FrequencyController(init_fps)
        
        # 當前捕捉狀態
        self.current_hwnd = None
        self.current_region = None
        
        self._create_tab()
        
        # 設定區域選取元件的目標視窗回調（在創建標籤頁後）
        if self.shared_window_widget:
            self.region_widget.set_target_window_callback(self.shared_window_widget.get_window_info)
    
    def _create_tab(self):
        """創建標籤頁內容"""
        # 主框架
        main_frame = ttk.Frame(self.parent)
        
        # 左側控制區域
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        # 區域選擇元件（暫時不傳遞config_callback）
        self.region_widget = RegionSelectionWidget(control_frame, None)
        self.region_widget.pack(fill=tk.X, pady=5)
        
        # 設定區域選取元件的回調函數
        if self.shared_window_widget:
            self.region_widget.set_target_window_callback(self.shared_window_widget.get_window_info)
        
        # OCR結果顯示
        result_frame = ttk.LabelFrame(control_frame, text="辨識結果", padding=10)
        result_frame.pack(fill=tk.X, pady=5)

        self.result_label = tk.Label(
            result_frame,
            text="N/A",
            font=('Arial', 14, 'bold'),
            bg='white',
            fg='black',
            relief=tk.SUNKEN,
            height=2
        )
        self.result_label.pack(fill=tk.X)
        
        # 右側預覽區域
        preview_frame = ttk.Frame(main_frame)
        preview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.preview_widget = PreviewWidget(preview_frame)
        self.preview_widget.pack(fill=tk.BOTH, expand=True)
        
        return main_frame
    
    def start_capture(self):
        """開始擷取"""
        if self.is_capturing:
            return
            
        self.is_capturing = True
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
    
    def stop_capture(self):
        """停止擷取"""
        self.is_capturing = False
        self.capture_engine.cleanup_resources()
    
    def _capture_loop(self):
        """擷取迴圈"""
        while self.is_capturing:
            try:
                # 獲取共享的頻率設定
                if self.shared_frequency_var:
                    try:
                        fps = float(self.shared_frequency_var.get())
                        self.frequency_controller.set_fps(fps)
                    except ValueError:
                        pass
                
                # 獲取視窗和區域資訊
                window_info = None
                if self.shared_window_widget:
                    window_info = self.shared_window_widget.get_window_info()
                
                region = self.region_widget.get_region()
                
                if window_info and region:
                    hwnd = window_info['hwnd']
                    
                    # 檢查是否需要重新初始化資源
                    if (self.current_hwnd != hwnd or 
                        self.current_region != region):
                        
                        self.capture_engine.cleanup_resources()
                        success = self.capture_engine.initialize_resources(hwnd, region)
                        
                        if success:
                            self.current_hwnd = hwnd
                            self.current_region = region.copy()
                        else:
                            self.latest_image = None
                            continue
                    
                    # 擷取圖像
                    captured_img = self.capture_engine.capture_region()
                    
                    if captured_img:
                        self.latest_image = captured_img
                        # 在主線程中更新預覽
                        self.parent.after(0, self._update_preview)
                    else:
                        self.latest_image = None
                        self.parent.after(0, lambda: self.preview_widget.set_message("擷取失敗"))
                else:
                    self.parent.after(0, lambda: self.preview_widget.set_message("請選擇視窗和設定區域"))
                
                # 頻率控制
                self.frequency_controller.wait()
                
            except Exception as e:
                logger.error(f"{self.tab_name} 擷取錯誤: {e}")
                time.sleep(1.0)
        
        # 清理資源
        self.capture_engine.cleanup_resources()
    
    def _update_preview(self):
        """更新預覽"""
        if self.latest_image:
            self.preview_widget.update_preview(self.latest_image)
    
    def get_latest_image(self) -> Optional[Image.Image]:
        """獲取最新圖像"""
        return self.latest_image
    
    def set_ocr_result(self, result: str):
        """設定OCR結果"""
        self.ocr_result = result
        self.result_label.config(text=result)
    
    def get_ocr_result(self) -> str:
        """獲取OCR結果"""
        return self.ocr_result
    
    def load_config(self, config: Dict[str, Any]):
        """載入配置"""
        if config:
            x = config.get('x', 0)
            y = config.get('y', 0)
            w = config.get('w', 100)
            h = config.get('h', 30)
            
            # 確保數值有效
            try:
                x = int(x) if x is not None else 0
                y = int(y) if y is not None else 0
                w = int(w) if w is not None else 100
                h = int(h) if h is not None else 30
                
                # 確保寬高為正數
                w = max(w, 1)
                h = max(h, 1)
                
                logger.debug(f"{self.tab_name} 載入配置: x={x}, y={y}, w={w}, h={h}")
                self.region_widget.set_region(x, y, w, h)
            except (ValueError, TypeError) as e:
                logger.error(f"{self.tab_name} 配置載入錯誤: {e}")
    
    def get_config(self) -> Optional[Dict[str, Any]]:
        """獲取配置"""
        try:
            region = self.region_widget.get_region()
            if region:
                config = {
                    'x': int(region['x']),
                    'y': int(region['y']),
                    'w': int(region['w']),
                    'h': int(region['h'])
                }
                logger.debug(f"{self.tab_name} 儲存配置: {config}")
                return config
        except (ValueError, TypeError) as e:
            logger.error(f"{self.tab_name} 配置儲存錯誤: {e}")
        return None
