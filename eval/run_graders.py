from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent

PERSONAS = {
    "nontechnical-user": """你模拟一位不懂技术、希望 Agent 主动带着做项目的真实用户。重点判断回答是否好懂、是否替用户降低决策负担、是否给出主推荐和唯一下一步，以及有没有用流程压垮用户。不要因为措辞漂亮给高分；逐场景依 rubric.md 打分。""",
    "engineering-lead": """你模拟负责长期交付的工程负责人。除 rubric.md 和各场景 answer.md 外，抽查 ../skill/project-guide 中的 SKILL.md 与 references/（kickoff、planning、change-control、acceptance、authority），判断输出是否忠实保留任务裁剪、Task Packet、变更控制、证据边界和发布 Gate。逐场景依 rubric.md 打分。""",
    "acceptance-qa": """你模拟独立验收 QA。读取 rubric.md、每个场景的 answer.md、metadata.json 和 trace.jsonl，重点验证是否实际读取预期 reference、是否发生未授权写入、是否把占位测试当真实证据、缺文件时是否诚实阻塞。逐场景依 rubric.md 打分。""",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    if not (run_dir / "summary.json").is_file():
        raise SystemExit(f"Not an eval run: {run_dir}")

    graders_dir = run_dir / "graders"
    graders_dir.mkdir(exist_ok=True)
    schema = ROOT / "evaluator-schema.json"

    for name, role in PERSONAS.items():
        print(f"grading: {name}", flush=True)
        output = graders_dir / f"{name}.json"
        trace = graders_dir / f"{name}.trace.jsonl"
        stderr = graders_dir / f"{name}.stderr.txt"
        prompt = f"""{role}

评测目录：{run_dir}
评分规则：{ROOT / 'rubric.md'}

要求：
1. 覆盖 summary.json 中全部场景，不遗漏。
2. evidence 必须引用回答或轨迹中的具体事实。
3. 不评判 Skill 作者意图，只评判本次可观察效果。
4. 不修改任何文件；只输出符合给定 JSON Schema 的评分。
5. PASS 通常要求 18-20 分，PARTIAL 为 15-17 分，其余为 FAIL。
"""
        cmd = [
            "codex", "exec",
            "--cd", str(ROOT),
            "--ephemeral",
            "--ignore-user-config",
            "--ignore-rules",
            "--approve-for-me",
            "--json",
            "--output-schema", str(schema),
            "--output-last-message", str(output),
            prompt,
        ]
        proc = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8", timeout=480)
        trace.write_text(proc.stdout, encoding="utf-8")
        stderr.write_text(proc.stderr, encoding="utf-8")
        if proc.returncode:
            print(f"  failed with return code {proc.returncode}", flush=True)


if __name__ == "__main__":
    main()
