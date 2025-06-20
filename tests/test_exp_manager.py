import unittest
from unittest.mock import patch, MagicMock
import time
import sys
import os

# Add the parent directory to the path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from module.exp_manager import EXPManager
from module.monitor_timer import MonitorTimer

class TestEXPManager(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.exp_manager = EXPManager()
        
    def test_projected_10min_exp_calculation(self):
        """測試10分鐘內的預估值計算"""
        with patch('time.time') as mock_time:
            # 模擬時間流逝
            start_time = 1000000000.0
            mock_time.return_value = start_time
            
            # 開始追蹤
            self.exp_manager.start_tracking()
            self.exp_manager.update("12345 [20.5%]")
            
            # 模擬3分鐘後 (180秒)
            mock_time.return_value = start_time + 180
            self.exp_manager.timer.last_update_time = start_time + 180
            self.exp_manager.update("13000 [22.8%]")
            
            # 獲取10分鐘經驗數據
            exp_10min_data, total_exp_data = self.exp_manager.get_exp_per_10min_data()
            
            self.assertIsNotNone(exp_10min_data)
            self.assertIsNotNone(total_exp_data)
            
            exp_10min_value, exp_10min_percent = exp_10min_data
            
            # 預期計算：(13000-12345) / 180 * 600 = 655 * 10/3 ≈ 2183
            # 預期百分比：(22.8-20.5) / 180 * 600 = 2.3 * 10/3 ≈ 7.67%
            self.assertAlmostEqual(exp_10min_value, 2183, delta=10)
            self.assertAlmostEqual(exp_10min_percent, 7.67, delta=0.1)
    
    def test_actual_10min_exp_calculation(self):
        """測試超過10分鐘的實際計算 - 使用超過600筆資料"""
        with patch('time.time') as mock_time:
            start_time = 1000000000.0
            mock_time.return_value = start_time
            
            # 開始追蹤並建立歷史數據
            self.exp_manager.start_tracking()
            self.exp_manager.update("15000 [15.0%]")
            
            # 模擬超過600筆數據（約15分鐘，每秒一筆數據）
            for i in range(1, 900):  # 900秒 = 15分鐘的數據
                mock_time.return_value = start_time + i
                self.exp_manager.timer.last_update_time = start_time + i
                # 模擬穩定的經驗增長：每秒約2經驗值，每秒約0.004%
                value = 15000 + i * 2
                percent = 15.0 + i * 0.004
                self.exp_manager.update(f"{value} [{percent:.3f}%]")
            
            # 獲取10分鐘經驗數據
            exp_10min_data, total_exp_data = self.exp_manager.get_exp_per_10min_data()
            
            self.assertIsNotNone(exp_10min_data)
            exp_10min_value, exp_10min_percent = exp_10min_data
            
            # 最近10分鐘（600秒）的經驗增長
            # 從第299秒到第899秒（600秒差異）
            # 值差異：(15000 + 899*2) - (15000 + 299*2) = 1200經驗值
            # 百分比差異：(15.0 + 899*0.004) - (15.0 + 299*0.004) = 2.4%
            expected_exp_value = 600 * 2  # 1200
            expected_exp_percent = 600 * 0.004  # 2.4%
            
            self.assertAlmostEqual(exp_10min_value, expected_exp_value, delta=10)
            self.assertAlmostEqual(exp_10min_percent, expected_exp_percent, delta=0.1)
            
            # 確認歷史數據確實超過600筆
            self.assertEqual(len(self.exp_manager.exp_history), 600)
    
    def test_high_exp_percentage_no_levelup(self):
        """測試90幾%的時候還未升級的情況"""
        with patch('time.time') as mock_time:
            start_time = 1000000000.0
            mock_time.return_value = start_time
            
            # 開始追蹤
            self.exp_manager.start_tracking()
            self.exp_manager.update("50000 [85.0%]")
            
            # 模擬經驗值增長到95%但未升級
            mock_time.return_value = start_time + 300
            self.exp_manager.timer.last_update_time = start_time + 300
            self.exp_manager.update("55000 [95.5%]")
            
            # 檢查沒有觸發升級邏輯
            self.assertEqual(len(self.exp_manager.exp_history), 2)
            self.assertEqual(self.exp_manager.start_exp_value, 50000)
            self.assertEqual(self.exp_manager.start_exp_percent, 85.0)
            
            # 繼續增長到98%
            mock_time.return_value = start_time + 600
            self.exp_manager.timer.last_update_time = start_time + 600
            self.exp_manager.update("57000 [98.2%]")
            
            # 計算預估升級時間
            estimated_time_data = self.exp_manager.get_estimated_levelup_time_data()
            self.assertIsNotNone(estimated_time_data)
            
            hours, minutes, seconds = estimated_time_data
            # 剩餘1.8%，如果10分鐘增長13.2%，則需要約1.36分鐘
            self.assertTrue(minutes > 0 or seconds > 0)
    
    def test_level_up_detection_and_handling(self):
        """測試升級檢測和處理"""
        with patch('time.time') as mock_time:
            start_time = 1000000000.0
            mock_time.return_value = start_time
            
            # 開始追蹤
            self.exp_manager.start_tracking()
            self.exp_manager.update("45000 [90.0%]")
            
            # 增長到95%
            mock_time.return_value = start_time + 300
            self.exp_manager.timer.last_update_time = start_time + 300
            self.exp_manager.update("47500 [95.0%]")
            
            # 升級！經驗值重置
            mock_time.return_value = start_time + 600
            self.exp_manager.timer.last_update_time = start_time + 600
            self.exp_manager.update("1000 [2.0%]")  # 新等級的經驗值
            
            # 檢查升級邏輯是否正確執行
            # 歷史記錄應該被清空並重新開始
            self.assertEqual(len(self.exp_manager.exp_history), 1)
            
            # 檢查總累計經驗是否正確計算
            total_exp_data = self.exp_manager.get_exp_per_10min_data()[1]
            self.assertIsNotNone(total_exp_data)
            
            total_exp_value, total_exp_percent = total_exp_data
            # 總經驗應該包含前一個等級的增長 + 當前等級的經驗
            # 前一個等級：47500 - 45000 = 2500
            # 當前等級：1000 - 1000 = 0
            self.assertEqual(total_exp_value, 2500)
            self.assertAlmostEqual(total_exp_percent, 5.0, delta=0.1)
    
    def test_invalid_exp_values_handling(self):
        """測試無效經驗值的處理"""
        with patch('time.time') as mock_time:
            start_time = 1000000000.0
            mock_time.return_value = start_time
            
            # 開始追蹤
            self.exp_manager.start_tracking()
            self.exp_manager.update("12345 [20.5%]")
            
            # 更新一個無效的經驗值
            mock_time.return_value = start_time + 60
            self.exp_manager.timer.last_update_time = start_time + 60
            self.exp_manager.update("N/A")
            
            # 應該使用最後有效的經驗值
            cur_value, cur_percent = self.exp_manager._get_current_exp_values()
            self.assertEqual(cur_value, 12345)
            self.assertEqual(cur_percent, 20.5)
            
            # exp 應該保存原始值用於顯示
            self.assertEqual(self.exp_manager.exp, "N/A")
            self.assertEqual(self.exp_manager.last_valid_exp, (12345, 20.5))
    
    def test_error_detection_mechanism(self):
        """測試辨識糾錯機制"""
        with patch('time.time') as mock_time:
            start_time = 1000000000.0
            mock_time.return_value = start_time
            
            # 開始追蹤並建立足夠的歷史數據
            self.exp_manager.start_tracking()
            
            # 建立15筆穩定的數據（每百分比約500經驗值）
            for i in range(15):
                mock_time.return_value = start_time + i * 60
                self.exp_manager.timer.last_update_time = start_time + i * 60
                value = 10000 + i * 500
                percent = 20.0 + i * 1.0
                self.exp_manager.update(f"{value} [{percent:.1f}%]")
            
            # 插入一個可接受誤差範圍內的數據
            mock_time.return_value = start_time + 15 * 60
            self.exp_manager.timer.last_update_time = start_time + 15 * 60
            self.exp_manager.update("18000 [36.0%]")  # 每百分比約556經驗值，應該被接受
            
            # 插入一個極端錯誤的數據（誤差超過10%）
            mock_time.return_value = start_time + 16 * 60
            self.exp_manager.timer.last_update_time = start_time + 16 * 60
            self.exp_manager.update("1000000 [37.0%]")  # 每百分比約2703經驗值，誤差極大
            
            # 應該使用最後有效的經驗值（糾錯機制啟動）
            cur_value, cur_percent = self.exp_manager._get_current_exp_values()
            self.assertEqual(cur_value, 18000)
            self.assertEqual(cur_percent, 36.0)
    
    def test_pause_and_resume_tracking(self):
        """測試暫停和恢復追蹤"""
        with patch('time.time') as mock_time:
            start_time = 1000000000.0
            mock_time.return_value = start_time
            
            # 開始追蹤
            self.exp_manager.start_tracking()
            self.exp_manager.update("10000 [20.0%]")
            
            # 暫停追蹤
            mock_time.return_value = start_time + 300
            self.exp_manager.pause_tracking()
            
            # 在暫停期間更新經驗值（不應該被記錄）
            mock_time.return_value = start_time + 600
            self.exp_manager.update("15000 [30.0%]")
            
            # 恢復追蹤
            mock_time.return_value = start_time + 900
            self.exp_manager.resume_tracking()
            self.exp_manager.update("15000 [30.0%]")
            
            # 檢查有效時間計算
            elapsed_time = self.exp_manager.get_elapsed_time()
            # 應該是300秒（暫停前的時間），而不是900秒
            self.assertEqual(elapsed_time, 300.0)
    
    def test_exp_parsing_edge_cases(self):
        """測試經驗值解析的邊界情況"""
        test_cases = [
            ("12345 [20.5%]", (12345, 20.5)),
            ("12345 (20.5%)", (12345, 20.5)),
            ("12345/20.5%", (12345, 20.5)),
            ("12345 [20.5", (12345, 20.5)),
            ("12345/20.57", (12345, 20.57)),
            ("12 345 [20.5%]", (12345, 20.5)),  # 修正期待值：移除空格後變成12345
            ("N/A", (None, None)),
            ("", (None, None)),
            ("invalid_text", (None, None)),
            ("12345 [120.5%]", (12345, 120.5)),  # 超過100%的情況
        ]
        
        for exp_text, expected in test_cases:
            with self.subTest(exp_text=exp_text):
                result = self.exp_manager._parse_exp_value(exp_text)
                self.assertEqual(result, expected)
    
    def test_multiple_level_ups(self):
        """測試多次升級的情況"""
        with patch('time.time') as mock_time:
            start_time = 1000000000.0
            mock_time.return_value = start_time
            
            # 開始追蹤
            self.exp_manager.start_tracking()
            self.exp_manager.update("45000 [90.0%]")
            
            # 第一次升級前增加一些經驗
            mock_time.return_value = start_time + 200
            self.exp_manager.timer.last_update_time = start_time + 200
            self.exp_manager.update("47500 [95.0%]")
            
            # 第一次升級
            mock_time.return_value = start_time + 300
            self.exp_manager.timer.last_update_time = start_time + 300
            self.exp_manager.update("1000 [2.0%]")
            
            # 檢查第一次升級後的累計
            first_level_total = self.exp_manager.total_exp_value
            self.assertEqual(first_level_total, 2500)  # 47500 - 45000
            
            # 第二次升級前的經驗增長
            mock_time.return_value = start_time + 600
            self.exp_manager.timer.last_update_time = start_time + 600
            self.exp_manager.update("48000 [96.0%]")
            
            # 第二次升級
            mock_time.return_value = start_time + 900
            self.exp_manager.timer.last_update_time = start_time + 900
            self.exp_manager.update("500 [1.0%]")
            
            # 檢查總累計經驗
            _, total_exp_data = self.exp_manager.get_exp_per_10min_data()
            total_exp_value, total_exp_percent = total_exp_data
            
            # 正確的期待值計算：
            # 第一次升級累計：2500 (47500-45000)
            # 第二次升級累計：47000 (48000-1000) 
            # 當前經驗：500-500=0
            # 總計：2500 + 47000 + 0 = 49500
            expected_total = 2500 + 47000  # 49500
            self.assertAlmostEqual(total_exp_value, expected_total, delta=100)
            
            # 百分比計算：5% + 94% = 99%
            expected_percent = 5.0 + 94.0  # 99%
            self.assertAlmostEqual(total_exp_percent, expected_percent, delta=1.0)

if __name__ == '__main__':
    # 確保測試目錄存在
    os.makedirs('/Users/shiaojung/Desktop/program/MapleStoryMonitor/tests', exist_ok=True)
    
    # 運行測試
    unittest.main(verbosity=2)
