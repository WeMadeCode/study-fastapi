import asyncio
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CliResult:
    returncode: int | None
    stdout: str
    stderr: str
    truncated: bool
    error: str | None = None

async def read_bounded(reader: asyncio.StreamReader, keep_bytes: int):
    """只保留前 keep_bytes 字节,但继续排空管道,避免子进程卡在写入。"""
    saved = bytearray()
    total = 0
    while chunk := await reader.read(4096):
        total += len(chunk)
        saved.extend(chunk[: max(0, keep_bytes - len(saved))])
    # 截断可能落在一个汉字中间,replace 显式替换残缺字符。
    return saved.decode("utf-8", errors="replace"), total > keep_bytes

async def run_cli(argv: list[str], cwd: Path, timeout: float = 2.0, keep_bytes: int = 4096):
    if not argv or timeout <= 0 or keep_bytes < 0:
        raise ValueError("argv 不能为空,timeout 必须为正,keep_bytes 不能为负")
    try:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            cwd=cwd,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except OSError as exc:
        return CliResult(None, "", "", False, f"启动失败:{exc}")
    assert proc.stdout is not None and proc.stderr is not None
    # 两根管道同时排空。只读 stdout,可能被写满的 stderr 反向阻塞。
    out_task = asyncio.create_task(read_bounded(proc.stdout, keep_bytes))
    err_task = asyncio.create_task(read_bounded(proc.stderr, keep_bytes))
    error: str | None = None
    # 提前初始化，保证异常分支下变量也已绑定；类型由初始值推导。
    out, err = "", ""
    out_cut, err_cut = False, False
    try:
        async with asyncio.timeout(timeout):
            await proc.wait()
            out, out_cut = await out_task
            err, err_cut = await err_task
    except TimeoutError:
        error = "执行超时"
    finally:
        # 超时或上层取消都要回收子进程。取消异常不会变成成功结果。
        if proc.returncode is None:
            with suppress(ProcessLookupError):
                proc.kill()
        await proc.wait()
        for task in (out_task, err_task):
            if not task.done():
                task.cancel()
        await asyncio.gather(out_task, err_task, return_exceptions=True)
    if error is not None:
        return CliResult(proc.returncode, "", "", False, error)
    return CliResult(proc.returncode, out, err, out_cut or err_cut)