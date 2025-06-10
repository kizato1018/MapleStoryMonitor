"""
Configuration Manager Module
配置管理模組
"""

import json
import os
from typing import Dict, Any, Optional
from utils.log import get_logger

logger = get_logger(__name__)


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: str = "game_monitor_config.json"):
        self.config_file = config_file
        self.config_data = {}
        # 不在初始化時載入預設配置，而是在需要時載入
    
    def _get_default_config(self) -> Dict[str, Any]:
        """獲取預設配置"""
        with open("config/default_config.json", 'r', encoding='utf-8') as f:
            loaded_config = json.load(f)
        return loaded_config
    
    def load_config(self) -> bool:
        """
        從檔案載入配置
        
        Returns:
            bool: 載入是否成功
        """
        # 先載入預設配置
        self.config_data = self._get_default_config()
        
        if not os.path.exists(self.config_file):
            logger.info("配置檔案不存在，使用預設配置")
            return True
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
            
            # 合併載入的配置與預設配置
            self._merge_config(loaded_config)
            # logger.info(f"成功載入配置檔案: {self.config_file}")  # 移除重複log，交由呼叫端記錄
            return True
            
        except Exception as e:
            logger.error(f"載入配置檔案失敗: {e}")
            return False
    
    def save_config(self) -> bool:
        """
        儲存配置到檔案
        
        Returns:
            bool: 儲存是否成功
        """
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=2, ensure_ascii=False)
            return True
            
        except Exception as e:
            logger.error(f"儲存配置檔案失敗: {e}")
            return False
    
    def _merge_config(self, loaded_config: Dict[str, Any]) -> None:
        """
        合併載入的配置與預設配置
        
        Args:
            loaded_config: 從檔案載入的配置
        """
        # 遞歸合併配置
        def merge_dict(default: Dict, loaded: Dict) -> Dict:
            result = default.copy()
            for key, value in loaded.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = merge_dict(result[key], value)
                else:
                    result[key] = value
            return result
        
        self.config_data = merge_dict(self.config_data, loaded_config)
    
    def get_global_config(self) -> Dict[str, Any]:
        """獲取全域配置"""
        return self.config_data.get("global", {})
    
    def set_global_config(self, key: str, value: Any) -> None:
        """設定全域配置"""
        if "global" not in self.config_data:
            self.config_data["global"] = {}
        self.config_data["global"][key] = value
    
    def get_tab_config(self, tab_name: str) -> Optional[Dict[str, Any]]:
        """
        獲取標籤頁配置
        
        Args:
            tab_name: 標籤頁名稱
        
        Returns:
            dict: 標籤頁配置，如果不存在則返回None
        """
        return self.config_data.get("tabs", {}).get(tab_name)
    
    def set_tab_config(self, tab_name: str, config: Dict[str, Any]) -> None:
        """
        設定標籤頁配置
        
        Args:
            tab_name: 標籤頁名稱
            config: 標籤頁配置
        """
        if "tabs" not in self.config_data:
            self.config_data["tabs"] = {}
        self.config_data["tabs"][tab_name] = config
    
    def get_tab_region(self, tab_name: str) -> Optional[Dict[str, int]]:
        """
        獲取標籤頁區域配置
        
        Args:
            tab_name: 標籤頁名稱
        
        Returns:
            dict: 區域配置 {'x': int, 'y': int, 'w': int, 'h': int}
        """
        tab_config = self.get_tab_config(tab_name)
        if tab_config:
            return {
                'x': tab_config.get('x', 0),
                'y': tab_config.get('y', 0),
                'w': tab_config.get('w', 100),
                'h': tab_config.get('h', 30)
            }
        return None
    
    def set_tab_region(self, tab_name: str, x: int, y: int, w: int, h: int) -> None:
        """
        設定標籤頁區域配置
        
        Args:
            tab_name: 標籤頁名稱
            x, y, w, h: 區域座標和尺寸
        """
        tab_config = self.get_tab_config(tab_name) or {}
        tab_config.update({'x': x, 'y': y, 'w': w, 'h': h})
        self.set_tab_config(tab_name, tab_config)
    
    def get_fps(self) -> float:
        """獲取FPS設定"""
        return self.get_global_config().get("fps", 5.0)
    
    def set_fps(self, fps: float) -> None:
        """設定FPS"""
        self.set_global_config("fps", fps)
    
    def get_window_title(self) -> str:
        """獲取視窗標題"""
        return self.get_global_config().get("window_title", "")
    
    def set_window_title(self, title: str) -> None:
        """設定視窗標題"""
        self.set_global_config("window_title", title)
    
    def get_ocr_allow_list(self) -> str:
        """獲取OCR允許字符列表"""
        return self.get_global_config().get("ocr_allow_list", "0123456789.[]/%")
    
    def set_ocr_allow_list(self, allow_list: str) -> None:
        """設定OCR允許字符列表"""
        self.set_global_config("ocr_allow_list", allow_list)
    
    def get_auto_update(self) -> bool:
        """獲取自動更新設定"""
        return self.get_global_config().get("auto_update", True)
    
    def set_auto_update(self, auto_update: bool) -> None:
        """設定自動更新"""
        self.set_global_config("auto_update", auto_update)
    
    def get_window_size(self) -> Dict[str, int]:
        """獲取視窗大小設定"""
        return self.get_global_config().get("window_size", {"width": 380, "height": 700})
    
    def set_window_size(self, width: int, height: int) -> None:
        """設定視窗大小"""
        self.set_global_config("window_size", {"width": width, "height": height})
    
    def get_window_position(self) -> Dict[str, int]:
        """獲取視窗位置設定"""
        return self.get_global_config().get("window_position", {"x": 100, "y": 100})
    
    def set_window_position(self, x: int, y: int) -> None:
        """設定視窗位置"""
        self.set_global_config("window_position", {"x": x, "y": y})
