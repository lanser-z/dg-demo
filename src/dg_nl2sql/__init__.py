"""dg_nl2sql — Natural Language to SQL context builder.

从 DataHub GMS 真实查询血缘/schema/词典，结构化为 LLM 可消费的 context JSON。
**严禁使用 lineage_recipe.yaml 作为 fallback**（那是模拟的声明式血缘，不是 GMS 真实图）。

公开 API:
    build_context(question: str) -> dict
"""

from dg_nl2sql.context_builder import build_context

__all__ = ["build_context"]
