import re
from typing import Optional, List, Tuple
from collections import deque
from module.monitor_timer import MonitorTimer

class CoinManager:
    """負責處理Coin相關邏輯"""
    
    def __init__(self):
        self.coin = None
        self.last_valid_coin = None  # 記錄最後一次有效的楓幣值
        self.coin_history = deque(maxlen=600)  # 10分鐘，每秒一筆
        self.timer = MonitorTimer()  # 使用MonitorTimer管理時間
        self.start_coin_value = None  # int or None

    def start_tracking(self):
        """開始追蹤楓幣"""
        self.timer.start_tracking()
        coin_value = self._parse_coin_value(self.coin) if self.coin else None
        self.start_coin_value = coin_value
        # 清空歷史記錄
        self.coin_history.clear()
        if coin_value is not None:
            self.coin_history.append((self.timer.start_time, coin_value))

    def pause_tracking(self):
        """暫停追蹤楓幣"""
        self.timer.pause_tracking()

    def resume_tracking(self):
        """恢復追蹤楓幣"""
        self.timer.resume_tracking()

    def stop_tracking(self):
        """停止追蹤楓幣"""
        self.timer.stop_tracking()

    def reset_tracking(self):
        """重置追蹤"""
        self.timer.reset_tracking()
        self.start_coin_value = None
        self.coin_history.clear()

    def update(self, coin_value: str):
        """更新楓幣值"""
        # 檢查新的楓幣值是否有效
        value = self._parse_coin_value(coin_value)
        
        # 如果新值有效，更新楓幣值和最後有效值
        if value is not None:
            self.coin = coin_value
            self.last_valid_coin = coin_value
        else:
            # 如果新值無效，保持原有的 coin 值但使用最後有效值進行計算
            self.coin = coin_value  # 保存原始值用於顯示
        
        if self.timer.is_tracking and not self.timer.is_paused:
            # 使用計時器基準時間，而非直接使用 time.time()
            current_effective_time = self._get_current_effective_time()
            
            # 使用最後有效的楓幣值進行計算
            calc_value = self._get_valid_coin_value()
            
            if calc_value is not None:
                # 僅每秒保留一筆資料，使用有效時間計算
                if not self.coin_history or int(current_effective_time) > int(self.coin_history[-1][0]):
                    self.coin_history.append((current_effective_time, calc_value))
                    self.timer.update_last_update_time()
                
                # 如果這是第一次有效的楓幣值，設為起始值
                if self.start_coin_value is None and calc_value is not None:
                    self.start_coin_value = calc_value
                if self.timer.start_time is None:
                    self.timer.start_time = current_effective_time

    def _get_current_effective_time(self) -> float:
        """獲取當前有效時間（基於計時器的時間基準）"""
        if not self.timer.is_tracking or self.timer.start_time is None:
            return 0.0
        
        elapsed = self.timer.get_elapsed_time()
        if elapsed is None:
            return self.timer.start_time
        
        # 返回基於起始時間加上有效經過時間的時間點
        return self.timer.start_time + elapsed

    def _get_valid_coin_value(self) -> Optional[int]:
        """獲取有效的楓幣值（優先使用最後有效值）"""
        if self.last_valid_coin:
            return self._parse_coin_value(self.last_valid_coin)
        return self._parse_coin_value(self.coin) if self.coin else None

    def _parse_coin_value(self, value: str) -> Optional[int]:
        """
        解析楓幣值，回傳 coin_value
        coin_value: int (e.g. 123,456,789 -> 123456789)
        """
        if not value or value == "N/A":
            return None
            
        try:
            # 移除所有非數字字符（包括逗號、空格等）
            cleaned_value = re.sub(r'[^\d]', '', value)
            if cleaned_value:
                return int(cleaned_value)
            return None
        except (ValueError, AttributeError):
            return None

    def get_elapsed_time(self) -> Optional[float]:
        """獲取已經過時間（秒），排除暫停時間"""
        return self.timer.get_elapsed_time()

    def _get_current_coin_value(self) -> Optional[int]:
        """獲取當前楓幣值"""
        return self._get_valid_coin_value()

    def _calculate_total_coin(self) -> Optional[int]:
        """計算總累計楓幣"""
        cur_value = self._get_current_coin_value()
        
        total_coin_value = None
        if cur_value is not None and self.start_coin_value is not None:
            total_coin_value = cur_value - self.start_coin_value
            
        return total_coin_value

    def _calculate_10min_coin_projected(self, elapsed_time: float) -> Optional[int]:
        """計算投影的10分鐘楓幣（不足10分鐘時使用）"""
        cur_value = self._get_current_coin_value()
        
        if self.start_coin_value is not None and cur_value is not None:
            value_diff = cur_value - self.start_coin_value
            projected_value = int(value_diff / elapsed_time * 600) if value_diff is not None else None
            return projected_value
        return None

    def _calculate_10min_coin_actual(self) -> Optional[int]:
        """計算實際10分鐘楓幣（超過10分鐘時使用）"""
        current_effective_time = self._get_current_effective_time()
        target_time = current_effective_time - 600  # 10分鐘前（基於有效時間）
        cur_value = self._get_current_coin_value()
        
        # 找到最接近10分鐘前的記錄
        past_value = None
        for timestamp, value in self.coin_history:
            if timestamp >= target_time:
                past_value = value
                break
                
        value_diff = (cur_value - past_value) if (cur_value is not None and past_value is not None) else None
        
        return value_diff

    def get_coin_per_10min_data(self) -> Tuple[Optional[int], Optional[int]]:
        """
        計算10分鐘楓幣量和總累計楓幣數據
        Returns:
            Tuple[10分鐘楓幣值, 總累計楓幣值]
        """
        if not self.timer.is_tracking or not self.coin_history:
            return None, None
            
        cur_value = self._get_current_coin_value()
        if cur_value is None:
            return None, None
            
        elapsed_time = self.get_elapsed_time()
        if elapsed_time is None or elapsed_time < 1:
            return None, None
        
        # 計算總累計楓幣
        total_coin_value = self._calculate_total_coin()
        
        # 計算10分鐘楓幣
        if elapsed_time < 600:  # 600秒 = 10分鐘
            projected_value = self._calculate_10min_coin_projected(elapsed_time)
            coin_10min_data = projected_value
        else:
            value_diff = self._calculate_10min_coin_actual()
            coin_10min_data = value_diff
        
        return coin_10min_data, total_coin_value

    def get_coin_per_10min(self) -> Tuple[Optional[str], Optional[str]]:
        """
        計算10分鐘楓幣量和總累計楓幣（保持向後兼容）
        Returns:
            Tuple[10分鐘楓幣文字, 總累計楓幣文字]
        """
        coin_10min_data, total_coin_data = self.get_coin_per_10min_data()
        
        if coin_10min_data is None or total_coin_data is None:
            return None, None
            
        # 格式化10分鐘楓幣
        coin_10min_text = None
        if coin_10min_data is not None:
            coin_10min_text = f"10分鐘楓幣:{coin_10min_data:,}"
            
        # 格式化總累計楓幣
        total_coin_text = None
        if total_coin_data is not None:
            total_coin_text = f"總累計楓幣:{total_coin_data:,}"
        
        return coin_10min_text, total_coin_text

    def get_status(self):
        coin_per_10min, total_coin = self.get_coin_per_10min()
        coin_10min_data, total_coin_data = self.get_coin_per_10min_data()
        elapsed_time = self.get_elapsed_time()
        cur_value = self._get_current_coin_value()
        timer_status = self.timer.get_status()
        
        return {
            "Coin": self.coin,
            "is_tracking": timer_status["is_tracking"],
            "is_paused": timer_status["is_paused"],
            "elapsed_time": elapsed_time,
            "coin_per_10min": coin_per_10min,
            "total_coin": total_coin,
            "coin_10min_data": coin_10min_data,
            "total_coin_data": total_coin_data,
            "start_coin_value": self.start_coin_value,
            "current_coin_value": cur_value,
            "timer_status": timer_status
        }
