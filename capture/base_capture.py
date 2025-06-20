"""
Base Capture Module
抽象基類定義捕捉介面
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Tuple
from PIL import Image
import os
import time
import numpy as np
import cv2
import threading
from utils.log import get_logger
from utils.get_scalor_factor import get_all_monitor_scales

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
        self.capture_fps = 2.0  # FPS
        self._stop_event = threading.Event()
        self.scale_factors = get_all_monitor_scales()

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

    def get_full_image(self) -> Optional[Image.Image]:
        """
        獲取最新擷取的完整圖像
        
        Returns:
            PIL.Image: 最新擷取的完整圖像，失敗時返回None
        """
        with self.cache_lock:
            return self.latest_image.copy() if self.latest_image else None

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
    def detect_region(self, tab_name: str) -> Optional[Dict[str, int]]:
        """
        根據tab_name獲取對應的捕捉區域
        Args:
            tab_name: 捕捉區域名稱
        Returns:
            Dict: 捕捉區域 {'x': int, 'y': int, 'w': int, 'h': int}
        """
        if tab_name == 'HP' or tab_name == 'MP' or tab_name == 'EXP':
            status_region = self.detect_status_region()
            if status_region:
                hp_rect, mp_rect, exp_rect = status_region
                if tab_name == 'HP':
                    return {'x': hp_rect[0], 'y': hp_rect[1], 'w': hp_rect[2], 'h': hp_rect[3]}
                elif tab_name == 'MP':
                    return {'x': mp_rect[0], 'y': mp_rect[1], 'w': mp_rect[2], 'h': mp_rect[3]}
                elif tab_name == 'EXP':
                    return {'x': exp_rect[0], 'y': exp_rect[1], 'w': exp_rect[2], 'h': exp_rect[3]}
        elif '藥水' in tab_name:
            potions_region = self.detect_potions_region()
            if potions_region:
                potion_index = int(tab_name.replace('藥水', '')) - 1
                if 0 <= potion_index < len(potions_region):
                    potion_rect = potions_region[potion_index]
                    return {'x': potion_rect[0], 'y': potion_rect[1], 'w': potion_rect[2], 'h': potion_rect[3]}
        else:
            logger.warning(f"{tab_name} 無法自動捕捉，請手動設定捕捉區域")
        return None

    def detect_status_region(self) -> Optional[Tuple[Tuple[int, int, int, int], Tuple[int, int, int, int], Tuple[int, int, int, int]]]:
        """
        獲取狀態欄圖像位置
        Returns:
            Tuple: 包含HP、MP、EXP圖像和矩形框的元組
        例如: (hp_rect, mp_rect, exp_rect)
        """
        image = np.array(self.get_full_image())
        h, w = image.shape[:2]
        top = 0.9
        bottom = 0.0
        left = 0.25
        right = 0.3
        cropped_image = image[int(h * top):int(w * (1-bottom)), int(w * left):int(w * (1-right))]
        offset_y = int(h * top)
        offset_x = int(w * left)
        # 選取紅色像素條件 (r > 220, g < 30, b < 30)
        red_mask = (cropped_image[:, :, 0] > 230) & \
                (cropped_image[:, :, 1] < 70) & \
                (cropped_image[:, :, 2] < 70)

        # 找出符合條件的紅色點座標
        coords = np.column_stack(np.where(red_mask))

        if len(coords) == 0:
            print("找不到紅色區塊")
            return cropped_image  # fallback 回原裁切圖

        # 包圍紅色點的矩形框
        y_min, x_min = coords.min(axis=0)
        y_max, x_max = coords.max(axis=0)
        bar_h = y_max - y_min
        bar_w = x_max - x_min
        hp_start_y = y_min - int(bar_h * 1.1)
        hp_end_y = y_min
        hp_start_x = x_min + int(w * 0.02)
        hp_end_x = x_max
        hp_rect = (hp_start_x + offset_x, hp_start_y + offset_y, hp_end_x - hp_start_x, bar_h)
        
        mp_start_y = hp_start_y
        mp_end_y = hp_end_y
        spacing = 0.004
        padding = 0.02
        mp_start_x = hp_end_x + int(w * (spacing + padding))
        mp_end_x = mp_start_x + int(bar_w - w * (padding))
        mp_rect = (mp_start_x + offset_x, mp_start_y + offset_y, mp_end_x - mp_start_x, bar_h)
        
        exp_start_y = hp_start_y
        exp_end_y = hp_end_y
        spacing = 0.023
        padding = 0.02
        exp_start_x = mp_end_x + int(w * (spacing + padding))
        exp_end_x = exp_start_x + int(bar_w - w * (padding))
        exp_rect = (exp_start_x + offset_x, exp_start_y + offset_y, exp_end_x - exp_start_x, bar_h)
        


        # 提取紅色區塊圖像
        # hp_img = cropped_image[hp_start_y:hp_end_y, hp_start_x:hp_end_x]
        # mp_img = cropped_image[mp_start_y:mp_end_y, mp_start_x:mp_end_x]
        # exp_img = cropped_image[exp_start_y:exp_end_y, exp_start_x:exp_end_x]
        # print(f"hp_rect: {hp_rect}, mp_rect: {mp_rect}, exp_rect: {exp_rect}")
        
        
        return hp_rect, mp_rect, exp_rect
    
    def detect_potions_region(self) -> Optional[Tuple[Tuple[int, int, int, int], ...]]:
        """
        獲取個別藥水欄圖像位置
        Returns:
            Tuple[Tuple[int, int, int, int], ...]: 藥水欄位置列表，座標為相對於完整螢幕
        """
        full_image = self.get_full_image()
        image = np.array(full_image)
        if image is None:
            
            return None
        
        # 獲取藥水框架
        potions_frame = self._detect_potions_frame(image)
        if potions_frame is None:
            return ()
        frame_x, frame_y, frame_w, frame_h = potions_frame

        # return frame_x, frame_y, frame_w, frame_h
        
        padding = (0.07, 0.04, 0.03, 0.03)  # 預設裁切比例
        top, bottom, left, right = padding
        top = int(frame_h * top)
        bottom = int(frame_h * bottom)
        left = int(frame_w * left)
        right = int(frame_w * right)

        padding_frame_x = frame_x + left
        padding_frame_y = frame_y + top
        padding_frame_w = frame_w - left - right
        padding_frame_h = frame_h - top - bottom

        # return padding_frame_x, padding_frame_y, padding_frame_w, padding_frame_h
        rows = 2  # 藥水欄行數
        cols = 4  # 藥水欄列數
        potions_spacing = (0.00, 0.02)  # 每個藥水欄之間的間距
        potions_padding = (0.02, 0.01)  # 每個藥水欄的邊緣填充
        spacing_h, spacing_w = potions_spacing
        padding_h, padding_w = potions_padding
        key_h = (padding_frame_h - (rows - 1) * spacing_h * padding_frame_h) / rows
        key_w = (padding_frame_w - (cols - 1) * spacing_w * padding_frame_w) / cols

        potion_rects = []

        for i in range(rows):
            for j in range(cols):
                y_start = int(i * (key_h + spacing_h * padding_frame_h) + padding_h * key_h)
                y_end = int(y_start + key_h - 2 * padding_h * key_h)
                x_start = int(j * (key_w + spacing_w * padding_frame_w) + padding_w * key_w)
                x_end = int(x_start + key_w - 2 * padding_w * key_w)

                potion_x = padding_frame_x + x_start
                potion_y = padding_frame_y + y_start
                potion_w = x_end - x_start
                potion_h = y_end - y_start
                
                potion_rects.append((potion_x, potion_y, potion_w, potion_h))

        return tuple(potion_rects)
    
    def _detect_potions_frame(self, image: np.ndarray) -> np.ndarray:
        """
        獲取整個藥水欄圖像
        Args:
            image: 原始圖像
        Returns:
            np.ndarray: 整個藥水欄圖像
        """
        img = image.copy()
        h, w = img.shape[:2]
        top, bottom, left, right = (0.7, 0.0, 0.8, 0.0)  # 預設裁切比例
        start_y = int(h * top)
        end_y = int(h * (1 - bottom))
        start_x = int(w * left)
        end_x = int(w * (1 - right))
        img = img[int(h * top):int(h * (1-bottom)), int(w * left):int(w * (1-right))]
        
        output = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, output = cv2.threshold(output, 254, 255, cv2.THRESH_BINARY_INV)
        
        # 洪水填充處理
        h, w = output.shape
        mask = np.zeros((h + 2, w + 2), np.uint8)
        
        threshold = 255
        for x in range(w):
            if output[0, x] == threshold:
                cv2.floodFill(output, mask, (x, 0), 0)
            if output[h - 1, x] == threshold:
                cv2.floodFill(output, mask, (x, h - 1), 0)
        for y in range(h):
            if output[y, 0] == threshold:
                cv2.floodFill(output, mask, (0, y), 0)
            if output[y, w - 1] == threshold:
                cv2.floodFill(output, mask, (w - 1, y), 0)
        
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(output, connectivity=8)
        if num_labels > 1:  # 排除背景標籤 (標籤 0)
            # 找到最大的連通區域（排除背景）
            largest_label = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
            coords = np.column_stack(np.where(labels == largest_label))
            coords = coords[:, [1, 0]]  # 轉換為 (x, y) 格式    
        else:
            coords = np.array([[0, 0]])  # 如果沒有找到連通區域，返回默認值
        x, y, w, h = cv2.boundingRect(coords)
        x += start_x
        y += start_y
        return x, y, w, h

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

    def set_capture_fps(self, fps: float):
        """更新捕捉頻率"""
        self.capture_fps = fps

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
                        if os.path.exists("tmp"):
                            full_image.save("tmp/latest_capture.png")
                    else:
                        logger.warning("捕捉失敗，將重試")
                
            except Exception as e:
                logger.error(f"捕捉循環錯誤: {e}")
            finally:
                interval = 1.0 / self.capture_fps
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
