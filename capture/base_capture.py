"""
Base Capture Module
抽象基類定義捕捉介面
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Tuple
from PIL import Image


class BaseCaptureEngine(ABC):
    """捕捉引擎抽象基類"""
    
    def __init__(self):
        self.is_initialized = False
        self.current_resources = None
    
    @abstractmethod
    def initialize_resources(self, window_handle: Any, region: Dict[str, int]) -> bool:
        """
        初始化捕捉資源
        
        Args:
            window_handle: 視窗控制代碼（Windows為HWND，Mac為其他格式）
            region: 捕捉區域 {'x': int, 'y': int, 'w': int, 'h': int}
        
        Returns:
            bool: 初始化是否成功
        """
        pass
    
    @abstractmethod
    def capture_region(self) -> Optional[Image.Image]:
        """
        捕捉指定區域
        
        Returns:
            PIL.Image: 捕捉到的圖像，失敗時返回None
        """
        pass
    
    @abstractmethod
    def cleanup_resources(self) -> None:
        """清理捕捉資源"""
        pass
    
    @abstractmethod
    def is_window_valid(self, window_handle: Any) -> bool:
        """
        檢查視窗是否有效
        
        Args:
            window_handle: 視窗控制代碼
        
        Returns:
            bool: 視窗是否有效
        """
        pass
    
    @abstractmethod
    def get_window_list(self) -> list:
        """
        獲取系統視窗列表
        
        Returns:
            list: 視窗列表，格式為[(handle, title), ...]
        """
        pass
    
    @abstractmethod
    def get_window_rect(self, window_handle: Any) -> Optional[Tuple[int, int, int, int]]:
        """
        獲取視窗矩形區域
        
        Args:
            window_handle: 視窗控制代碼
        
        Returns:
            tuple: (left, top, right, bottom) 或 None
        """
        pass


class CaptureFactory:
    """捕捉引擎工廠類"""
    
    @staticmethod
    def create_capture_engine() -> BaseCaptureEngine:
        """
        根據當前平台創建對應的捕捉引擎
        
        Returns:
            BaseCaptureEngine: 平台對應的捕捉引擎實例
        """
        import platform
        
        system = platform.system().lower()
        
        if system == "windows":
            from .windows_capture import WindowsCaptureEngine
            return WindowsCaptureEngine()
        elif system == "darwin":  # Mac
            from .mac_capture import MacCaptureEngine
            return MacCaptureEngine()
        else:
            raise NotImplementedError(f"不支援的平台: {system}")
