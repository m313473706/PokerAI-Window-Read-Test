import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import ctypes
from ctypes import wintypes
import json, re, time

try:
    from PIL import ImageGrab, ImageTk, Image
except Exception:
    ImageGrab = ImageTk = Image = None

try:
    from rapidocr_onnxruntime import RapidOCR
except Exception:
    RapidOCR = None

OUT = Path("auto_capture")
OUT.mkdir(exist_ok=True)

user32 = ctypes.windll.user32
EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

def win_text(hwnd):
    n = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(hwnd, buf, n + 1)
    return buf.value

def visible_windows():
    rows = []
    def cb(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            title = win_text(hwnd).strip()
            clsbuf = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, clsbuf, 256)
            cls = clsbuf.value
            if title:
                rows.append((hwnd, title, cls))
        return True
    user32.EnumWindows(EnumWindowsProc(cb), 0)
    rows.sort(key=lambda x: (0 if "poker" in x[1].lower() else 1, x[1].lower()))
    return rows

def rect(hwnd):
    r = wintypes.RECT()
    if user32.GetWindowRect(hwnd, ctypes.byref(r)):
        return r.left, r.top, r.right, r.bottom
    return None

def capture(hwnd):
    box = rect(hwnd)
    if not box or ImageGrab is None:
        raise RuntimeError("无法获取窗口区域或 Pillow 不可用")
    im = ImageGrab.grab(bbox=box, all_screens=True)
    p = OUT / "current_window.png"
    im.save(p)
    return im, p

CARD_RE = re.compile(r'(?<![A-Za-z0-9])([2-9TJQKA])\s*([shdc♠♥♦♣])', re.I)
MONEY_RE = re.compile(r'[$€£]?\s*\d+(?:[.,]\d+)?')

def classify_ocr(items):
    pot = None
    money = []
    cards = []
    raw = []
    for item in items:
        txt = str(item.get("text","")).strip()
        if not txt: continue
        raw.append(txt)
        for m in MONEY_RE.findall(txt):
            money.append(m)
        for m in CARD_RE.finditer(txt):
            cards.append(m.group(0))
        low = txt.lower().replace(" ", "")
        if any(k in low for k in ["pot", "底池"]):
            vals = MONEY_RE.findall(txt)
            if vals:
                pot = vals[-1]
    return {"pot": pot, "money_candidates": money, "card_candidates": cards, "raw_text": raw}

def run_ocr(im):
    if RapidOCR is None:
        return [], "RapidOCR 未安装"
    ocr = RapidOCR()
    result, _ = ocr(im)
    items = []
    if result:
        for row in result:
            try:
                box, text, score = row
                items.append({"text": text, "score": float(score), "box": box})
            except Exception:
                pass
    return items, None

class App:
    def __init__(self, root):
        self.root = root
        root.title("Poker AI Coach - 完整牌桌状态识别测试版 0.3")
        root.geometry("1180x820")
        self.rows = []
        self.img = None

        top = ttk.Frame(root, padding=10); top.pack(fill="x")
        ttk.Label(top, text="完整牌桌状态识别测试版 0.3", font=("Segoe UI", 16, "bold")).pack(side="left")
        ttk.Button(top, text="刷新窗口", command=self.refresh).pack(side="right")
        self.win = ttk.Combobox(root, state="readonly", width=100)
        self.win.pack(fill="x", padx=10)
        ttk.Button(root, text="自动抓取并识别", command=self.process).pack(pady=8)

        body = ttk.Panedwindow(root, orient="horizontal"); body.pack(fill="both", expand=True, padx=10, pady=5)
        left = ttk.Frame(body); right = ttk.Frame(body)
        body.add(left, weight=3); body.add(right, weight=2)

        self.preview = ttk.Label(left, text="牌桌画面预览", anchor="center")
        self.preview.pack(fill="both", expand=True)

        self.state = tk.Text(right, wrap="word", font=("Consolas", 11))
        self.state.pack(fill="both", expand=True)

        self.status = ttk.Label(root, text="状态：请选择模拟器窗口")
        self.status.pack(fill="x", padx=10, pady=6)
        self.refresh()

    def refresh(self):
        self.rows = visible_windows()
        vals = [f"{i}: {t}   [{c}]" for i,(h,t,c) in enumerate(self.rows)]
        self.win["values"] = vals
        if vals: self.win.current(0)
        self.status.config(text=f"发现 {len(vals)} 个可见窗口。请选择扑克模拟器。")

    def selected(self):
        i = self.win.current()
        if i < 0 or i >= len(self.rows): return None
        return self.rows[i]

    def process(self):
        item = self.selected()
        if not item:
            messagebox.showwarning("提示", "请先选择模拟器窗口")
            return
        hwnd, title, cls = item
        try:
            im, path = capture(hwnd)
            ocr_items, err = run_ocr(im)
            c = classify_ocr(ocr_items)
            state = self.build_state(title, cls, c, ocr_items, path)
            (OUT/"recognition_result.json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
            self.show_image(im)
            self.state.delete("1.0","end")
            self.state.insert("end", json.dumps(state, ensure_ascii=False, indent=2))
            self.status.config(text=f"完成：画面已保存到 {path}；识别结果已保存到 auto_capture/recognition_result.json")
        except Exception as e:
            messagebox.showerror("识别失败", str(e))

    def build_state(self, title, cls, c, ocr_items, path):
        # 关键原则：没有可靠证据时不猜，使用“待确认”。
        raw = c["raw_text"]
        money = c["money_candidates"]
        cards = c["card_candidates"]
        street = "待确认"
        if len(cards) >= 5: street = "River"
        elif len(cards) == 4: street = "Turn"
        elif len(cards) == 3: street = "Flop"
        elif len(cards) == 0: street = "Preflop"

        return {
            "window": {"title": title, "class": cls},
            "hero_hand": {"value": cards[:2] if len(cards) >= 2 else [], "status": "待确认"},
            "community_cards": {"value": cards[2:] if len(cards) > 2 else [], "status": "待确认"},
            "street": {"value": street, "status": "自动推断" if street != "待确认" else "待确认"},
            "pot": {"value": c["pot"] or "待确认", "status": "待确认" if not c["pot"] else "OCR候选"},
            "effective_stack": {"value": "待确认", "status": "待确认"},
            "opponent_count": {"value": "待确认", "status": "待确认"},
            "hero_position": {"value": "待确认", "status": "待确认"},
            "current_opponent": {"position": "待确认", "action": "待确认", "bet": "待确认"},
            "opponent_action": {"value": "待确认", "status": "待确认"},
            "opponent_bet": {"value": "待确认", "status": "待确认"},
            "all_visible_money_candidates": money,
            "ocr_raw_text": raw,
            "capture_file": str(path),
            "note": "测试版采用证据优先策略：无法可靠识别的字段不猜测，统一标记为“待确认”。"
        }

    def show_image(self, im):
        im.thumbnail((700, 650))
        self.img = ImageTk.PhotoImage(im)
        self.preview.configure(image=self.img, text="")

if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
