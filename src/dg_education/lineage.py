"""离线血缘分析 API（模块三）。

从 lineage_recipe.yaml 读取血缘图，提供上下游遍历、影响面（blast-radius）
计算与 ASCII 可视化。所有操作离线，不触碰 GMS/OpenSearch。

教学 notebook（module3.ipynb）通过本模块读取「recipe 自建图」，
与 scripts/query_lineage.py 返回的「DataHub 真图」对比，确认二者一致。

血缘图模型：networkx.DiGraph，边方向 = upstream → downstream
（数据流向：源表 → 派生表），与 lineage_recipe.yaml 中
`downstream ← upstream` 的语义一致。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import networkx as nx
import yaml

# recipe 默认路径（项目根目录）。notebook 运行在 notebook/ 下，
# 调用方通常传入显式路径；此默认仅作 fallback。
DEFAULT_RECIPE = Path(__file__).resolve().parents[2] / "lineage_recipe.yaml"


def _node_key(platform: str, table: str) -> str:
    """节点简写：platform.table。"""
    return f"{platform}.{table}"


def load_lineage_graph(recipe_path: str | Path = DEFAULT_RECIPE) -> nx.DiGraph:
    """从 lineage_recipe.yaml 构建有向血缘图。

    边方向 upstream → downstream（数据流向）。一条 relationship 若含多个
    upstream，则为每对 upstream→downstream 各加一条边。
    """
    with open(recipe_path, "r", encoding="utf-8") as f:
        recipe = yaml.safe_load(f)

    g = nx.DiGraph()
    for rel in recipe.get("lineage_relationships", []):
        downstream = rel.get("downstream")
        if not downstream:
            continue
        down_key = _node_key(downstream["platform"], downstream["table"])
        g.add_node(
            down_key,
            platform=downstream["platform"],
            table=downstream["table"],
            description=rel.get("description", ""),
            type=rel.get("type", ""),
        )
        for upstream in rel.get("upstream") or []:
            up_key = _node_key(upstream["platform"], upstream["table"])
            # 上游节点可能在本 recipe 无独立 relationship 声明，补建
            if up_key not in g:
                g.add_node(
                    up_key,
                    platform=upstream["platform"],
                    table=upstream["table"],
                    description="",
                    type="",
                )
            g.add_edge(up_key, down_key, join_key=upstream.get("join_key", ""))
    return g


def upstream(graph: nx.DiGraph, node: str) -> list[str]:
    """返回 node 的直接上游（数据来源），按字母序。"""
    if node not in graph:
        return []
    return sorted(graph.predecessors(node))


def downstream(graph: nx.DiGraph, node: str) -> list[str]:
    """返回 node 的直接下游（去向），按字母序。"""
    if node not in graph:
        return []
    return sorted(graph.successors(node))


def blast_radius(graph: nx.DiGraph, node: str) -> list[str]:
    """影响面：node 的所有下游节点（传递闭包，不含 node 自身）。

    业务含义：node 数据出问题，会影响哪些下游表。按拓扑序返回。
    """
    if node not in graph:
        return []
    descendants = nx.descendants(graph, node)
    # 按拓扑序排列，让「近的下游」排前
    return [n for n in nx.topological_sort(graph) if n in descendants]


def ancestors(graph: nx.DiGraph, node: str) -> list[str]:
    """追根溯源：node 的所有上游节点（传递闭包，不含 node 自身），拓扑序。"""
    if node not in graph:
        return []
    anc = nx.ancestors(graph, node)
    return [n for n in nx.topological_sort(graph) if n in anc]


# 节点分层（用于 ASCII 可视化按层排列）
_LAYER_ORDER = ["sap_erp", "pi_system", "lims", "oa", "scada", "dwd", "dwa"]


def _layer_of(node_key: str) -> int:
    platform = node_key.split(".", 1)[0]
    return _LAYER_ORDER.index(platform) if platform in _LAYER_ORDER else len(_LAYER_ORDER)


def render_ascii(graph: nx.DiGraph) -> str:
    """渲染分层文本血缘图（源层在上，DWA 层在下）。"""
    lines = ["血缘图（上游 → 下游，数据流向自上而下）", "=" * 56]

    # 按层分组
    by_layer: dict[int, list[str]] = {}
    for n in graph.nodes:
        by_layer.setdefault(_layer_of(n), []).append(n)

    for layer in sorted(by_layer):
        nodes = sorted(by_layer[layer])
        platform = nodes[0].split(".", 1)[0] if nodes else ""
        lines.append(f"\n【{platform} 层】")
        for n in nodes:
            ups = upstream(graph, n)
            downs = downstream(graph, n)
            tag = " (源头)" if not ups else ""
            lines.append(f"  {n}{tag}")
            for u in ups:
                lines.append(f"      ↑ {u}")
            for d in downs:
                lines.append(f"      ↓ {d}")

    lines.append("=" * 56)
    lines.append(f"节点 {graph.number_of_nodes()} / 边 {graph.number_of_edges()}")
    return "\n".join(lines)


def edge_list(graph: nx.DiGraph) -> list[dict[str, str]]:
    """返回所有边 [{upstream, downstream}]，便于与 DataHub 真图对比。"""
    return [{"upstream": u, "downstream": v} for u, v in graph.edges()]
