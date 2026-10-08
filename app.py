import tkinter as tk
from tkinter import ttk, messagebox
import ctypes
from ctypes import wintypes
from pathlib import Path
import traceback

try:
    from pywinauto import Desktop
    PYWINAUTO_OK = True
except Exception:
    PYWINAUTO_OK = False

user32 = ctypes.windll.user32
EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

def win_text(hwnd):
    n = user32.GetWindowTextLengthW(hwnd)
    b = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(hwnd, b, n + 1)
    return b.value

def win_class(hwnd):
    b = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, b, 256)
    return b.value

def visible_windows():
    out = []
    def cb(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            title = win_text(hwnd).strip()
            if title:
                out.append((hwnd, title, win_class(hwnd)))
        return True
    user32.EnumWindows(EnumWindowsProc(cb), 0)
    return out

def children(hwnd):
    out = []
    Proc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(ch, _):
        out.append((ch, win_text(ch).strip(), win_class(ch)))
        return True
    user32.EnumChildWindows(hwnd, Proc(cb), 0)
    return out

def uia(title):
    lines = []
    if not PYWINAUTO_OK:
        return ["pywinauto 未安装，跳过 UI Automation。"]
    try:
        w = Desktop(backend="uia").window(title=title)
        w.wait("exists", timeout=3)
        cs = w.descendants()
        lines.append(f"UI Automation 找到窗口，子控件数量：{len(cs)}")
        for i, c in enumerate(cs[:100]):
            try: name = c.window_text()
            except: name = ""
            try: typ = c.element_info.control_type
            except: typ = ""
            if name or typ:
                lines.append(f"  [{i}] name={name!r} type={typ!r}")
    except Exception as e:
        lines.append(f"UI Automation 未找到/读取失败：{e}")
    return lines

class App:
    def __init__(self, root):
        self.root = root
        root.title("Poker AI Window Read Test 0.3")
        root.geometry("900x650")
        top = ttk.Frame(root, padding=10); top.pack(fill="x")
        ttk.Label(top, text="扑克模拟器窗口：").pack(side="left")
        self.combo = ttk.Combobox(top, state="readonly", width=70)
        self.combo.pack(side="left", padx=8, fill="x", expand=True)
        ttk.Button(top, text="刷新窗口", command=self.refresh).pack(side="left")
        ttk.Button(top, text="开始测试", command=self.test).pack(side="left", padx=8)
        self.status = ttk.Label(root, text="请先打开扑克模拟器，然后刷新窗口。", padding=10)
        self.status.pack(fill="x")
        self.out = tk.Text(root, wrap="word", font=("Consolas", 10))
        self.out.pack(fill="both", expand=True, padx=10, pady=10)
        self.windows = []
        self.refresh()

    def refresh(self):
        self.windows = visible_windows()
        self.combo["values"] = [f"{t} [{c}]" for _, t, c in self.windows]
        if self.windows:
            self.combo.current(0)
            self.status.config(text=f"找到 {len(self.windows)} 个可见窗口，请选择扑克模拟器。")
        else:
            self.status.config(text="没有找到带标题的可见窗口。")

    def test(self):
        self.out.delete("1.0", "end")
        i = self.combo.current()
        if i < 0:
            messagebox.showwarning("提示", "请先选择扑克模拟器窗口。"); return
        hwnd, title, cls = self.windows[i]
        ch = children(hwnd)
        lines = [
            "Poker AI Window Read Test 0.3",
            "=" * 70,
            f"窗口标题：{title}",
            f"窗口类名：{cls}",
            f"HWND：{hwnd}",
            "",
            "[1] Win32 主窗口文字",
            f"GetWindowText = {win_text(hwnd)!r}",
            "",
            "[2] Win32 子窗口控件",
            f"子窗口数量：{len(ch)}"
        ]
        for j, (h, txt, c) in enumerate(ch[:200]):
            if txt or c:
                lines.append(f"  [{j}] text={txt!r} class={c!r} hwnd={h}")
        lines += ["", "[3] UI Automation"]
        lines += uia(title)
        useful = any(txt for _, txt, _ in ch)
        if useful:
            lines += ["", "[结论]", "🟢 发现可读取的子控件文字。优先继续直接读取方案。"]
        elif win_text(hwnd).strip():
            lines += ["", "[结论]", "🟡 能读取窗口标题，但没有发现明显子控件文字。"]
        else:
            lines += ["", "[结论]", "🔴 暂未发现可直接读取的文字/控件。下一步建议自动窗口捕获 + OCR。"]
        try:
            Path("window_test_result.txt").write_text("\n".join(lines), encoding="utf-8")
            lines += ["", "测试报告已保存：window_test_result.txt"]
        except Exception as e:
            lines += [f"保存报告失败：{e}"]
        self.out.insert("1.0", "\n".join(lines))
        self.status.config(text="测试完成。请把结果截图或 window_test_result.txt 发给我。")

try:
    root = tk.Tk()
    App(root)
    root.mainloop()
except Exception:
    Path("window_test_error.txt").write_text(traceback.format_exc(), encoding="utf-8")
    raise
