import time
import re
from typing import Optional, List, Tuple
from collections import deque

class EXPManager:
    """負責處理EXP相關邏輯"""
    
    def __init__(self):
        self.exp = None
        self.last_valid_exp = None  # 記錄最後一次有效的經驗值
        self.exp_history = deque(maxlen=600)  # 10分鐘，每秒一筆
        self.start_time = None
        self.start_exp_value = None  # int or None
        self.start_exp_percent = None
        self.is_tracking = False
        self.is_paused = False  # 新增暫停狀態
        self.last_update_time = None
        self.paused_time = 0  # 累計暫停的時間
        self.pause_start_time = None  # 暫停開始時間

    def start_tracking(self):
        """開始追蹤經驗"""
        current_time = time.time()
        self.start_time = current_time
        exp_value, exp_percent = self._parse_exp_value(self.exp) if self.exp else (None, None)
        self.start_exp_value = exp_value
        self.start_exp_percent = exp_percent
        self.is_tracking = True
        self.is_paused = False
        self.paused_time = 0
        self.pause_start_time = None
        # 清空歷史記錄
        self.exp_history.clear()
        if exp_value is not None or exp_percent is not None:
            self.exp_history.append((current_time, exp_value, exp_percent))

    def pause_tracking(self):
        """暫停追蹤經驗"""
        if self.is_tracking and not self.is_paused:
            self.is_paused = True
            self.pause_start_time = time.time()

    def resume_tracking(self):
        """恢復追蹤經驗"""
        if self.is_tracking and self.is_paused:
            self.is_paused = False
            if self.pause_start_time is not None:
                self.paused_time += time.time() - self.pause_start_time
                self.pause_start_time = None

    def stop_tracking(self):
        """停止追蹤經驗"""
        self.is_tracking = False
        self.is_paused = False
        self.paused_time = 0
        self.pause_start_time = None

    def reset_tracking(self):
        """重置追蹤"""
        self.start_time = None
        self.start_exp_value = None
        self.start_exp_percent = None
        self.is_tracking = False
        self.is_paused = False
        self.exp_history.clear()
        self.last_update_time = None
        self.paused_time = 0
        self.pause_start_time = None

    def update(self, exp_value: str):
        """更新經驗值"""
        # 檢查新的經驗值是否有效
        value, percent = self._parse_exp_value(exp_value)
        
        # 如果新值有效，更新經驗值和最後有效值
        if value is not None or percent is not None:
            self.exp = exp_value
            self.last_valid_exp = exp_value
        else:
            # 如果新值無效，保持原有的 exp 值但使用最後有效值進行計算
            self.exp = exp_value  # 保存原始值用於顯示
        
        if self.is_tracking and not self.is_paused:
            current_time = time.time()
            
            # 使用最後有效的經驗值進行計算
            calc_value, calc_percent = self._get_valid_exp_values()
            
            if calc_value is not None or calc_percent is not None:
                # 僅每秒保留一筆資料
                if not self.exp_history or int(current_time) > int(self.exp_history[-1][0]):
                    self.exp_history.append((current_time, calc_value, calc_percent))
                    self.last_update_time = current_time
                
                # 如果這是第一次有效的經驗值，設為起始值
                if self.start_exp_value is None and calc_value is not None:
                    self.start_exp_value = calc_value
                if self.start_exp_percent is None and calc_percent is not None:
                    self.start_exp_percent = calc_percent
                if self.start_time is None:
                    self.start_time = current_time

    def _get_valid_exp_values(self) -> Tuple[Optional[int], Optional[float]]:
        """獲取有效的經驗值和百分比（優先使用最後有效值）"""
        if self.last_valid_exp:
            return self._parse_exp_value(self.last_valid_exp)
        return self._parse_exp_value(self.exp) if self.exp else (None, None)

    def _parse_exp_value(self, value: str) -> Tuple[Optional[int], Optional[float]]:
        """
        解析經驗值，回傳 (exp_value, exp_percent)
        exp_value: int
        exp_percent: float
        """
        if not value or value == "N/A":
            return None, None
            
        try:
            value = value.replace(" ", "")
            # 百分比
            percent_patterns = [
                r'[\[\(](\d+\.?\d*)%',     # [20.3%
                r'/(\d+\.?\d*)%',          # /20.3%
                r'[\[\(](\d+\.?\d*)[%）\]]', # [20.3% 或 [20.3] 或 [20.3）
                r'/(\d+\.?\d*)[%）\]7]',   # /20.3% 或 /20.3] 或 /20.37
                r'(\d+\.?\d*)%',           # 20.3%
            ]
            percent_value = None
            for pattern in percent_patterns:
                match = re.search(pattern, value)
                if match:
                    percent_value = float(match.group(1))
                    break
            # 數值部分（取第一個數字，轉為int）
            number_match = re.search(r'(\d+)', value)
            value_num = int(number_match.group(1)) if number_match else None
            return value_num, percent_value
        except (ValueError, AttributeError):
            return None, None

    def get_elapsed_time(self) -> Optional[float]:
        """獲取已經過時間（秒），排除暫停時間"""
        if not self.is_tracking or self.start_time is None:
            return None
        
        current_time = time.time()
        total_paused = self.paused_time
        
        # 如果目前正在暫停，加上當前暫停時間
        if self.is_paused and self.pause_start_time is not None:
            total_paused += current_time - self.pause_start_time
        
        return current_time - self.start_time - total_paused

    def _get_current_exp_values(self) -> Tuple[Optional[int], Optional[float]]:
        """獲取當前經驗值和百分比"""
        return self._get_valid_exp_values()

    def _calculate_total_exp(self) -> Tuple[Optional[int], Optional[float]]:
        """計算總累計經驗"""
        cur_value, cur_percent = self._get_current_exp_values()
        
        total_exp_value = None
        total_exp_percent = None
        if cur_value is not None and self.start_exp_value is not None:
            total_exp_value = cur_value - self.start_exp_value
        if cur_percent is not None and self.start_exp_percent is not None:
            total_exp_percent = cur_percent - self.start_exp_percent
            
        return total_exp_value, total_exp_percent

    def _calculate_10min_exp_projected(self, elapsed_time: float) -> Tuple[Optional[int], Optional[float]]:
        """計算投影的10分鐘經驗（不足10分鐘時使用）"""
        cur_value, cur_percent = self._get_current_exp_values()
        
        if self.start_exp_value is not None or self.start_exp_percent is not None:
            value_diff = (cur_value - self.start_exp_value) if (cur_value is not None and self.start_exp_value is not None) else None
            percent_diff = (cur_percent - self.start_exp_percent) if (cur_percent is not None and self.start_exp_percent is not None) else None
            
            projected_value = int(value_diff / elapsed_time * 600) if value_diff is not None else None
            projected_percent = percent_diff / elapsed_time * 600 if percent_diff is not None else None
            
            return projected_value, projected_percent
        return None, None

    def _calculate_10min_exp_actual(self) -> Tuple[Optional[int], Optional[float]]:
        """計算實際10分鐘經驗（超過10分鐘時使用）"""
        current_time = time.time()
        target_time = current_time - 600  # 10分鐘前
        cur_value, cur_percent = self._get_current_exp_values()
        
        # 找到最接近10分鐘前的記錄
        past_value = None
        past_percent = None
        for timestamp, value, percent in self.exp_history:
            if timestamp >= target_time:
                past_value = value
                past_percent = percent
                break
                
        value_diff = (cur_value - past_value) if (cur_value is not None and past_value is not None) else None
        percent_diff = (cur_percent - past_percent) if (cur_percent is not None and past_percent is not None) else None
        
        return value_diff, percent_diff

    def get_exp_per_10min_data(self) -> Tuple[Optional[Tuple[Optional[int], Optional[float]]], Optional[Tuple[Optional[int], Optional[float]]]]:
        """
        計算10分鐘經驗量和總累計經驗數據
        Returns:
            Tuple[(10分鐘經驗值, 10分鐘經驗百分比), (總累計經驗值, 總累計經驗百分比)]
        """
        if not self.is_tracking or not self.exp_history:
            return None, None
            
        cur_value, cur_percent = self._get_current_exp_values()
        if cur_value is None and cur_percent is None:
            return None, None
            
        elapsed_time = self.get_elapsed_time()
        if elapsed_time is None or elapsed_time < 1:
            return None, None
        
        # 計算總累計經驗
        total_exp_value, total_exp_percent = self._calculate_total_exp()
        
        # 計算10分鐘經驗
        if elapsed_time < 600:  # 600秒 = 10分鐘
            projected_value, projected_percent = self._calculate_10min_exp_projected(elapsed_time)
            exp_10min_data = (projected_value, projected_percent)
        else:
            value_diff, percent_diff = self._calculate_10min_exp_actual()
            exp_10min_data = (value_diff, percent_diff)
        
        total_exp_data = (total_exp_value, total_exp_percent)
        return exp_10min_data, total_exp_data

    def get_exp_per_10min(self) -> Tuple[Optional[str], Optional[str]]:
        """
        計算10分鐘經驗量和總累計經驗（保持向後兼容）
        Returns:
            Tuple[10分鐘經驗文字, 總累計經驗文字]
        """
        exp_10min_data, total_exp_data = self.get_exp_per_10min_data()
        
        if exp_10min_data is None or total_exp_data is None:
            return None, None
            
        # 格式化10分鐘經驗
        exp_10min_value, exp_10min_percent = exp_10min_data
        exp_10min_text = None
        if exp_10min_value is not None and exp_10min_percent is not None:
            exp_10min_text = f"10分鐘經驗:{exp_10min_value:,} ({exp_10min_percent:.2f}%)"
        elif exp_10min_percent is not None:
            exp_10min_text = f"10分鐘經驗:N/A ({exp_10min_percent:.2f}%)"
        elif exp_10min_value is not None:
            exp_10min_text = f"10分鐘經驗:{exp_10min_value:,} (N/A%)"
            
        # 格式化總累計經驗
        total_exp_value, total_exp_percent = total_exp_data
        total_exp_text = None
        if total_exp_value is not None and total_exp_percent is not None:
            total_exp_text = f"總累計經驗:{total_exp_value:,} ({total_exp_percent:.2f}%)"
        elif total_exp_percent is not None:
            total_exp_text = f"總累計經驗:N/A ({total_exp_percent:.2f}%)"
        elif total_exp_value is not None:
            total_exp_text = f"總累計經驗:{total_exp_value:,} (N/A%)"
        
        return exp_10min_text, total_exp_text

    def get_estimated_levelup_time_data(self) -> Optional[Tuple[int, int, int]]:
        """
        計算預估升級時間數據
        Returns:
            Optional[Tuple[hours, minutes, seconds]]
        """
        if not self.is_tracking or not self.exp_history:
            return None
            
        cur_value, cur_percent = self._get_current_exp_values()
        if cur_percent is None:
            return None
            
            
        # 獲取10分鐘經驗百分比
        exp_10min_data, _ = self.get_exp_per_10min_data()
        if not exp_10min_data:
            return None
            
        exp_10min_value, exp_10min_percent = exp_10min_data
        if exp_10min_percent is None or exp_10min_percent <= 0:
            return None
            
        try:
            remaining_percent = 100.0 - cur_percent
            
            # 計算: 剩餘百分比 / (10分鐘經驗百分比 / 600秒) = 預估秒數
            estimated_seconds = remaining_percent / (exp_10min_percent / 600)
            
            # 轉換為時分秒
            hours = int(estimated_seconds // 3600)
            minutes = int((estimated_seconds % 3600) // 60)
            seconds = int(estimated_seconds % 60)
            
            return (hours, minutes, seconds)
                
        except (ValueError, ZeroDivisionError):
            return None

    def get_estimated_levelup_time(self) -> Optional[str]:
        """計算預估升級時間（保持向後兼容）"""
        time_data = self.get_estimated_levelup_time_data()
        if time_data is None:
            return "數據不足"
            
        hours, minutes, seconds = time_data
        
        if hours > 0:
            return f"預估升級時間: {hours}小時{minutes}分{seconds}秒"
        elif minutes > 0:
            return f"預估升級時間: {minutes}分{seconds}秒"
        else:
            return f"預估升級時間: {seconds}秒"

    def get_status(self):
        exp_per_10min, total_exp = self.get_exp_per_10min()
        exp_10min_data, total_exp_data = self.get_exp_per_10min_data()
        estimated_levelup = self.get_estimated_levelup_time()
        estimated_levelup_data = self.get_estimated_levelup_time_data()
        elapsed_time = self.get_elapsed_time()
        cur_value, cur_percent = self._get_current_exp_values()
        
        return {
            "EXP": self.exp,
            "is_tracking": self.is_tracking,
            "is_paused": self.is_paused,
            "elapsed_time": elapsed_time,
            "exp_per_10min": exp_per_10min,
            "total_exp": total_exp,
            "exp_10min_data": exp_10min_data,
            "total_exp_data": total_exp_data,
            "estimated_levelup": estimated_levelup,
            "estimated_levelup_data": estimated_levelup_data,
            "start_exp_value": self.start_exp_value,
            "start_exp_percent": self.start_exp_percent,
            "current_exp_value": cur_value,
            "current_exp_percent": cur_percent
        }
