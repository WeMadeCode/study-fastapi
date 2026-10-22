import json
import re
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import cast

import yaml


@dataclass(frozen=True)
class SkillCard:
    name: str
    description: str
    directory: Path


def read_limited(path: Path, limit: int = 32_768):
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError(f"文件超过 {limit} 字节:{path.name}")
    return raw.decode("utf-8")


def split_skill(text: str):
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise ValueError("SKILL.md 必须以 --- 开头")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError("缺少 frontmatter 结束符") from exc
    # safe_load 不构造任意 Python 对象;返回值依然是 Any,随后立即检查映射与键类型。
    try:
        loaded = yaml.safe_load("\n".join(lines[1:end]))
    except yaml.YAMLError as exc:
        raise ValueError("frontmatter 不是合法 YAML") from exc
    if not isinstance(loaded, dict) or not all(isinstance(k, str) for k in loaded):
        raise ValueError("frontmatter 必须是字符串键的映射")
    metadata = cast(dict[str, object], loaded)
    name, description = metadata.get("name"), metadata.get("description")
    if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        raise ValueError("name 仅允许小写字母、数字、单个连字符")
    if len(name) > 64 or not isinstance(description, str) or not description.strip() or len(description) > 1024:
        raise ValueError("name/description 长度或类型不合法")
    body = "\n".join(lines[end + 1 :]).strip()
    if not body:
        raise ValueError("本练习要求正文非空")
    return name, description.strip(), body


def scan_skills(root: Path):
    root = root.resolve(strict=True)
    cards: dict[str, SkillCard] = {}
    for path in sorted(root.glob("*/SKILL.md")):
        resolved = path.resolve(strict=True)
        if not resolved.is_relative_to(root):
            raise ValueError("Skill 符号链接越出目录")
        name, description, _ = split_skill(read_limited(resolved))
        if name != path.parent.name or name in cards:
            raise ValueError("Skill 名称必须与目录一致且不能重复")
        cards[name] = SkillCard(name, description, resolved.parent)
    return cards


def build_index(cards: dict[str, SkillCard]):
    # 索引只包含元数据;正文没有被送进模型上下文。
    return json.dumps([{"name": c.name, "description": c.description} for c in cards.values()], ensure_ascii=False)


def load_skill(cards: dict[str, SkillCard], name: str):
    card = cards.get(name)
    if card is None:
        raise ValueError(f"未知 Skill:{name}")
    path = (card.directory / "SKILL.md").resolve(strict=True)
    if not path.is_relative_to(card.directory):
        raise ValueError("Skill 正文越出已发现目录")
    found_name, _, body = split_skill(read_limited(path))
    if found_name != name:
        raise ValueError("文件已改变,请重新扫描")
    return body


def read_reference(cards: dict[str, SkillCard], name: str, relative: str):
    card = cards.get(name)
    if card is None:
        raise ValueError("未知 Skill")
    base = (card.directory / "references").resolve(strict=True)
    # 先检查 references 本身,防止它是一个越出 skill 的符号链接。
    if not base.is_relative_to(card.directory):
        raise ValueError("references 越出 Skill 目录")
    target = (card.directory / relative).resolve(strict=True)
    if not target.is_relative_to(base) or not target.is_file():
        raise ValueError("只允许读取该 Skill 的 references 文件")
    return read_limited(target)


def main():
    # 可运行自测不安装全局 Skill,也不连接模型。
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        folder = root / "py-hand-check"
        (folder / "references").mkdir(parents=True)
        (folder / "SKILL.md").write_text(
            "---\nname: py-hand-check\ndescription: 检查 Python 参数类型和拼写。\n---\n"
            "先运行检查,再阅读 references/types.md。正文标记 ONLY_BODY。",
            encoding="utf-8",
        )
        (folder / "references/types.md").write_text("参数必须标注,返回类型可省略。", encoding="utf-8")
        (root / "outside.txt").write_text("不允许读", encoding="utf-8")
        cards = scan_skills(root)
        assert "ONLY_BODY" not in build_index(cards)
        assert "ONLY_BODY" in load_skill(cards, "py-hand-check")
        assert "参数" in read_reference(cards, "py-hand-check", "references/types.md")
        for operation in (
            lambda: load_skill(cards, "missing"),
            lambda: read_reference(cards, "py-hand-check", "../outside.txt"),
            lambda: split_skill("---\nname: bad\ndescription: [不是字符串]\n---\nx"),
        ):
            try:
                operation()
            except ValueError:
                pass
            else:
                raise AssertionError("应拒绝非法输入")
        print("T4:元数据/正文隔离、引用加载、未知名称、路径越界、元数据类型均通过")


if __name__ == "__main__":
    main()
