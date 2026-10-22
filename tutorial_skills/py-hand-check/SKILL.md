---
name: py-hand-check
description: Python 代码自查清单。写完或改完任何 Python 代码后、或被要求检查/审查代码时使用。检查项:变量拼写手滑(如 contet/emial/DATATBASE_URL)、函数参数类型标注、泛型参数化(dict/list 不裸写)、改动后是否跑了 ruff 与 mypy 验证。
---

# py-hand-check:Python 代码自查清单

## 第一步:拼写扫描(确定性的事,交给脚本)

对目标文件运行扫描脚本:

    bash ~/tutorial_skills/py-hand-check/scripts/check_typos.sh <文件...>

脚本只找已知手滑词。退出 1 表示发现候选问题,报告位置和建议;不要自动改源码。
退出 2 表示扫描失败,先解决文件或命令问题。退出 0 仅表示本词表未命中。
本项目由用户亲手改源码,本 Skill 只检查、讲解并给修改片段。

## 第二步:人工检查(需要判断的事,模型来)

按顺序核对:

1. **拼写与命名**:变量名是否手滑(重点:contet → content、emial → email、
   DATATBASE → DATABASE)。命名风格与所在文件既有风格一致。
2. **参数类型标注**:所有函数参数必须标注类型;`dict` / `list` 裸写不行,要参数化
   (如 `dict[str, object]`);返回类型不写。
3. **Any 边界**:json.loads / 外部响应的 Any 结果必须就近收窄
   (isinstance + cast,或 pydantic 建形状),禁止链式裸取。

## 第三步:验证(不可跳过)

    uv run python -m ruff check <改过的文件>
    uv run python -m mypy <改过的文件>

两条都绿了才算完。跳过验证 = 本次检查不合格。

## 输出格式

按「✅/❌ 检查项 → 位置 → 建议」列表汇报,最后一行给结论。
