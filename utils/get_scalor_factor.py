import ctypes
from ctypes import wintypes
import tkinter as tk

ctypes.windll.shcore.SetProcessDpiAwareness(2)
user32 = ctypes.windll.user32
dc = user32.GetDC(0)
dpi_x = ctypes.windll.gdi32.GetDeviceCaps(dc, 88)  # LOGPIXELSX
user32.ReleaseDC(0, dc)
scale_factor = dpi_x / 96.0  # 96 DPI 是標準 100% 縮放
print(scale_factor)