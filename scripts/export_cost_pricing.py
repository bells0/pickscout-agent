#!/usr/bin/env python3
"""Export the canonical cost-pricing Skill as a portable directory and ZIP."""
import argparse
import json
import posixpath
import re
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit
from zipfile import ZIP_DEFLATED, ZipFile

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "amazon-cost-pricing"
DEFAULT_SOURCE_REPO = "https://github.com/bells0/pickscout-agent"
VERSION = "v1.0 未定稿"
SOURCE_FILES = (
    ("skills/amazon-cost-pricing/SKILL.md", "SKILL.md"),
    ("skills/amazon-cost-pricing/agents/openai.yaml", "agents/openai.yaml"),
    ("docs/cost-pricing-methodology-v1.0.md", "references/cost-pricing-methodology-v1.0.md"),
    ("docs/decisions/0018-cost-pricing-capability.md", "references/decisions/0018-cost-pricing-capability.md"),
    ("scripts/cost_pricing.py", "scripts/cost_pricing.py"),
    ("scripts/unit_economics.py", "scripts/unit_economics.py"),
    ("templates/cost-pricing-input.json", "assets/cost-pricing-input.json"),
    ("LICENSE", "LICENSE"),
)
MARKDOWN_LINK = re.compile(r"(!?\[[^\]\n]*\]\()([^\s)]+)(\))")
PRIVATE_MARKERS = (
    "/Users/", "/home/", "C:\\Users\\", "local-data/",
    ".agent-teamworks/", "thread_id", "threadId", "rollout_summaries/",
)


def _relative_link(target, source, destination, mapping):
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc or target.startswith("#"):
        return target
    path, separator, fragment = target.partition("#")
    source_target = posixpath.normpath(
        posixpath.join(posixpath.dirname(source), unquote(path))
    )
    if source_target not in mapping:
        raise ValueError("unbundled local link in " + source + ": " + target)
    relative = posixpath.relpath(mapping[source_target], posixpath.dirname(destination) or ".")
    return relative + (separator + fragment if separator else "")


def rewrite_markdown(text, source, destination):
    """Relocate declared local resources; reject links outside the export list."""
    mapping = dict(SOURCE_FILES)
    text = MARKDOWN_LINK.sub(
        lambda match: match[1] + _relative_link(match[2], source, destination, mapping) + match[3],
        text,
    )
    # Backticked paths and shell examples are relative to the package root.
    replacements = {
        "../../docs/cost-pricing-methodology-v1.0.md": "references/cost-pricing-methodology-v1.0.md",
        "../../scripts/cost_pricing.py": "scripts/cost_pricing.py",
        "../../templates/cost-pricing-input.json": "assets/cost-pricing-input.json",
        "docs/cost-pricing-methodology-v1.0.md": "references/cost-pricing-methodology-v1.0.md",
        "docs/decisions/0018-cost-pricing-capability.md": "references/decisions/0018-cost-pricing-capability.md",
        "skills/amazon-cost-pricing/SKILL.md": "SKILL.md",
        "templates/cost-pricing-input.json": "assets/cost-pricing-input.json",
        "artifacts/cost-pricing/<task-id>/": "outputs/<task-id>/",
        "artifacts/cost-pricing/": "outputs/",
    }
    for original, replacement in replacements.items():
        text = text.replace(original, replacement)
    if source == "skills/amazon-cost-pricing/SKILL.md":
        lines = text.splitlines()
        for index, line in enumerate(lines):
            if "唯一维护源" in line and "skills/amazon-cost-pricing/" in line:
                lines[index] = (
                    "本目录是PickScout成本与定价Skill的导出快照；唯一维护源及版本见"
                    "[SOURCE.json](SOURCE.json)。读取包内[成本与定价方法]"
                    "(references/cost-pricing-methodology-v1.0.md)，复用同一方法与计算工具。"
                )
        text = "\n".join(lines) + "\n"
        text += (
            "\n## 独立目录使用\n\n"
            "计算只需Python 3标准库，无须Data或其他外部插件。没有报告插件时，"
            "按本方法交付完整Markdown或简单HTML，保留费用来源、算式、"
            "保本/市场/20%及30%目标价和关键未知。\n\n"
            "将本包作为工作目录可运行"
            "`python3 scripts/cost_pricing.py assets/cost-pricing-input.json`。"
            "从其他工作目录调用时，将脚本和输入参数换成其实际路径。"
            "示例是合成数据，真实输入与报告保存到调用者指定的本地目录；"
            "不要求原PickScout仓库、其他项目、私人资料或运行绑定。\n"
        )
    return text


