"""T2:由用户抄入 scripts/t2_cli_lab.py;本文件不依赖模型或数据库。"""

import argparse
import asyncio
import json
import sys
import time

from contextlib import suppress
from dataclasses import asdict, dataclass
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


def worker():
    """独立子进程:stdout 只给机器结果,stderr 给诊断。mode 仅用于故障实验。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["count", "fail", "flood", "wait"], default="count")
    parser.add_argument("text")
    args = parser.parse_args(sys.argv[2:])
    if args.mode == "fail":
        print("模拟业务失败", file=sys.stderr)
        raise SystemExit(3)
    if args.mode == "wait":
        time.sleep(5)  # 真正制造慢命令,仅用于超时/取消实验。
    if args.mode == "flood":
        print("x" * 100_000)
        print("y" * 100_000, file=sys.stderr)
        return
    print(json.dumps({"text": args.text, "characters": len(args.text)}, ensure_ascii=False))


async def text_stats(args: dict[str, object]):
    """与 TOOL_REGISTRY 的 ToolFunc 同形:业务参数进,JSON 字符串出。"""
    value = args.get("text")
    if not isinstance(value, str):
        return json.dumps({"error": "text 必须是字符串"}, ensure_ascii=False)
    result = await run_cli(
        [sys.executable, str(Path(__file__).resolve()), "--worker", "--", value],
        Path(__file__).resolve().parent,
    )
    if result.error or result.returncode != 0 or result.truncated:
        return json.dumps({"error": "CLI 未完整成功", "detail": asdict(result)}, ensure_ascii=False)
    # 此处先交回业务 JSON;消费其中字段的一侧仍应使用 Pydantic 验证。
    return result.stdout


async def main():
    base = [sys.executable, str(Path(__file__).resolve()), "--worker"]
    cwd = Path.cwd()
    ok = await run_cli([*base, "--", "你好; echo unsafe"], cwd)
    assert ok.returncode == 0 and "你好; echo unsafe" in ok.stdout
    fail = await run_cli([*base, "--mode", "fail", "a"], cwd)
    assert fail.returncode == 3 and "模拟业务失败" in fail.stderr
    flood = await run_cli([*base, "--mode", "flood", "a"], cwd, keep_bytes=64)
    assert flood.truncated and len(flood.stdout.encode()) == 64
    slow = await run_cli([*base, "--mode", "wait", "a"], cwd, timeout=0.2)
    assert slow.error == "执行超时"
    missing = await run_cli(["/definitely-not-an-installed-command"], cwd)
    assert missing.error is not None and missing.returncode is None
    task = asyncio.create_task(run_cli([*base, "--mode", "wait", "a"], cwd))
    await asyncio.sleep(0.05)  # 测试时让子进程启动;产品路径不靠延时排序。
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    else:
        raise AssertionError("取消必须传回调用方")
    assert "error" in await text_stats({"text": 123})
    print("T2:成功、非零退出、输出限制、超时、启动失败、取消、类型错误均通过")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        worker()
    else:
        asyncio.run(main())
