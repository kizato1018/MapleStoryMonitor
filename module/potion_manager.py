import re
from typing import Optional, List, Tuple
from collections import deque
import statistics
from module.monitor_timer import MonitorTimer
from utils.log import get_logger

logger = get_logger(__name__)

class PotionManager:
    """負責處理藥水使用量相關邏輯"""
    
    def __init__(self):
        self.potion = None
        self.last_valid_value = None  # 記錄最後一次有效的藥水值
        self.value = None
        self.potion_history = deque(maxlen=600)  # 10分鐘，每秒一筆
        self.value_history = deque(maxlen=100)  # 記錄藥水數值變化，用於中值濾波
        self.timer = MonitorTimer()  # 使用MonitorTimer管理時間
        self.start_potion_value = None  # int or None
        self.total_used = 0  # 累計總使用量
        self.unit_cost = 0  # 藥水單價
        self.prev_value = None  # 上一次的藥水值，用於檢測補充
        self.error_threshold = 50  # 當前值小於上一次值的容錯範圍，默認為50個單位
        self.enabled = False
        self.median_window_size = 5  # 中值濾波窗口大小

    def start_tracking(self):
        """開始追蹤藥水使用量"""
        self.timer.start_tracking()
        self._reset()  # 重置狀態

    def is_tracking(self) -> bool:
        """檢查是否正在追蹤藥水"""
        return self.timer.is_tracking

    def is_paused(self) -> bool:
        """檢查是否暫停追蹤藥水"""
        return self.timer.is_paused

    def pause_tracking(self):
        """暫停追蹤藥水使用量"""
        self.timer.pause_tracking()
        total_used = self.total_used
        self._reset()
        self.total_used = total_used  # 保留累計使用量

    def resume_tracking(self):
        """恢復追蹤藥水使用量"""
        self.timer.resume_tracking()

    def stop_tracking(self):
        """停止追蹤藥水使用量"""
        self.timer.stop_tracking()

    def reset_tracking(self):
        """重置追蹤"""
        self.timer.reset_tracking()
        self._reset()

    def _reset(self):
        self.start_potion_value = None
        self.prev_value = None
        self.total_used = 0
        self.potion_history.clear()
        self.value_history.clear()

    def set_unit_cost(self, cost: str):
        """設定藥水單價"""
        try:
            cost = int(cost)
            if cost < 0:
                logger.warning(f"無效的藥水單價: {cost}. 單價不能為負數。")
            self.unit_cost = cost
            logger.info(f"藥水單價已設定為: {cost}")
        except ValueError as e:
            logger.error(f"無效的藥水單價: {e}. 請確保輸入為有效的正整術。")

    def update(self, potion_text: str):
        """更新藥水數量"""
        # 檢查新的藥水值是否有效
        self.value = self._parse_potion_value(potion_text)
        self.value = self._correct_value(self.value)  # 確保值在合理範圍內
        
        self.potion = potion_text
        # 如果新值有效，更新藥水值和最後有效值
        if self._is_valid_number(self.value):
            self.last_valid_value = self.value
        
        if self.timer.is_tracking and not self.timer.is_paused:
            # 使用計時器基準時間，而非直接使用 time.time()
            current_effective_time = self._get_current_effective_time()
            
            # 使用最後有效的藥水值進行計算
            calc_value = self.last_valid_value
            
            if calc_value is not None:
                # 只有當數值有變化時才記錄到 value_history
                if not self.value_history or calc_value != self.value_history[-1][1]:
                    self.value_history.append((current_effective_time, calc_value))
                
                # 應用中值濾波處理歷史數據
                # self._apply_median_filter()
                
                # 獲取最新的濾波後數值
                # calc_value = self.value_history[-1][1] if self.value_history else calc_value
                
                # 檢測補充邏輯：從0變成其他數字 = 補充
                if (self.prev_value is not None and 
                    self.prev_value == 0 and 
                    calc_value > 0):
                    # 檢測到補充，清空歷史記錄但保持累計使用量
                    logger.info(f"檢測到藥水補充：從 0 到 {calc_value}")
                    self.value_history.clear()
                    self.potion_history.clear()
                    self.start_potion_value = calc_value
                    # 重新記錄當前狀態
                    self.value_history.append((current_effective_time, calc_value))
                    self.potion_history.append((current_effective_time, self.total_used))
                
                # 檢測正常使用：當前值小於上一次值
                elif (self.prev_value is not None and 
                      self.prev_value > calc_value and
                      self.prev_value - calc_value < self.error_threshold):
                    used_amount = self.prev_value - calc_value
                    self.total_used += used_amount
                
                self.prev_value = calc_value
                
                # 僅每秒保留一筆資料，使用有效時間計算
                if not self.potion_history or int(current_effective_time) > int(self.potion_history[-1][0]):
                    self.potion_history.append((current_effective_time, calc_value))
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

    def _is_valid_number(self, value) -> bool:
        """獲取有效的藥水值（優先使用最後有效值）"""
        return isinstance(value,(int)) and value >= 0 and value <= 3000
    
    def _correct_value(self, value: Optional[int]) -> Optional[int]:
        """
        確保藥水值在合理範圍內，並返回修正後的值
        value: int (e.g. 2999)
        Returns:
            int or None (如果值不在範圍內則返回 None)
        """
        if self._is_valid_number(value):
            return value
        else:
            last_value = self.last_valid_value
            if last_value is not None:
                if len(str(value)) > len(str(last_value)):
                    value1 = int(str(value)[:len(str(last_value))])
                    value2 = int(str(value)[-len(str(last_value)):])
                    if abs(value1 - last_value) < abs(value2 - last_value):
                        return value1
                    else:
                        return value2
            else:
                if len(str(value)) > 4:
                    value1 = int(str(value)[:4]) if int(str(value)[:4]) <= 3000 else None
                    value2 = int(str(value)[-4:]) if int(str(value)[-4:]) <= 3000 else None
                    if value1 is not None and value2 is not None:
                        return max(value1, value2)
                    elif value1 is not None:
                        return value1
                    elif value2 is not None:
                        return value2
        return None
    def _parse_potion_value(self, value: str) -> Optional[int]:
        """
        解析藥水值，回傳 potion_value
        potion_value: int (e.g. "2,999" -> 2999)
        """
        if not value or value == "N/A":
            return None
            
        try:
            cleaned_value = re.sub(r'[^\d]', '', value)  # 移除非數字字符
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

    def get_cost_per_10min_data(self) -> Tuple[Optional[int], Optional[int]]:
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
        timer_status = self.timer.get_status()
        
        return {
            "potion": self.potion,
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
            "current_potion_value": self.value,
            "total_used_amount": self.total_used,
            "timer_status": timer_status
        }

    def _apply_median_filter(self) -> None:
        """
        對 value_history 應用中值濾波器來移除異常值
        """
        if len(self.value_history) < self.median_window_size:
            return
        
        # 獲取最近的數值進行分析
        recent_entries = list(self.value_history)[-self.median_window_size:]
        recent_values = [entry[1] for entry in recent_entries]
        
        try:
            median_value = statistics.median(recent_values)
            
            # 檢查是否有異常值需要移除
            anomalous_indices = []
            for i, (timestamp, value) in enumerate(recent_entries):
                # 跳過可能的補充值（大幅增加）
                if i > 0 and value > recent_entries[i-1][1] + 1000:
                    continue
                    
                # 檢測異常低值或高值
                if abs(value - median_value) > 100:
                    # 進一步驗證是否為異常值
                    other_values = [v for j, v in enumerate(recent_values) if j != (len(recent_entries) - len(recent_values) + i)]
                    if len(other_values) >= 2:
                        other_median = statistics.median(other_values)
                        if abs(value - other_median) > 50:
                            anomalous_indices.append(len(self.value_history) - len(recent_entries) + i)
                            logger.warning(f"檢測到異常藥水數值: {value}, 中值: {median_value:.1f}")
            
            # 移除異常值
            if anomalous_indices:
                self._remove_anomalous_entries(anomalous_indices)
                
        except statistics.StatisticsError:
            logger.warning("中值濾波計算錯誤")

    def _remove_anomalous_entries(self, anomalous_indices: List[int]) -> None:
        """
        移除異常的 value_history 條目，並移除對應的 potion_history 條目
        """
        # 獲取要移除的時間戳和數值
        anomalous_timestamps = []
        anomalous_values = []
        for index in sorted(anomalous_indices, reverse=True):
            if 0 <= index < len(self.value_history):
                timestamp, value = self.value_history[index]
                anomalous_timestamps.append(timestamp)
                anomalous_values.append(value)
                # 從 value_history 移除
                del self.value_history[index]
                logger.info(f"已移除異常藥水數值: {value} (時間: {timestamp})")
        
        # 檢查是否移除的異常值影響到起始值
        need_recalculate = False
        if self.start_potion_value in anomalous_values:
            # 如果起始值被移除，重新設定起始值
            if self.value_history:
                self.start_potion_value = self.value_history[0][1]
                logger.info(f"重新設定起始藥水值為: {self.start_potion_value}")
            else:
                self.start_potion_value = None
            need_recalculate = True
        
        # 從 potion_history 移除對應時間的記錄（允許1秒誤差）
        if anomalous_timestamps:
            original_potion_count = len(self.potion_history)
            filtered_potion_history = deque(maxlen=self.potion_history.maxlen)
            
            for timestamp, usage in self.potion_history:
                # 檢查是否在異常時間範圍內
                is_anomalous = any(abs(timestamp - at) <= 1 for at in anomalous_timestamps)
                if not is_anomalous:
                    filtered_potion_history.append((timestamp, usage))
            
            self.potion_history = filtered_potion_history
            removed_potion_count = original_potion_count - len(self.potion_history)
            
            if removed_potion_count > 0:
                logger.info(f"已移除 {removed_potion_count} 個對應的使用量記錄")
                need_recalculate = True
        
        # 如果需要重新計算，重建 total_used 和 potion_history
        if need_recalculate:
            self._recalculate_usage_from_history()

    def _recalculate_usage_from_history(self) -> None:
        """
        從清理後的 value_history 重新計算使用量和 potion_history
        """
        if not self.value_history:
            self.total_used = 0
            self.potion_history.clear()
            return
        
        # 重置計算
        old_total = self.total_used
        self.total_used = 0
        new_potion_history = deque(maxlen=self.potion_history.maxlen)
        
        # 從第一個記錄開始重新計算
        prev_value = None
        for i, (timestamp, value) in enumerate(self.value_history):
            if i == 0:
                # 第一個記錄，設定為起始點
                if self.start_potion_value is None:
                    self.start_potion_value = value
                prev_value = value
                # 添加初始記錄
                new_potion_history.append((timestamp, self.total_used))
            else:
                # 檢測使用量：當前值小於前一個值
                if (prev_value is not None and 
                    prev_value > value and 
                    prev_value - value < self.error_threshold):
                    used_amount = prev_value - value
                    self.total_used += used_amount
                
                # 檢測補充：當前值大幅增加
                elif (prev_value is not None and 
                      value > prev_value + 1000):
                    # 補充不影響總使用量，但重置參考點
                    logger.info(f"在重計算中檢測到補充：從 {prev_value} 到 {value}")
                
                prev_value = value
                
                # 只保留整秒的記錄
                if not new_potion_history or int(timestamp) > int(new_potion_history[-1][0]):
                    new_potion_history.append((timestamp, self.total_used))
        
        # 更新 potion_history
        self.potion_history = new_potion_history
        
        # 更新最後的藥水值
        if self.value_history:
            self.prev_value = self.value_history[-1][1]
        
        logger.info(f"重新計算完成：總使用量從 {old_total} 調整為 {self.total_used}")

