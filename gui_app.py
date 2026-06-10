"""htmlGENERATOR GUI — 拖拽式文件转换界面。

输入支持拖拽或浏览，输出默认与源文件同目录，后台线程转换不冻结 UI。
"""

import queue
import sys
import threading
import webbrowser
from pathlib import Path

# 当作为 frozen exe 运行时，PyInstaller 不会自动将 exe 所在目录
# 加入 sys.path。此处手动加入，以便导入外部 converter/ 文件夹。
if getattr(sys, 'frozen', False):
    sys.path.insert(0, str(Path(sys.executable).parent))

from tkinter import Tk, Frame, Label, Button, Entry, StringVar, ttk
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText

from converter import detect_format, PdfConverter, DocxConverter

# ── 格式 → 转换器映射 ──────────────────────────────────────────────
_CONVERTERS = {
    "pdf":  PdfConverter,
    "docx": DocxConverter,
}
_EXT_FILTER = [
    ("支持的文件", "*.pdf *.docx"),
    ("PDF", "*.pdf"),
    ("Word 文档", "*.docx"),
]

# ── tkinterdnd2 可选导入 ──────────────────────────────────────────
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False
    _DND_HINT = " (点击「选择文件」浏览)"
else:
    _DND_HINT = " (拖拽文件到此处 或 点击「选择文件」)"


# ═══════════════════════════════════════════════════════════════════════
# 后台转换线程
# ═══════════════════════════════════════════════════════════════════════

class ConversionThread(threading.Thread):
    """后台执行转换，通过队列向 GUI 线程发送状态消息。

    消息格式:
        ("log", text)       — 日志文本
        ("progress", pct)  — 进度百分比 0-100
        ("done", path, size)— 转换完成 (输出路径, 文件大小字节)
        ("error", text)    — 错误信息
    """

    def __init__(self, input_path: Path, output_path: Path, fmt: str):
        super().__init__(daemon=True)
        self.input_path = input_path
        self.output_path = output_path
        self.fmt = fmt
        self._queue = queue.Queue()

    def run(self):
        try:
            self._queue.put(("log", f"检测到格式: {self.fmt.upper()}"))
            self._queue.put(("progress", 10))
            self._queue.put(("log", f"输入: {self.input_path}"))
            self._queue.put(("log", f"输出: {self.output_path}"))

            converter = _CONVERTERS[self.fmt]()
            self._queue.put(("progress", 30))
            self._queue.put(("log", "正在转换..."))

            converter.convert(self.input_path, self.output_path)

            size = self.output_path.stat().st_size
            self._queue.put(("progress", 100))
            self._queue.put(("log", f"转换完成 → {self.output_path.name} ({size / 1024:.1f} KB)"))
            self._queue.put(("done", str(self.output_path), size))

        except Exception as e:
            self._queue.put(("error", str(e)))

    def poll(self) -> tuple | None:
        """非阻塞获取下一条消息，无消息返回 None。"""
        try:
            return self._queue.get_nowait()
        except queue.Empty:
            return None


