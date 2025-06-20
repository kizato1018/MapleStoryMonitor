import re
from typing import Optional, List, Tuple
from collections import deque
from module.monitor_timer import MonitorTimer

class EXPManager:
    """負責處理EXP相關邏輯"""
    
    def __init__(self):
        self.exp = None
        self.last_valid_exp = None  # 記錄最後一次有效的經驗值
        self.exp_history = deque(maxlen=600)  # 10分鐘，每秒一筆
        self.timer = MonitorTimer()  # 使用MonitorTimer管理時間
        self.start_exp_value = None  # int or None
        self.start_exp_percent = None
        self.total_exp_value = 0
        self.total_exp_percent = 0.0

    def start_tracking(self):
        """開始追蹤經驗"""
        self.timer.start_tracking()
        self.update(self.exp)  # 確保在開始追蹤時更新一次經驗值

    def is_tracking(self) -> bool:
        """檢查是否正在追蹤經驗"""
        return self.timer.is_tracking
    def is_paused(self) -> bool:
        """檢查是否暫停追蹤經驗"""
        return self.timer.is_paused

    def pause_tracking(self):
        """暫停追蹤經驗"""
        self.timer.pause_tracking()

    def resume_tracking(self):
        """恢復追蹤經驗"""
        self.timer.resume_tracking()

    def stop_tracking(self):
        """停止追蹤經驗"""
        self.timer.stop_tracking()

    def reset_tracking(self):
        """重置追蹤"""
        self.timer.reset_tracking()
        self.start_exp_value = None
        self.start_exp_percent = None
        self.total_exp_value = 0
        self.total_exp_percent = 0.0
        self.exp_history.clear()

    def update(self, exp_text: str):
        """更新經驗值"""
        self.exp = exp_text

        if self.timer.is_tracking and not self.timer.is_paused:
            # 使用計時器基準時間，而非直接使用 time.time()
            current_effective_time = self._get_current_effective_time()
            
            # 使用最後有效的經驗值進行計算
            calc_value, calc_percent = self._get_valid_exp_values()
            
            if calc_value is not None or calc_percent is not None:
                # 僅每秒保留一筆資料，使用有效時間計算
                if not self.exp_history or int(current_effective_time) > int(self.exp_history[-1][0]):
                    if self._is_level_up(calc_percent):
                        # 如果升級，累計前一個等級的經驗並清空歷史記錄
                        if self.exp_history:
                            _, last_value, last_percent = self.exp_history[-1]
                            if last_value is not None and self.start_exp_value is not None:
                                self.total_exp_value += last_value - self.start_exp_value
                            if last_percent is not None and self.start_exp_percent is not None:
                                self.total_exp_percent += last_percent - self.start_exp_percent
                        self.exp_history.clear()
                        self.start_exp_value = calc_value
                        self.start_exp_percent = calc_percent
                    self.exp_history.append((current_effective_time, calc_value, calc_percent))
                    self.timer.update_last_update_time()
                
                # 如果這是第一次有效的經驗值，設為起始值
                if self.start_exp_value is None and calc_value is not None:
                    self.start_exp_value = calc_value
                if self.start_exp_percent is None and calc_percent is not None:
                    self.start_exp_percent = calc_percent
                if self.timer.start_time is None:
                    self.timer.start_time = current_effective_time
                self.last_valid_exp = (calc_value, calc_percent)  # 更新最後有效經驗值

    def _is_level_up(self, percent) -> bool:
        """檢查是否升級"""
        if not self.exp_history or percent is None:
            return False
        
        # 獲取最後一筆經驗值
        last_exp = self.exp_history[-1]
        if last_exp[1] is None or last_exp[2] is None:
            return False
        
        # 檢查經驗值是否達到100%
        return last_exp[2] > 90 and percent < 10

    def _get_current_effective_time(self) -> float:
        """獲取當前有效時間（基於計時器的時間基準）"""
        if not self.timer.is_tracking or self.timer.start_time is None:
            return 0.0
        
        elapsed = self.timer.get_elapsed_time()
        if elapsed is None:
            return self.timer.start_time
        
        # 返回基於起始時間加上有效經過時間的時間點
        return self.timer.start_time + elapsed

    def _get_valid_exp_values(self) -> Tuple[Optional[int], Optional[float]]:
        """獲取有效的經驗值和百分比（優先使用最後有效值，並加入辨識糾錯機制）"""
        current_value, current_percent = self._parse_exp_value(self.exp) if self.exp else (None, None)
        
        # 如果當前值無效，直接使用最後有效值
        if current_value is None and current_percent is None:
            if self.last_valid_exp:
                return self.last_valid_exp
            return None, None
        
        # 檢查百分比是否超過100%（辨識錯誤）
        if current_percent is not None and current_percent > 100:
            if self.last_valid_exp:
                return self.last_valid_exp
            return None, None
        
        # 必須等到有超過10筆資料才進行誤差檢查
        if len(self.exp_history) >= 10 and current_value is not None and current_percent is not None and current_percent > 0:
            expected_exp_per_percent = self._calculate_exp_per_percent_from_history()
            if expected_exp_per_percent is not None and expected_exp_per_percent > 0:
                # 計算當前數據的每百分比經驗值
                current_exp_per_percent = current_value / current_percent
                
                # 計算誤差百分比
                error_rate = abs(current_exp_per_percent - expected_exp_per_percent) / expected_exp_per_percent
                
                # 如果誤差超過5%，視為辨識失誤（放寬閾值以避免過度敏感）
                if error_rate > 0.05:  # 5%
                    if self.last_valid_exp:
                        return self.last_valid_exp
                    return None, None
        
        # 當前值通過驗證，返回當前值
        return current_value, current_percent

    def _calculate_exp_per_percent_from_history(self) -> Optional[float]:
        """從歷史資料計算每百分比代表的經驗值（剔除超過誤差範圍的資料）"""
        if len(self.exp_history) < 5:  # 進一步降低要求
            return None
        
        # 先收集所有有效的比值
        all_ratios = []
        for timestamp, value, percent in self.exp_history:
            if value is not None and percent is not None and percent > 0:
                exp_per_percent = value / percent
                all_ratios.append(exp_per_percent)
        
        if len(all_ratios) < 3:  # 進一步降低要求
            return None
        
        # 計算初始平均值
        initial_avg = sum(all_ratios) / len(all_ratios)
        
        # 剔除超過10%誤差的資料（進一步放寬閾值）
        valid_ratios = []
        for ratio in all_ratios:
            error_rate = abs(ratio - initial_avg) / initial_avg
            if error_rate <= 0.05:  # 5%
                valid_ratios.append(ratio)
        
        if len(valid_ratios) < 2:
            return initial_avg  # 如果過濾後數據太少，直接使用平均值
        
        # 計算平均值作為預期的每百分比經驗值
        return sum(valid_ratios) / len(valid_ratios)

    def _parse_exp_value(self, value: str) -> Tuple[Optional[int], Optional[float]]:
        """
        解析經驗值，回傳 (exp_value, exp_percent)
        exp_value: int
        exp_percent: float
        """
        if not value or value == "N/A":
            return None, None
            
        try:
            # 先解析百分比，再移除空格處理數值
            original_value = value
            
            # 百分比解析（不移除空格，避免影響匹配）
            percent_patterns = [
                r'[\[\(](\d+\.?\d*)%',          # [20.3%
                r'/(\d+\.?\d*)%',               # /20.3%
                r'[\[\(](\d+\.?\d*)[%）\]]',    # [20.3% 或 [20.3] 或 [20.3）
                r'/(\d+\.?\d*)(?=[%）\]7]|$)',  # /20.3% 或 /20.3] 或 /20.37 (修正正則)
                r'[\[\(](\d+\.?\d*)(?=[%）\]\s]|$)',  # [20.5 (缺少結尾符號)
                r'(\d+\.?\d*)%',                # 20.3%
            ]
            percent_value = None
            for pattern in percent_patterns:
                match = re.search(pattern, original_value)
                if match:
                    percent_value = float(match.group(1))
                    break
            
            # 數值部分解析（移除空格後取第一個連續數字）
            value_no_space = original_value.replace(" ", "")
            number_match = re.search(r'(\d+)', value_no_space)
            value_num = int(number_match.group(1)) if number_match else None
            
            return value_num, percent_value
        except (ValueError, AttributeError):
            return None, None

    def get_elapsed_time(self) -> Optional[float]:
        """獲取已經過時間（秒），排除暫停時間"""
        return self.timer.get_elapsed_time()

    def _get_current_exp_values(self) -> Tuple[Optional[int], Optional[float]]:
        """獲取當前經驗值和百分比"""
        return self._get_valid_exp_values()

    def _calculate_total_exp(self) -> Tuple[Optional[int], Optional[float]]:
        """計算總累計經驗"""
        cur_value, cur_percent = self._get_current_exp_values()
        
        total_exp_value = None
        total_exp_percent = None
        if cur_value is not None and self.start_exp_value is not None:
            total_exp_value = cur_value - self.start_exp_value + self.total_exp_value
        if cur_percent is not None and self.start_exp_percent is not None:
            total_exp_percent = cur_percent - self.start_exp_percent + self.total_exp_percent
            
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
        current_effective_time = self._get_current_effective_time()
        target_time = current_effective_time - 600  # 10分鐘前（基於有效時間）
        cur_value, cur_percent = self._get_current_exp_values()
        
        past_value = None
        past_percent = None
        # 找到最接近10分鐘前的記錄
        for timestamp, value, percent in self.exp_history:
            if timestamp >= target_time:
                past_value = value if value is not None else self.start_exp_value
                past_percent = percent if percent is not None else self.start_exp_percent
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
        if not self.timer.is_tracking or not self.exp_history:
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
        if not self.timer.is_tracking or not self.exp_history:
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
        timer_status = self.timer.get_status()
        
        return {
            "EXP": self.exp,
            "is_tracking": timer_status["is_tracking"],
            "is_paused": timer_status["is_paused"],
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
            "current_exp_percent": cur_percent,
            "timer_status": timer_status
        }
