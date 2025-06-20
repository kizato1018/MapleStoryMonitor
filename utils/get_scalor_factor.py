import platform
from multiprocessing import Process, Pipe

def get_all_monitor_scales():
    """跨平台獲取所有螢幕的縮放比例 (float)，例如 [1.0, 1.25, 1.75]"""
    if platform.system() == "Windows":
        return _get_scales_windows()
    elif platform.system() == "Darwin":
        return _get_scales_mac()
    else:
        raise NotImplementedError("Unsupported platform: {}".format(platform.system()))

# --- Windows 多螢幕支援 --- #
def _child_get_scales(conn):
    import ctypes
    from ctypes import wintypes
    ctypes.windll.shcore.SetProcessDpiAwareness(2)

    MONITOR_ENUM_PROC = ctypes.WINFUNCTYPE(
        wintypes.BOOL,
        wintypes.HMONITOR,
        wintypes.HDC,
        ctypes.POINTER(wintypes.RECT),
        wintypes.LPARAM
    )

    scales = []

    def callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
        dpi_x = ctypes.c_uint()
        dpi_y = ctypes.c_uint()
        ctypes.windll.shcore.GetDpiForMonitor(hMonitor, 0, ctypes.byref(dpi_x), ctypes.byref(dpi_y))
        scale = dpi_x.value / 96.0
        scales.append(scale)
        return True

    enum_func = MONITOR_ENUM_PROC(callback)
    ctypes.windll.user32.EnumDisplayMonitors(0, 0, enum_func, 0)
    conn.send(scales)
    conn.close()
def _get_scales_windows():
    parent_conn, child_conn = Pipe()
    p = Process(target=_child_get_scales, args=(child_conn,))
    p.start()
    scales = parent_conn.recv()
    p.join()
    return scales

# --- macOS --- #
def _get_scales_mac():
    try:
        import AppKit
        screens = AppKit.NSScreen.screens()
        return [screen.backingScaleFactor() for screen in screens]
    except Exception:
        return [1.0]
    
if __name__ == "__main__":
    scales = get_all_monitor_scales()
    print("螢幕縮放比例:", scales)