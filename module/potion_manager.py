import re
from typing import Optional, List, Tuple
from collections import deque
from module.monitor_timer import MonitorTimer

class PotionManager:
    """負責處理藥水使用量相關邏輯"""
    
    def __init__(self):
        self.potion = None
        self.last_valid_potion = None  # 記錄最後一次有效的藥水值
        self.potion_history = deque(maxlen=600)  # 10分鐘，每秒一筆
        self.timer = MonitorTimer()  # 使用MonitorTimer管理時間
        self.start_potion_value = None  # int or None
        self.total_used = 0  # 累計總使用量
        self.unit_cost = 0  # 藥水單價
        self.last_potion_value = None  # 上一次的藥水值，用於檢測補充
        self.error_threshold = 50  # 當前值小於上一次值的容錯範圍，默認為10個單位

    def start_tracking(self):
        """開始追蹤藥水使用量"""
        self.timer.start_tracking()
        potion_value = self._parse_potion_value(self.potion) if self.potion else None
        self.start_potion_value = potion_value
        self.last_potion_value = potion_value
        self.total_used = 0  # 重置累計使用量
        # 清空歷史記錄
        self.potion_history.clear()
        if potion_value is not None:
            self.potion_history.append((self.timer.start_time, self.total_used))

    def is_tracking(self) -> bool:
        """檢查是否正在追蹤藥水"""
        return self.timer.is_tracking

    def is_paused(self) -> bool:
        """檢查是否暫停追蹤藥水"""
        return self.timer.is_paused

    def pause_tracking(self):
        """暫停追蹤藥水使用量"""
        self.timer.pause_tracking()

    def resume_tracking(self):
        """恢復追蹤藥水使用量"""
        self.timer.resume_tracking()

    def stop_tracking(self):
        """停止追蹤藥水使用量"""
        self.timer.stop_tracking()

    def reset_tracking(self):
        """重置追蹤"""
        self.timer.reset_tracking()
        self.start_potion_value = None
        self.last_potion_value = None
        self.total_used = 0
        self.potion_history.clear()

    def set_unit_cost(self, cost: float):
        """設定藥水單價"""
        self.unit_cost = cost

    def update(self, potion_value: str):
        """更新藥水數量"""
        # 檢查新的藥水值是否有效
        value = self._parse_potion_value(potion_value)
        
        # 如果新值有效，更新藥水值和最後有效值
        if value is not None:
            self.potion = potion_value
            self.last_valid_potion = potion_value
        else:
            # 如果新值無效，保持原有的 potion 值但使用最後有效值進行計算
            self.potion = potion_value  # 保存原始值用於顯示
        
        if self.timer.is_tracking and not self.timer.is_paused:
            # 使用計時器基準時間，而非直接使用 time.time()
            current_effective_time = self._get_current_effective_time()
            
            # 使用最後有效的藥水值進行計算
            calc_value = self._get_valid_potion_value()
            
            if calc_value is not None:
                # 檢測補充邏輯：從0變成其他數字 = 補充3000個
                if (self.last_potion_value is not None and 
                    self.last_potion_value == 0 and 
                    calc_value > 0):
                    # 檢測到補充，累加3000個到使用量
                    self.total_used += (3000 - calc_value) 
                
                # 檢測正常使用：當前值小於上一次值
                elif (self.last_potion_value is not None and 
                      self.last_potion_value > calc_value and
                      self.last_potion_value - calc_value < self.error_threshold):
                    used_amount = self.last_potion_value - calc_value
                    self.total_used += used_amount
                
                self.last_potion_value = calc_value
                
                # 僅每秒保留一筆資料，使用有效時間計算
                if not self.potion_history or int(current_effective_time) > int(self.potion_history[-1][0]):
                    self.potion_history.append((current_effective_time, self.total_used))
                    self.timer.update_last_update_time()
                
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

    def _get_valid_potion_value(self) -> Optional[int]:
        """獲取有效的藥水值（優先使用最後有效值）"""
        if self.last_valid_potion:
            return self._parse_potion_value(self.last_valid_potion)
        return self._parse_potion_value(self.potion) if self.potion else None

    def _parse_potion_value(self, value: str) -> Optional[int]:
        """
        解析藥水值，回傳 potion_value
        potion_value: int (e.g. "2,999" -> 2999)
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

    def _get_current_potion_used(self) -> int:
        """獲取當前累計使用量"""
        return self.total_used

    def _calculate_10min_potion_projected(self, elapsed_time: float) -> Optional[int]:
        """計算投影的10分鐘藥水使用量（不足10分鐘時使用）"""
        if elapsed_time <= 0:
            return None
        
        current_used = self._get_current_potion_used()
        projected_value = int(current_used / elapsed_time * 600)
        return projected_value

    def _calculate_10min_potion_actual(self) -> Optional[int]:
        """計算實際10分鐘藥水使用量（超過10分鐘時使用）"""
        current_effective_time = self._get_current_effective_time()
        target_time = current_effective_time - 600  # 10分鐘前（基於有效時間）
        current_used = self._get_current_potion_used()
        
        # 找到最接近10分鐘前的記錄
        past_used = None
        for timestamp, used in self.potion_history:
            if timestamp >= target_time:
                past_used = used
                break
                
        if past_used is not None:
            return current_used - past_used
        return None

    def get_potion_per_10min_data(self) -> Tuple[Optional[int], Optional[int]]:
        """
        計算10分鐘藥水使用量和總累計使用量數據
        Returns:
            Tuple[10分鐘使用量, 總累計使用量]
        """
        if not self.timer.is_tracking or not self.potion_history:
            return None, None
            
        elapsed_time = self.get_elapsed_time()
        if elapsed_time is None or elapsed_time < 1:
            return None, None
        
        # 計算總累計使用量
        total_used = self._get_current_potion_used()
        
        # 計算10分鐘使用量
        if elapsed_time < 600:  # 600秒 = 10分鐘
            projected_value = self._calculate_10min_potion_projected(elapsed_time)
            potion_10min_data = projected_value
        else:
            value_diff = self._calculate_10min_potion_actual()
            potion_10min_data = value_diff
        
        return potion_10min_data, total_used

    def get_cost_per_10min_data(self) -> Tuple[Optional[float], Optional[float]]:
        """
        計算10分鐘成本和總累計成本數據
        Returns:
            Tuple[10分鐘成本, 總累計成本]
        """
        potion_10min_data, total_used = self.get_potion_per_10min_data()
        
        if potion_10min_data is None or total_used is None:
            return None, None
        
        cost_10min = potion_10min_data * self.unit_cost if potion_10min_data is not None else None
        total_cost = total_used * self.unit_cost
        
        return cost_10min, total_cost

    def get_potion_per_10min(self) -> Tuple[Optional[str], Optional[str]]:
        """
        計算10分鐘藥水使用量和總累計使用量（保持向後兼容）
        Returns:
            Tuple[10分鐘使用量文字, 總累計使用量文字]
        """
        potion_10min_data, total_used = self.get_potion_per_10min_data()
        
        if potion_10min_data is None or total_used is None:
            return None, None
            
        # 格式化10分鐘使用量
        potion_10min_text = None
        if potion_10min_data is not None:
            potion_10min_text = f"10分鐘使用量:{potion_10min_data:,}"
            
        # 格式化總累計使用量
        total_used_text = None
        if total_used is not None:
            total_used_text = f"總累計使用量:{total_used:,}"
        
        return potion_10min_text, total_used_text

    def get_cost_per_10min(self) -> Tuple[Optional[str], Optional[str]]:
        """
        計算10分鐘成本和總累計成本（文字格式）
        Returns:
            Tuple[10分鐘成本文字, 總累計成本文字]
        """
        cost_10min, total_cost = self.get_cost_per_10min_data()
        
        if cost_10min is None or total_cost is None:
            return None, None
            
        # 格式化10分鐘成本
        cost_10min_text = None
        if cost_10min is not None:
            cost_10min_text = f"10分鐘成本:{cost_10min:,.0f}"
            
        # 格式化總累計成本
        total_cost_text = None
        if total_cost is not None:
            total_cost_text = f"總累計成本:{total_cost:,.0f}"
        
        return cost_10min_text, total_cost_text

    def get_status(self):
        potion_per_10min, total_used = self.get_potion_per_10min()
        potion_10min_data, total_used_data = self.get_potion_per_10min_data()
        cost_per_10min, total_cost = self.get_cost_per_10min()
        cost_10min_data, total_cost_data = self.get_cost_per_10min_data()
        elapsed_time = self.get_elapsed_time()
        cur_value = self._get_valid_potion_value()
        timer_status = self.timer.get_status()
        
        return {
            "Potion": self.potion,
            "is_tracking": timer_status["is_tracking"],
            "is_paused": timer_status["is_paused"],
            "elapsed_time": elapsed_time,
            "potion_per_10min": potion_per_10min,
            "total_used": total_used,
            "potion_10min_data": potion_10min_data,
            "total_used_data": total_used_data,
            "cost_per_10min": cost_per_10min,
            "total_cost": total_cost,
            "cost_10min_data": cost_10min_data,
            "total_cost_data": total_cost_data,
            "unit_cost": self.unit_cost,
            "current_potion_value": cur_value,
            "total_used_amount": self.total_used,
            "timer_status": timer_status
        }
