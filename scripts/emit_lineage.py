#!/usr/bin/env python3
"""
emit_lineage.py - 通过 DataHub 官方 SDK 写入 upstreamLineage 血缘

读取 lineage_recipe.yaml，用 DatahubRestEmitter + MetadataChangeProposalWrapper +
schema_classes.UpstreamLineageClass 写入 GMS（POST /aspects?action=ingestProposal，
SDK 自动处理 proposal 外层与 value/contentType 包装）。

架构变更（提交 bb03262 起）：移除 Neo4j 依赖，血缘只走 GMS REST。
本版本进一步弃用裸 requests 手写调用，改用官方 SDK（与 emit_via_rest_emitter.py 同模式），
确保字段名 dataset / type / aspect 包装符合 DataHub v1.6 协议。

Usage: uv run python scripts/emit_lineage.py
"""

import os
import sys

import yaml
from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.emitter.rest_emitter import DatahubRestEmitter
import datahub.metadata.schema_classes as schema

GMS_HOST = "http://localhost:28080"


def load_recipe(recipe_path: str) -> dict:
    """从 YAML 加载血缘 recipe。"""
    with open(recipe_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_urn(platform: str, table: str) -> str:
    """构造 DataHub dataset URN。"""
    return f"urn:li:dataset:(urn:li:dataPlatform:{platform},{table},PROD)"


def build_upstream_lineage_aspect(lineage_config: dict):
    """构造 UpstreamLineageClass。

    DataHub 的 Upstream record 字段名为 dataset（非 upstreamEntity），
    type 取 TRANSFORMED（业务血缘与加工血缘都用此值，DataHub enum 无 business 类型，
    语义区分靠 lineage_recipe.yaml 的 description）。
    auditStamp 由 SDK 填默认值。
    """
    upstream_list = lineage_config.get("upstream", [])
    if not upstream_list:
        return None

    upstreams = []
    for upstream in upstream_list:
        upstream_urn = build_urn(upstream["platform"], upstream["table"])
        upstreams.append(
            schema.UpstreamClass(
                dataset=upstream_urn,
                type="TRANSFORMED",
            )
        )

    return schema.UpstreamLineageClass(upstreams=upstreams)


def print_lineage_graph(lineage_relationships: list):
    """打印血缘图的文本表示。"""
    print("\n" + "=" * 60)
    print("LINEAGE GRAPH")
    print("=" * 60)

    nodes = set()
    edges = []

    for rel in lineage_relationships:
        downstream = rel.get("downstream")
        upstream_list = rel.get("upstream", [])

        if downstream:
            down_key = f"{downstream['platform']}.{downstream['table']}"
            nodes.add(down_key)

            if upstream_list:
                for upstream in upstream_list:
                    up_key = f"{upstream['platform']}.{upstream['table']}"
                    nodes.add(up_key)
                    edges.append((up_key, down_key))

    print("\nNodes (datasets):")
    for node in sorted(nodes):
        print(f"  [{node}]")

    print("\nEdges (lineage flow):")
    for src, dst in sorted(edges):
        print(f"  {src} --> {dst}")

    print("=" * 60 + "\n")


def main():
    """主入口：读取 recipe，逐条写入血缘。"""
    # 定位 recipe 路径（允许 LINEAGE_RECIPE 环境变量覆盖）
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    recipe_path = os.environ.get(
        "LINEAGE_RECIPE", os.path.join(project_root, "lineage_recipe.yaml")
    )

    print(f"Loading lineage recipe from: {recipe_path}")

    recipe = load_recipe(recipe_path)
    lineage_relationships = recipe.get("lineage_relationships", [])

    # 仅处理有 upstream 的关系（源头节点 upstream=null，跳过）
    edges_with_upstream = [
        r for r in lineage_relationships if r.get("downstream") and r.get("upstream")
    ]
    print(f"Found {len(lineage_relationships)} relationships, "
          f"{len(edges_with_upstream)} with upstream edges")

    emitter = DatahubRestEmitter(gms_server=GMS_HOST, timeout_sec=30)
    print(f"Connected to GMS: {GMS_HOST}\n")

    success = 0
    failed = 0

    for rel in edges_with_upstream:
        downstream = rel["downstream"]
        downstream_urn = build_urn(downstream["platform"], downstream["table"])
        down_key = f"{downstream['platform']}.{downstream['table']}"
        print(f"Processing: {down_key}")

        aspect = build_upstream_lineage_aspect(rel)
        if aspect is None:
            continue

        try:
            mcp = MetadataChangeProposalWrapper(
                entityUrn=downstream_urn,
                aspect=aspect,
                changeType="UPSERT",
            )
            emitter.emit(mcp)
            upstream_count = len(rel["upstream"])
            print(f"  [GMS] Wrote upstreamLineage ({upstream_count} upstreams)")
            success += 1
        except Exception as e:
            print(f"  [GMS] FAILED: {e}")
            failed += 1

    # 汇总
    print("\n" + "-" * 40)
    print("SUMMARY")
    print("-" * 40)
    print(f"  GMS writes successful: {success}")
    print(f"  GMS writes failed:     {failed}")

    # 始终打印血缘图
    print_lineage_graph(lineage_relationships)

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
