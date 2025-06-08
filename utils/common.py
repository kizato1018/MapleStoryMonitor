"""
Common Utilities Module
共用工具函數模組
"""

import threading
import time
from typing import Any, Callable, Optional
from utils.log import get_logger

logger = get_logger(__name__)


def safe_call(func: Callable, *args, **kwargs) -> Any:
    """
    安全調用函數，捕獲異常
    
    Args:
        func: 要調用的函數
        *args: 位置參數
        **kwargs: 關鍵字參數
    
    Returns:
        函數返回值，如果發生異常則返回None
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"安全調用錯誤 {func.__name__}: {e}")
        return None


def create_daemon_thread(target: Callable, *args, **kwargs) -> threading.Thread:
    """
    創建守護進程線程
    
    Args:
        target: 目標函數
        *args: 位置參數
        **kwargs: 關鍵字參數
    
    Returns:
        threading.Thread: 配置好的線程對象
    """
    thread = threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True)
    return thread


class PerformanceTimer:
    """性能計時器"""
    
    def __init__(self, name: str = "Timer"):
        self.name = name
        self.start_time = None
        self.end_time = None
    
    def start(self) -> None:
        """開始計時"""
        self.start_time = time.time()
    
    def stop(self) -> float:
        """
        停止計時
        
        Returns:
            float: 經過的時間（秒）
        """
        self.end_time = time.time()
        if self.start_time is None:
            return 0.0
        return self.end_time - self.start_time
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = self.stop()
        logger.debug(f"{self.name}: {elapsed:.4f}秒")


class FrequencyController:
    """頻率控制器"""
    
    def __init__(self, fps: float = 5.0):
        self.fps = fps
        self.last_time = 0.0
    
    def set_fps(self, fps: float) -> None:
        """設定FPS"""
        self.fps = max(0.1, fps)  # 最小0.1 FPS
    
    def wait(self) -> None:
        """等待到下一個幀時間"""
        if self.fps <= 0:
            return
        
        current_time = time.time()
        frame_time = 1.0 / self.fps
        elapsed = current_time - self.last_time
        
        if elapsed < frame_time:
            sleep_time = frame_time - elapsed
            time.sleep(sleep_time)
        
        self.last_time = time.time()
    
    def should_process(self) -> bool:
        """
        檢查是否應該處理下一幀
        
        Returns:
            bool: 是否應該處理
        """
        if self.fps <= 0:
            return True
        
        current_time = time.time()
        frame_time = 1.0 / self.fps
        elapsed = current_time - self.last_time
        
        if elapsed >= frame_time:
            self.last_time = current_time
            return True
        
        return False


def clamp(value: float, min_val: float, max_val: float) -> float:
    """
    將值限制在指定範圍內
    
    Args:
        value: 要限制的值
        min_val: 最小值
        max_val: 最大值
    
    Returns:
        float: 限制後的值
    """
    return max(min_val, min(value, max_val))


def format_size(size: int) -> str:
    """
    格式化檔案大小
    
    Args:
        size: 檔案大小（字節）
    
    Returns:
        str: 格式化後的大小字符串
    """
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    return f"{size:.2f} {units[unit_index]}"


def validate_region(x: int, y: int, w: int, h: int, 
                   max_width: Optional[int] = None, 
                   max_height: Optional[int] = None) -> tuple:
    """
    驗證並修正區域座標
    
    Args:
        x, y: 區域左上角座標
        w, h: 區域寬度和高度
        max_width, max_height: 最大寬度和高度限制
    
    Returns:
        tuple: 修正後的 (x, y, w, h)
    """
    # 確保座標為非負數
    x = max(0, x)
    y = max(0, y)
    w = max(1, w)  # 寬度至少為1
    h = max(1, h)  # 高度至少為1
    
    # 應用最大尺寸限制
    if max_width is not None:
        if x + w > max_width:
            w = max_width - x
        w = max(1, w)
    
    if max_height is not None:
        if y + h > max_height:
            h = max_height - y
        h = max(1, h)
    
    return x, y, w, h


class FuzzySearchMatcher:
    """模糊搜尋匹配器"""
    
    def __init__(self, confidence_threshold: float = 0.8):
        """
        初始化模糊搜尋匹配器
        
        Args:
            confidence_threshold: 信心度閾值 (0.0-1.0)
        """
        self.confidence_threshold = max(0.0, min(1.0, confidence_threshold))
    
    def calculate_fuzzy_score(self, search_text: str, target_text: str) -> float:
        """
        計算模糊匹配分數 (0.0-1.0)
        
        Args:
            search_text: 搜尋文字
            target_text: 目標文字
            
        Returns:
            float: 匹配分數 (0.0-1.0)
        """
        if not search_text or not target_text:
            return 0.0
        
        search_text = search_text.lower()
        target_text = target_text.lower()
        
        # 完全匹配給最高分
        if search_text == target_text:
            return 1.0
        
        # 包含完整搜尋文字給高分
        if search_text in target_text:
            return self._calculate_substring_score(search_text, target_text)
        
        # 字符序列匹配分數
        char_score = self._calculate_character_score(search_text, target_text)
        
        # 單詞邊界匹配分數
        word_score = self._calculate_word_boundary_score(search_text, target_text)
        
        return max(char_score, word_score)
    
    def _calculate_substring_score(self, search_text: str, target_text: str) -> float:
        """計算子字符串匹配分數"""
        position = target_text.find(search_text)
        position_bonus = max(0, 0.3 - position * 0.02)  # 位置越前分數越高
        length_ratio = len(search_text) / len(target_text)  # 搜尋文字佔目標的比例
        base_score = 0.7 + position_bonus + length_ratio * 0.2
        return min(0.99, base_score)  # 不完全匹配最高0.99
    
    def _calculate_character_score(self, search_text: str, target_text: str) -> float:
        """計算字符序列匹配分數"""
        search_chars = list(search_text)
        target_chars = list(target_text)
        
        matched_chars = 0
        search_index = 0
        
        for target_char in target_chars:
            if search_index < len(search_chars) and target_char == search_chars[search_index]:
                matched_chars += 1
                search_index += 1
        
        if matched_chars == 0:
            return 0.0
        
        # 基於匹配字符數和順序的分數
        sequence_score = (matched_chars / len(search_chars)) * 0.4
        
        # 額外分數：如果匹配的字符是連續的
        continuous_bonus = 0.2 if matched_chars == len(search_chars) else 0
        
        return sequence_score + continuous_bonus
    
    def _calculate_word_boundary_score(self, search_text: str, target_text: str) -> float:
        """計算單詞邊界匹配分數"""
        # 將目標文字按分隔符分割成單詞
        words = target_text.replace('_', ' ').replace('-', ' ').split()
        
        for word in words:
            if word.startswith(search_text):
                return 0.6
            elif search_text in word:
                return 0.4
        
        return 0.0
    
    def find_best_matches(self, search_text: str, candidates: list, 
                         key_func: callable = None) -> list:
        """
        在候選列表中找到最佳匹配
        
        Args:
            search_text: 搜尋文字
            candidates: 候選列表
            key_func: 從候選項提取搜尋目標文字的函數
            
        Returns:
            list: 匹配結果列表，每項包含 (index, score, candidate)
        """
        if not search_text or not candidates:
            return []
        
        matches = []
        for i, candidate in enumerate(candidates):
            target_text = key_func(candidate) if key_func else str(candidate)
            score = self.calculate_fuzzy_score(search_text, target_text)
            
            if score >= self.confidence_threshold:
                matches.append((i, score, candidate))
        
        # 按分數排序（分數越高越好）
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches
    
    def find_best_match(self, search_text: str, candidates: list, 
                       key_func: callable = None) -> tuple:
        """
        找到單個最佳匹配
        
        Args:
            search_text: 搜尋文字
            candidates: 候選列表
            key_func: 從候選項提取搜尋目標文字的函數
            
        Returns:
            tuple: (index, score, candidate) 或 (None, 0.0, None)
        """
        matches = self.find_best_matches(search_text, candidates, key_func)
        return matches[0] if matches else (None, 0.0, None)
    
    def set_confidence_threshold(self, threshold: float) -> None:
        """設定信心度閾值"""
        self.confidence_threshold = max(0.0, min(1.0, threshold))
