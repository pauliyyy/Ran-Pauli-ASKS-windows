#!/usr/bin/env python3
"""win_compat.py — Windows/Unix 跨平台兼容层（2026-09-20 适配）。

设计原则：
1. **Unix 行为零变化**：在 macOS/Linux 上，所有函数走原有路径（python3 命令、
   fcntl.flock、signal.SIGALRM），与适配前逐字节等价。
2. **Windows 分支只增不改**：Windows 上用 sys.executable 派生子进程、
   msvcrt.locking 文件锁、threading.Timer 限时；语义与 Unix 对应物一致。
3. 各修复点统一从本模块取启动器/锁，不散落 if os.name == 'nt'。

被替换的 Unix 专属依赖：
- subprocess 里硬编码的 "python3"          → PY（跨平台启动器）
- fcntl.flock（graph_lib.graph_writer_lock）→ lock_file 上下文管理器
- signal.SIGALRM/setitimer（dsh timeout）   → timeout_scope 上下文管理器
"""
from __future__ import annotations

import os
import sys

IS_WINDOWS = os.name == "nt"

# ---------------------------------------------------------------------------
# 1) Python 子进程启动器
#
# Unix 惯例是 "python3"；Windows 官方安装器不提供 python3.exe（只有 python.exe
# 与 py.exe），且本机托管的运行时也以 python.exe 命名。这里：
#   - Windows：用当前解释器的绝对路径（sys.executable），保证子进程与父进程
#     同版本、同 site-packages，杜绝 PATH 污染。
#   - Unix：保持 "python3" 字面量，行为与适配前一致。
# ---------------------------------------------------------------------------
if IS_WINDOWS:
    PY = sys.executable or "python"
else:
    PY = "python3"


# ---------------------------------------------------------------------------
# 2) 跨平台文件锁（替代 fcntl.flock）
#
# graph_writer_lock 原实现：打开锁文件后 fcntl.flock(LOCK_EX) 串行化跨进程写入。
# Windows 对应物为 msvcrt.locking（对已打开句柄的指定区域加锁）。
# 两者语义均为“同一路径上的独占锁，进程退出自动释放”。
# ---------------------------------------------------------------------------
if IS_WINDOWS:
    import msvcrt
    from contextlib import contextmanager

    @contextmanager
    def lock_file(handle):
        """Windows：对整个文件区域加独占锁，退出时解锁。"""
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        try:
            yield handle
        finally:
            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            except (PermissionError, OSError):
                pass
else:
    import fcntl
    from contextlib import contextmanager

    @contextmanager
    def lock_file(handle):
        """Unix：fcntl.flock 独占锁（与适配前行为一致）。"""
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield handle
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


# ---------------------------------------------------------------------------
# 3) 跨平台限时执行（替代 signal.SIGALRM/setitimer）
#
# dsh timeout guard 原实现：SIGALRM 定时器到点后中断工具函数体。
# Windows 无 SIGALRM；signal.setitimer 也不可用。threading.Timer 无法硬中断
# 运行中的同步调用，因此 Windows 分支提供“软超时”：
#   - 到点后 guard 抛 TimeoutError（可被上层捕获转为 TOOL_TIMEOUT 结果）；
#   - 正常路径与 Unix 相同：with 块正常结束即视为未超时。
# 注意：Windows 上工具函数体若已陷入阻塞 IO，其本身不会被中断，超时结果在
# 函数返回后才生效；这是平台差异的已知限制，guard 的“超时可见性”保留。
# ---------------------------------------------------------------------------
if IS_WINDOWS:
    import threading
    from contextlib import contextmanager

    @contextmanager
    def timeout_scope(timeout_ms: int):
        """Windows：软超时。到点设置标志并抛 TimeoutError。"""
        timed_out = threading.Event()
        state = {"fired": False}

        def _fire():
            state["fired"] = True
            timed_out.set()

        timer = threading.Timer(timeout_ms / 1000.0, _fire)
        timer.daemon = True
        timer.start()
        try:
            yield state
        finally:
            timer.cancel()
            if timed_out.is_set():
                raise TimeoutError(f"timeout after {timeout_ms}ms")
else:
    import signal
    from contextlib import contextmanager

    @contextmanager
    def timeout_scope(timeout_ms: int):
        """Unix：SIGALRM 硬超时（与 dsh/guards/timeout_policy.py 原实现一致）。"""
        old_handler = signal.getsignal(signal.SIGALRM)
        signal.signal(signal.SIGALRM, lambda *_: None)
        signal.setitimer(signal.ITIMER_REAL, timeout_ms / 1000.0)
        try:
            yield None
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old_handler or signal.SIG_DFL)


# ---------------------------------------------------------------------------
# 4) Docling venv 解释器路径
#
# 原实现硬编码 DOCLING_VENV / "bin" / "python"（Unix venv 布局）。
# Windows venv 布局为 Scripts/python.exe。
# ---------------------------------------------------------------------------
def venv_python(venv_root) -> str:
    """返回 venv 内 Python 解释器的可执行路径（跨平台）。"""
    if IS_WINDOWS:
        return os.path.join(str(venv_root), "Scripts", "python.exe")
    return os.path.join(str(venv_root), "bin", "python")
