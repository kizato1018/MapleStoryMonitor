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
from capture.base_capture import BaseCaptureEngine, create_capture_engine
from utils.common import FrequencyController
from utils.log import get_logger

logger = get_logger(__name__)


class GameMonitorTab:
    """單個監控標籤頁類別"""
    def __init__(self, parent, tab_name: str, config_callback: Optional[Callable] = None,  
                 capture_engine: BaseCaptureEngine = None,
                 get_window_info_callback: Optional[Callable] = None):
        self.parent = parent
        self.tab_name = tab_name
        self.config_callback = config_callback
        self.latest_image = None
        self.ocr_result = "N/A"
        self.ocr_allow_list = '0123456789.[]/%'
        self.is_capturing = False
        self.capture_thread = None
        self.get_window_info_callback = get_window_info_callback
        
        # 捕捉引擎 - 使用外部傳入的實例
        self.capture_manager = capture_engine
        
        self._create_tab()
        

    def _create_tab(self):
        """創建標籤頁內容"""
        # 主框架
        main_frame = ttk.Frame(self.parent)
        
        # 控制區域
        self.control_frame = ttk.Frame(main_frame)
        self.control_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 區域選擇元件
        self.region_widget = RegionSelectionWidget(self.control_frame, None)
        self.region_widget.set_target_window_callback(self.get_window_info_callback)
        self.region_widget.pack(fill=tk.X, pady=(0, 10))
            
        
        # 顯示區域
        self.display_frame = ttk.LabelFrame(main_frame, text="顯示區域", padding=10)
        self.display_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # OCR結果顯示
        result_frame = ttk.LabelFrame(self.display_frame, text="辨識結果", padding=10)
        result_frame.pack(fill=tk.X, pady=(0, 10))

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
        
        # 預覽區域（移到OCR結果下方）
        preview_frame = ttk.LabelFrame(self.display_frame, text="預覽畫面", padding=5)
        preview_frame.pack(fill=tk.BOTH, expand=True)
        
        self.preview_widget = PreviewWidget(preview_frame)
        self.preview_widget.pack(fill=tk.BOTH, expand=True)
        
        return main_frame
    
    def add_potion_cost_input(self, on_cost_changed: Optional[Callable] = None):
        """添加藥水單價輸入框"""
        cost_frame = ttk.Frame(self.control_frame)
        cost_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(cost_frame, text="藥水單價:").pack(side=tk.LEFT)
        self.potion_cost_var = tk.StringVar(value="0")
        cost_entry = ttk.Entry(cost_frame, textvariable=self.potion_cost_var, width=10)
        cost_entry.pack(side=tk.LEFT, padx=2)
        cost_entry.bind('<Return>', lambda e: on_cost_changed(self.potion_cost_var.get()))
        cost_entry.bind('<FocusOut>', lambda e: on_cost_changed(self.potion_cost_var.get()))
    
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
        self.capture_manager.cleanup_resources()
    
    def _capture_loop(self):
        """擷取迴圈"""
        while self.is_capturing:
            try:
                region = self.region_widget.get_region()
                
                if region:
                    # 擷取圖像
                    captured_img = self.capture_manager.get_region(
                        x=region['x'], 
                        y=region['y'], 
                        w=region['w'], 
                        h=region['h']
                    )
                    
                    if captured_img:
                        self.latest_image = captured_img
                        
                        # [Deubg] 儲存到tmp/{tab_name}.png
                        # Image.Image.save(self.latest_image, f"tmp/{self.tab_name}.png")
                        
                        # 在主線程中更新預覽
                        self.parent.after(0, self._update_preview)
                    else:
                        self.latest_image = None
                        self.parent.after(0, lambda: self.preview_widget.set_message("擷取失敗"))
                else:
                    self.parent.after(0, lambda: self.preview_widget.set_message("請選擇視窗和設定區域"))

            except Exception as e:
                logger.error(f"{self.tab_name} 擷取錯誤: {e}")
            time.sleep(1 /  float(self.capture_manager.capture_fps) if self.capture_manager.capture_fps else 0.1)
        
        # 清理資源
        self.capture_manager.cleanup_resources()
    
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
