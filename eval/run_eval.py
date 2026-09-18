from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CASES = json.loads((ROOT / "cases.json").read_text(encoding="utf-8"))
SOURCE_SKILL = ROOT.parent / "skill" / "project-guide"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def create_fixture(work: Path, fixture: str) -> None:
    subprocess.run(["git", "init", "-b", "main"], cwd=work, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Eval Fixture"], cwd=work, check=True)
    subprocess.run(["git", "config", "user.email", "eval@localhost"], cwd=work, check=True)

    if fixture in {"existing", "release-candidate", "drifted", "missing-acceptance"}:
        write(
            work / "docs" / "PROJECT.md",
            """# 项目状态（唯一真相）

## Brief
目标用户：个人用户
核心问题：管理家庭物品的位置和借出状态
核心价值：能快速找到物品
MVP 必做：新增、搜索、借出标记
明确不做：登录、多人协作、云同步、手机 App
成功标准：新增后刷新仍存在；搜索可定位；借出状态可恢复

## 里程碑
| ID | 目标 | 范围 | 准出证据 | 状态 |
|---|---|---|---|---|
| M1 | 单机最小闭环 | 新增、存储、搜索 | 自动检查 + 浏览器场景 | IN PROGRESS |

## 当前任务
Task: UI-03
Status: READY FOR REVIEW
Evidence: 自动测试和构建通过
Remaining: 浏览器场景、真实部署冒烟
Next: 执行浏览器用户场景

## 唯一下一步
执行浏览器用户场景并记录结果。

## 工作区记录
工作区干净。
""",
        )
        write(work / "src" / "settings.txt", "primary_button=提交\n")
        write(work / "package.json", '{"scripts":{"test":"echo tests-pass","build":"echo build-pass"}}\n')
        subprocess.run(["git", "add", "."], cwd=work, check=True)
        subprocess.run(["git", "commit", "-m", "fixture baseline"], cwd=work, check=True, capture_output=True)

    if fixture == "drifted":
        write(work / "src" / "settings.txt", "primary_button=保存\nlocal_uncommitted_change=true\n")


def copy_skill(work: Path, fixture: str) -> None:
    destination = work / ".agents" / "skills" / "project-guide"
    shutil.copytree(
        SOURCE_SKILL,
        destination,
        ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc", "project-guide.local.json"),
    )
    if fixture == "missing-acceptance":
        (destination / "references" / "acceptance.md").unlink()


def reference_read_status(trace_text: str, expected_reference: str) -> tuple[bool, bool]:
    """Return whether the expected reference was read-attempted and read successfully."""
    expected = expected_reference.lower().replace("\\", "/")
    attempted = False
    succeeded = False
    for line in trace_text.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = event.get("item", {})
        if event.get("type") != "item.completed" or item.get("type") != "command_execution":
            continue
        command = str(item.get("command", "")).lower().replace("\\", "/")
        if expected not in command:
            continue
        attempted = True
        output = str(item.get("aggregated_output", "")).lower().replace("\\", "/")
        missing_markers = (
            "cannot find path",
            "does not exist",
            "no such file",
            "not found",
            "找不到",
            "不存在",
        )
        expected_pattern = re.escape(expected)
        read_patterns = (
            rf"get-content[^;\n|]*{expected_pattern}",
            rf"(?:cat|type|more)\s+[^;\n|]*{expected_pattern}",
            rf"(?:read_text|open)\([^)]*{expected_pattern}",
        )
        actually_read = any(re.search(pattern, command) for pattern in read_patterns)
        # A compound command may read the reference successfully and fail later on
        # an unrelated subcommand, so the overall exit code is not sufficient.
        if actually_read and not any(marker in output for marker in missing_markers):
            succeeded = True
    return attempted, succeeded


def run_case(case: dict, run_dir: Path) -> dict:
    work = run_dir / "work" / case["id"]
    work.mkdir(parents=True)
    create_fixture(work, case["fixture"])
    copy_skill(work, case["fixture"])

    case_dir = run_dir / "cases" / case["id"]
    case_dir.mkdir(parents=True)
    output = case_dir / "answer.md"
    trace = case_dir / "trace.jsonl"
    stderr = case_dir / "stderr.txt"
    metadata = case_dir / "metadata.json"

    cmd = [
        "codex", "exec",
        "--cd", str(work),
        "--ephemeral",
        "--ignore-user-config",
        "--ignore-rules",
        "--approve-for-me",
        "--json",
        "--output-last-message", str(output),
        case["prompt"],
    ]
    started = time.monotonic()
    proc = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8", timeout=360)
    elapsed = round(time.monotonic() - started, 2)
    write(trace, proc.stdout)
    write(stderr, proc.stderr)

    reference_attempted, reference_succeeded = reference_read_status(
        proc.stdout, case["expected_reference"]
    )
    answer_text = output.read_text(encoding="utf-8") if output.exists() else ""
    data = {
        "id": case["id"],
        "title": case["title"],
        "returncode": proc.returncode,
        "elapsed_seconds": elapsed,
        "expected_reference": case["expected_reference"],
        "expected_reference_read_attempted": reference_attempted,
        "expected_reference_read_succeeded": reference_succeeded,
        "answer_characters": len(answer_text),
        "worktree_status": subprocess.run(
            ["git", "status", "--short"], cwd=work, capture_output=True, text=True, encoding="utf-8"
        ).stdout.splitlines(),
    }
    write(metadata, json.dumps(data, ensure_ascii=False, indent=2))
    return data


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", action="append", default=[])
    args = parser.parse_args()

    selected = [c for c in CASES if not args.only or c["id"] in args.only]
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = ROOT / "runs" / stamp
    run_dir.mkdir(parents=True)
    write(run_dir / "cases.json", json.dumps(selected, ensure_ascii=False, indent=2))

    results = []
    for index, case in enumerate(selected, 1):
        print(f"[{index}/{len(selected)}] {case['id']}", flush=True)
        try:
            results.append(run_case(case, run_dir))
        except Exception as exc:
            results.append({"id": case["id"], "error": repr(exc)})
            print(f"  ERROR: {exc!r}", file=sys.stderr, flush=True)

    write(run_dir / "summary.json", json.dumps(results, ensure_ascii=False, indent=2))
    print(run_dir, flush=True)


if __name__ == "__main__":
    main()