# ═══════════════════════════════════════════════════════════════════════
# GUI 主窗口
# ═══════════════════════════════════════════════════════════════════════

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("htmlGENERATOR — PDF / DOCX → HTML")
        self.root.geometry("680x520")
        self.root.minsize(560, 460)
        self.root.resizable(True, True)

        self._thread: ConversionThread | None = None
        self._output_path: Path | None = None

        # ── 样式 ────────────────────────────────────────────────
        style = ttk.Style()
        style.theme_use("clam")

        # ── 拖拽绑定 ─────────────────────────────────────────────
        if HAS_DND:
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind("<<Drop>>", self._on_drop)

        self._build_ui()

        # 定时轮询后台线程消息
        self.root.after(100, self._poll_thread)

    # ── UI 构建 ──────────────────────────────────────────────────

    def _build_ui(self):
        pad = {"padx": 16, "pady": 4}

        # 标题
        header = ttk.Label(
            self.root,
            text="htmlGENERATOR\nPDF / DOCX → HTML 转换器",
            font=("Segoe UI", 16, "bold"),
            anchor="center", justify="center",
        )
        header.pack(pady=(16, 12))

        # ── 输入文件行 ──────────────────────────────────────────
        input_frame = ttk.Frame(self.root)
        input_frame.pack(fill="x", **pad)

        ttk.Label(input_frame, text="输入文件：", width=10).pack(side="left")
        self.var_input = StringVar()
        self.entry_input = ttk.Entry(input_frame, textvariable=self.var_input)
        self.entry_input.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Button(input_frame, text="选择文件", command=self._browse_input, width=10).pack(side="right")

        # 拖拽提示
        hint = ttk.Label(self.root, text=_DND_HINT, foreground="#888", font=("", 9))
        hint.pack(anchor="e", padx=24, pady=(0, 4))

        # 格式标签
        self.lbl_format = ttk.Label(self.root, text="格式: --", foreground="#666")
        self.lbl_format.pack(anchor="w", padx=24, pady=(0, 8))

        # ── 输出路径行 ──────────────────────────────────────────
        out_frame = ttk.Frame(self.root)
        out_frame.pack(fill="x", **pad)

        ttk.Label(out_frame, text="输出路径：", width=10).pack(side="left")
        self.var_output = StringVar()
        self.entry_output = ttk.Entry(out_frame, textvariable=self.var_output)
        self.entry_output.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Button(out_frame, text="选择路径", command=self._browse_output, width=10).pack(side="right")

        # ── 按钮行 ──────────────────────────────────────────────
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill="x", padx=16, pady=(12, 4))

        self.btn_convert = ttk.Button(btn_frame, text="▶  开始转换", command=self._start_convert)
        self.btn_convert.pack(side="left", padx=(0, 12))

        self.btn_open = ttk.Button(btn_frame, text="↗  用浏览器打开", command=self._open_output, state="disabled")
        self.btn_open.pack(side="left")

        # ── 进度条 ──────────────────────────────────────────────
        self.progress = ttk.Progressbar(self.root, mode="determinate", maximum=100)
        self.progress.pack(fill="x", padx=20, pady=(8, 8))

        # ── 日志区域 ────────────────────────────────────────────
        log_label = ttk.Label(self.root, text="转换日志：")
        log_label.pack(anchor="w", padx=20, pady=(4, 2))

        self.log = ScrolledText(self.root, height=10, state="disabled", font=("Consolas", 9))
        self.log.pack(fill="both", expand=True, padx=20, pady=(0, 16))

    # ── 文件选择 ────────────────────────────────────────────────

    def _browse_input(self):
        path = filedialog.askopenfilename(
            title="选择输入文件",
            filetypes=_EXT_FILTER,
        )
        if path:
            self._set_input(path)

    def _browse_output(self):
        initial = self.var_output.get() or ""
        path = filedialog.asksaveasfilename(
            title="选择输出位置",
            defaultextension=".html",
            filetypes=[("HTML 文件", "*.html")],
            initialfile=Path(initial).name if initial else "",
            initialdir=Path(initial).parent if initial else "",
        )
        if path:
            self.var_output.set(path)

    def _on_drop(self, event):
        """处理拖拽文件事件。"""
        # event.data 格式: {file1} {file2} ... (可能带花括号包裹含空格路径)
        raw = event.data.strip()
        # 去掉 tkinterdnd2 的 {} 包裹
        if raw.startswith("{") and raw.endswith("}"):
            raw = raw[1:-1]
        # 取第一个路径
        lines = raw.replace("} {", "|").replace("{", "").replace("}", "").split("|")
        first = lines[0].strip()
        if first:
            self._set_input(first)

    def _set_input(self, path_str: str):
        """设置输入文件，自动检测格式并填充输出路径。"""
        input_path = Path(path_str)
        try:
            fmt = detect_format(input_path)
        except ValueError:
            if input_path.suffix.lower() == ".doc":
                messagebox.showinfo(
                    "提示",
                    "不支持旧版 .doc 格式。\n\n"
                    "请先用 Word / WPS 打开该文件，\n"
                    "另存为 .docx 格式后再拖入转换。"
                )
            else:
                messagebox.showwarning("不支持", f"不支持的文件格式: {input_path.suffix}")
            return

        self.var_input.set(str(input_path))
        self.lbl_format.config(text=f"格式: {fmt.upper()}")

        # 自动填充输出路径：同目录同名 .html
        out = input_path.with_suffix(".html")
        self.var_output.set(str(out))
        self._output_path = out

    # ── 转换控制 ────────────────────────────────────────────────

    def _start_convert(self):
        input_str = self.var_input.get().strip()
        out_str = self.var_output.get().strip()

        if not input_str:
            messagebox.showwarning("提示", "请先选择输入文件。")
            return

        input_path = Path(input_str)
        if not input_path.is_file():
            messagebox.showerror("错误", f"文件不存在: {input_path}")
            return

        if not out_str:
            messagebox.showwarning("提示", "请指定输出路径。")
            return

        output_path = Path(out_str)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            fmt = detect_format(input_path)
        except ValueError as e:
            messagebox.showerror("错误", str(e))
            return

        # 禁用按钮，清空日志
        self.btn_convert.config(state="disabled")
        self.btn_open.config(state="disabled")
        self.progress["value"] = 0
        self._clear_log()

        self._thread = ConversionThread(input_path, output_path, fmt)
        self._thread.start()

    def _poll_thread(self):
        """定时轮询后台线程消息。"""
        if self._thread is not None:
            msg = self._thread.poll()
            while msg is not None:
                kind = msg[0]
                if kind == "log":
                    self._append_log(msg[1])
                elif kind == "progress":
                    self.progress["value"] = msg[1]
                elif kind == "done":
                    self._output_path = Path(msg[1])
                    self._append_log(f"✓ 文件大小: {msg[2] / 1024:.1f} KB")
                    self.btn_convert.config(state="normal")
                    self.btn_open.config(state="normal")
                    self._thread = None
                elif kind == "error":
                    self._append_log(f"✗ 错误: {msg[1]}")
                    messagebox.showerror("转换失败", msg[1])
                    self.btn_convert.config(state="normal")
                    self._thread = None
                msg = self._thread.poll() if self._thread else None

        self.root.after(100, self._poll_thread)

    # ── 工具方法 ────────────────────────────────────────────────

    def _open_output(self):
        if self._output_path and self._output_path.is_file():
            webbrowser.open(str(self._output_path.resolve()))

    def _append_log(self, text: str):
        self.log.config(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.config(state="disabled")

    def _clear_log(self):
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")


# ═══════════════════════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════════════════════

def main():
    root_cls = TkinterDnD.Tk if HAS_DND else Tk
    root = root_cls()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
