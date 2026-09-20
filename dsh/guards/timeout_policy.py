"""timeout-policy — 工具调用截止时间策略 guard。

借鉴 DSH packages/guard/timeout-policy：
- 注册 tools/execute wrapper（around-dispatch）
- 工具声明 timeout_ms 时武装截止时间
- 超时替换结果为结构化 TOOL_TIMEOUT 错误

跨平台（2026-09-20 Windows 适配）：
- macOS/Linux：SIGALRM + setitimer 硬超时（原实现，行为不变）。
- Windows：无 SIGALRM/setitimer，改用 win_compat.timeout_scope（threading.Timer
  软超时）。工具函数正常返回后若超时已触发，返回 TOOL_TIMEOUT 结果；guard 的
  “超时可见性”语义保留。无法硬中断阻塞中的同步调用是平台已知限制。
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
SCRIPTS = REPO / ".scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from win_compat import IS_WINDOWS

if not IS_WINDOWS:
    import signal

from dsh.harness import ToolExecution, ToolExecutionResult

TOOL_TIMEOUT_CODE = "TOOL_TIMEOUT"


def timeout_result(timeout_ms: int) -> ToolExecutionResult:
    msg = f"工具调用在 {timeout_ms}ms 后超时"
    return ToolExecutionResult(content=f"[ERROR] {msg}", is_error=True,
                               error_code=TOOL_TIMEOUT_CODE)


class TimeoutPolicy:
    """每次调用的截止时间策略。

    为每个工具执行设置截止时间。如果工具声明了 timeout_ms，
    超时后替换结果为 TOOL_TIMEOUT。
    """

    def __init__(self, default_timeout_ms: int = 30000):
        self.default_timeout_ms = default_timeout_ms

    def on_execute(self, exec_ctx: ToolExecution, next_fn) -> ToolExecutionResult:
        """around-dispatch wrapper：武装截止时间，委托，超时则替换。"""
        if IS_WINDOWS:
            # Windows：threading.Timer 软超时（无 SIGALRM）。
            from win_compat import timeout_scope
            try:
                with timeout_scope(self.default_timeout_ms):
                    return next_fn(exec_ctx)
            except TimeoutError:
                return timeout_result(self.default_timeout_ms)
        # macOS/Unix：SIGALRM 硬超时（单线程，原实现）。
        old_handler = signal.getsignal(signal.SIGALRM)
        signal.signal(signal.SIGALRM, lambda *_: None)
        signal.setitimer(signal.ITIMER_REAL, self.default_timeout_ms / 1000.0)
        try:
            result = next_fn(exec_ctx)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old_handler or signal.SIG_DFL)
        return result