def _readme():
    return """# Amazon 成本与定价 Skill — v1.0 未定稿

此目录是可独立复制的分享快照，唯一维护源为PickScout；来源与调用者提供的commit/ref见[SOURCE.json](SOURCE.json)。auto-amazon或其他仓库的备份仅作快照，不在备份处维护第二份方法。

## 使用

先阅读[SKILL.md](SKILL.md)与[成本方法](references/cost-pricing-methodology-v1.0.md)。在此目录中，用Python 3运行：

```sh
python3 scripts/cost_pricing.py assets/cost-pricing-input.json
```

也可从任意工作目录，用实际路径指向脚本与输入。计算器只依赖Python标准库及同目录的[金额汇总模块](scripts/unit_economics.py)。输入示例全部为合成数据；真实报价、费率、销售单元及情景须另行准备。

无Data或其他报告插件时，仍可核算并交付完整Markdown或简单HTML。市场接受价、费表与包规归档、装箱及情景需Agent准备；脚本不会自动调查。所得税和未计项目的范围按方法说明。

## 包含内容

- [方法](references/cost-pricing-methodology-v1.0.md)与[能力决定](references/decisions/0018-cost-pricing-capability.md)
- [计算器](scripts/cost_pricing.py)、金额模块及[合成输入](assets/cost-pricing-input.json)
- Skill元信息与原[LICENSE](LICENSE)

仅输出到导出命令指定的本地目录，不自动安装用户级Skill、不改配置。完整复制本目录或解压ZIP即可使用。真实输入/报告留在调用者本地工作目录，不随分享包复制。
"""


def _validate_package(files):
    for name, content in files.items():
        text = content.decode("utf-8")
        for marker in PRIVATE_MARKERS:
            if marker in text:
                raise ValueError("private local reference in " + name + ": " + marker)
        if name.endswith(".md"):
            for match in MARKDOWN_LINK.finditer(text):
                target = match[2]
                parsed = urlsplit(target)
                if parsed.scheme or parsed.netloc or target.startswith("#"):
                    continue
                local = posixpath.normpath(posixpath.join(posixpath.dirname(name), unquote(target.split("#", 1)[0])))
                if local not in files:
                    raise ValueError("missing packaged link in " + name + ": " + target)


def export_cost_pricing(output_dir, source_ref, source_repo=DEFAULT_SOURCE_REPO, source_root=REPO_ROOT):
    """Read the current whitelist and create a new package plus sibling ZIP."""
    if not source_ref.strip() or any(c in source_ref + source_repo for c in "\r\n"):
        raise ValueError("source ref and repository must be non-empty single-line values")
    if not source_repo.strip():
        raise ValueError("source repository must be non-empty")
    root = Path(source_root).resolve()
    output = Path(output_dir).expanduser().resolve()
    package, archive = output / PACKAGE_NAME, output / (PACKAGE_NAME + ".zip")
    if any(path.exists() or path.is_symlink() for path in (package, archive)):
        raise FileExistsError("package or ZIP already exists; choose a fresh output directory")
    files = {}
    for source, destination in SOURCE_FILES:
        path = (root / source).resolve()
        path.relative_to(root)
        content = path.read_bytes()
        if source.endswith(".md"):
            content = rewrite_markdown(content.decode("utf-8"), source, destination).encode("utf-8")
        files[destination] = content
    files["README.md"] = _readme().encode("utf-8")
    files["SOURCE.json"] = (json.dumps({
        "name": PACKAGE_NAME,
        "version": VERSION,
        "source_repository": source_repo,
        "source_ref": source_ref,
        "source_ref_supplied_by_caller": True,
        "maintenance": "PickScout is the sole source; this directory and auto-amazon copies are snapshots.",
        "source_files": [{"source": source, "packaged": destination} for source, destination in SOURCE_FILES],
        "generated_files": ["README.md", "SOURCE.json"],
        "transformations": "Relocated declared resource links/paths and added standalone usage; no private task files copied.",
    }, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    _validate_package(files)
    package.mkdir(parents=True)
    for name, content in files.items():
        target = package / PurePosixPath(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as zipped:
        for name in sorted(files):
            zipped.writestr(PACKAGE_NAME + "/" + name, files[name])
    return {"directory": str(package), "zip": str(archive), "source_ref": source_ref}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path, help="local parent directory for package and ZIP")
    parser.add_argument("--source-ref", required=True, help="caller-supplied source commit/ref; no Git lookup")
    parser.add_argument("--source-repo", default=DEFAULT_SOURCE_REPO, help="source repository recorded in SOURCE.json")
    args = parser.parse_args()
    try:
        result = export_cost_pricing(args.output_dir, args.source_ref, args.source_repo)
    except (OSError, ValueError, UnicodeError) as exc:
        parser.exit(2, "error: " + str(exc) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
