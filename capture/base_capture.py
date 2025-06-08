"""
Base Capture Module
抽象基類定義捕捉介面
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Tuple
from PIL import Image
import time
import threading
from utils.log import get_logger

logger = get_logger(__name__)

class BaseCaptureEngine(ABC):
    """捕捉引擎抽象基類，支援多執行緒快取與自動更新"""

    def __init__(self):
        self.is_initialized = False
        self.current_resources = None
        self.latest_image = None
        self.cache_lock = threading.Lock()
        self.current_window_handle = None
        self.last_window_handle = None
        # 捕捉循環相關
        self.is_running = False
        self.capture_thread = None
        self.capture_lock = threading.Lock()
        self.capture_frequency = 10.0  # FPS
        self._stop_event = threading.Event()

    def initialize(self, window_handle: Any) -> bool:
        """
        初始化捕捉資源（捕捉完整視窗）
        """
        self.last_window_handle = window_handle
        self.current_window_handle = window_handle
        window_rect = self.get_window_rect(window_handle)
        if window_rect:
            full_region = {
                'x': 0,
                'y': 0,
                'w': window_rect[2] - window_rect[0],
                'h': window_rect[3] - window_rect[1]
            }
            return self.initialize_resources(window_handle, full_region)
        return False

    def set_window(self, window_handle: Any) -> bool:
        """
        設定當前捕捉的視窗
        
        Args:
            window_handle: 視窗控制代碼（Windows為HWND，Mac為其他格式）
        
        Returns:
            bool: 是否成功設定視窗
        """
        if not self.is_window_valid(window_handle):
            return False
        if self.current_window_handle == window_handle:
            return True
        self.current_window_handle = window_handle
        return self.initialize(window_handle)
    
    def cleanup(self):
        """清理捕捉資源"""
        self.current_window_handle = None
        with self.cache_lock:
            self.latest_image = None
        self.cleanup_resources()

    def get_region(self, x: int, y: int, w: int, h: int) -> Optional[Image.Image]:
        """
        從最新擷取的完整圖像中裁切指定區域
        
        Args:
            x, y: 區域左上角座標（相對於視窗）
            w, h: 區域寬度和高度
            
        Returns:
            PIL.Image: 裁切的區域圖像，失敗時返回None
        """
        with self.cache_lock:
            if self.latest_image is None:
                return None
            img_w, img_h = self.latest_image.size
            if x < 0 or y < 0 or x + w > img_w or y + h > img_h:
                raise ValueError("裁切區域超出圖像範圍")
            try:
                cropped = self.latest_image.crop((x, y, x + w, y + h))
                return cropped
            except Exception:
                return None

    def start_capture(self) -> bool:
        """
        啟動自動捕捉循環
        """
        if self.is_running:
            return True
        self.is_running = True
        self._stop_event.clear()
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        return True

    def stop_capture(self):
        """停止自動捕捉循環"""
        if not self.is_running:
            return
        self.is_running = False
        self._stop_event.set()
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=1.0)
        self.cleanup()

    def update_capture_frequency(self, fps: float):
        """更新捕捉頻率"""
        self.capture_frequency = fps

    def _capture_loop(self):
        """自動捕捉循環"""
        logger.debug("開始自動捕捉循環")
        while self.is_running and not self._stop_event.is_set():
            try:
                if not self.is_window_valid(self.current_window_handle):
                    break
                with self.capture_lock:
                    full_image = self.capture_window()
                    if full_image:
                        logger.debug(f"捕捉到新圖像: {full_image.size}")
                        with self.cache_lock:
                            self.latest_image = full_image
                    else:
                        logger.warning("捕捉失敗，將重試")
                
            except Exception as e:
                logger.error(f"捕捉循環錯誤: {e}")
            finally:
                interval = 1.0 / self.capture_frequency
                if not self._stop_event.wait(interval):
                    continue
                else:
                    break
        self.is_running = False

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
    def capture_window(self) -> Optional[Image.Image]:
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



def create_capture_engine() -> BaseCaptureEngine:
    """
    根據當前平台創建對應的捕捉引擎
    Returns:
        BaseCaptureEngine: 捕捉引擎實例
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