class TotalPotionManager:
    """負責管理多個 PotionManager 實例"""
    
    def __init__(self):
        self.potion_managers: List[PotionManager] = [PotionManager() for _ in range(8)]
    
    def __iter__(self):
        """迭代 PotionManager 列表"""
        return iter(self.potion_managers)
    
    def __getitem__(self, index: int) -> PotionManager:
        """獲取指定索引的 PotionManager"""
        return self.potion_managers[index]
    
    def __len__(self) -> int:
        """獲取 PotionManager 的數量"""
        return len(self.potion_managers)
    
    def get_all_status(self) -> List[dict]:
        """獲取所有 PotionManager 的狀態"""
        return [manager.get_status() for manager in self.potion_managers]
    
    def get_potion_per_10min_data(self) -> Tuple[List[Optional[str]], List[Optional[str]]]:
        """獲取所有 PotionManager 的 10 分鐘使用量和總累計使用量"""
        potion_per_10min_list = []
        total_used_list = []
        
        for manager in self.potion_managers:
            if manager.enabled:
                potion_per_10min, total_used = manager.get_potion_per_10min_data()
                potion_per_10min_list.append(potion_per_10min)
                total_used_list.append(total_used)
            
        return potion_per_10min_list, total_used_list
    
    def get_cost_per_10min_data(self) -> Tuple[List[Optional[str]], List[Optional[str]]]:
        """獲取所有 PotionManager 的 10 分鐘成本和總累計成本"""
        cost_per_10min_list = []
        total_cost_list = []
        
        for manager in self.potion_managers:
            if manager.enabled:
                cost_per_10min, total_cost = manager.get_cost_per_10min_data()
                cost_per_10min_list.append(cost_per_10min)
                total_cost_list.append(total_cost)
            
        return cost_per_10min_list, total_cost_list

    def get_potion_per_10min_total_data(self) -> Tuple[Optional[str], Optional[str]]:
        """獲取所有 PotionManager 的 10 分鐘使用量和總累計使用量（總計）"""
        potion_per_10min_sum = 0
        total_used_sum = 0
        
        for manager in self.potion_managers:
            if manager.enabled:
                potion_per_10min, total_used = manager.get_potion_per_10min_data()
                potion_per_10min_sum += potion_per_10min if potion_per_10min is not None else 0
                total_used_sum += total_used if total_used is not None else 0
        
        return potion_per_10min_sum, total_used_sum
    
    def get_cost_per_10min_total_data(self) -> Tuple[Optional[str], Optional[str]]:
        """獲取所有 PotionManager 的 10 分鐘成本和總累計成本（總計）"""
        cost_per_10min_sum = 0
        total_cost_sum = 0
        
        for manager in self.potion_managers:
            if manager.enabled:
                cost_per_10min, total_cost = manager.get_cost_per_10min_data()
                cost_per_10min_sum += cost_per_10min if cost_per_10min is not None else 0
                total_cost_sum += total_cost if total_cost is not None else 0
            
        return cost_per_10min_sum, total_cost_sum