#!/usr/bin/env python3
"""
emit_lineage.py - 通过 DataHub 官方 SDK 写入血缘（表级 + 列级）

读取 lineage_recipe.yaml，用 DatahubRestEmitter + MetadataChangeProposalWrapper +
schema_classes.UpstreamLineageClass 写入 GMS（POST /aspects?action=ingestProposal，
SDK 自动处理 proposal 外层与 value/contentType 包装）。

双层血缘（v1.6）：
  - 表级：通过 UpstreamLineageClass.upstreams (UpstreamClass 列表) 表达
  - 列级：通过 UpstreamLineageClass.fineGrainedLineages (FineGrainedLineageClass 列表)
    表达；每条 FineGrainedLineageClass 含 upstreamType/downstreamType/upstreams/
    downstreams/transformOperation 字段。
    schemaField URN 形如 urn:li:schemaField:(urn:li:dataset:(...),<column>,...)。
    本脚本优先采用 fineGrainedLineages 路径（DataHub v1.6 官方推荐，
    GraphQL/UI 直接渲染），不另写 schemaMetadata.fieldRef。

架构变更（提交 bb03262 起）：移除 Neo4j 依赖，血缘只走 GMS REST。
本版本进一步弃用裸 requests 手写调用，改用官方 SDK（与 emit_via_rest_emitter.py 同模式），
确保字段名 dataset / type / aspect 包装符合 DataHub v1.6 协议。

Phase 2 升级（nl2sql-with-lineage-context）：
  - lineage_recipe.yaml 增 columnMappings 字段（可选）
  - 本脚本对含 columnMappings 的边自动追加 fineGrainedLineages 写入
  - 未声明 columnMappings 的边：仅写表级，不报错

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

def build_schema_field_urn(dataset_urn: str, column: str) -> str:
    """构造 DataHub schemaField URN（列级血缘目标）。"""
    return f"urn:li:schemaField:({dataset_urn},{column})"

def build_upstream_lineage_aspect(lineage_config: dict, dataset_urn: str):
    """构造 UpstreamLineageClass（表级 + 列级）。

    DataHub 的 Upstream record 字段名为 dataset（非 upstreamEntity），
    type 取 TRANSFORMED（业务血缘与加工血缘都用此值，DataHub enum 无 business 类型，
    语义区分靠 lineage_recipe.yaml 的 description）。
    auditStamp 由 SDK 填默认值。

    列级血缘：recipe 中声明的 columnMappings 列表会转成 FineGrainedLineageClass 记录
    追加到 fineGrainedLineages 字段。upstreamType=FIELD_SET、downstreamType=FIELD，
    upstreams/downstreams 为 schemaField URN 列表。
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

    fine_grained = _build_fine_grained_lineages(
        lineage_config.get("columnMappings"),
        upstream_list,
        dataset_urn,
    )

    return schema.UpstreamLineageClass(
        upstreams=upstreams,
        fineGrainedLineages=fine_grained or None,
    )

def _build_fine_grained_lineages(column_mappings, upstream_list, downstream_urn):
    """把 columnMappings 转成 FineGrainedLineageClass 列表。

    约定：每条 columnMappings 对应单一 upstream dataset（取 upstream_list[0]）。
    若某 downstream 实际由多 upstream 派生（DWA 通常是单上游），需在 recipe 中拆条
    声明；本演示 3 条 DWA 边均为单 upstream 场景。
    """
    if not column_mappings:
        return None
    if len(upstream_list) != 1:
        print(
            f"  [warn] columnMappings 不支持多 upstream 场景"
            f"（当前 {len(upstream_list)} 个 upstream），跳过列级写入"
        )
        return None

    upstream = upstream_list[0]
    upstream_dataset_urn = build_urn(upstream["platform"], upstream["table"])
    upstream_field_urn = build_schema_field_urn(
        upstream_dataset_urn, "ALL_COLUMNS"
    )

    fgl_list = []
    for cm in column_mappings:
        down_col = cm["downstream_column"]
        up_col = cm["upstream_column"]
        transform = cm.get("transformation")

        if up_col == "*":
            up_field_urn = upstream_field_urn
        else:
            up_field_urn = build_schema_field_urn(
                upstream_dataset_urn, up_col
            )
        down_field_urn = build_schema_field_urn(downstream_urn, down_col)

        fgl = schema.FineGrainedLineageClass(
            upstreamType="FIELD_SET",
            downstreamType="FIELD",
            upstreams=[up_field_urn],
            downstreams=[down_field_urn],
            transformOperation=transform or "IDENTITY",
            confidenceScore=1.0,
        )
        fgl_list.append(fgl)

    return fgl_list

def print_lineage_graph(lineage_relationships: list):
    """打印血缘图的文本表示。"""
    print("\n" + "=" * 60)
    print("LINEAGE GRAPH")
    print("=" * 60)

    nodes = set()
    edges = []
    column_edges = []

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

            for cm in rel.get("columnMappings", []) or []:
                column_edges.append((
                    f"{upstream_list[0]['platform']}.{upstream_list[0]['table']}.{cm['upstream_column']}",
                    f"{down_key}.{cm['downstream_column']}",
                    cm.get("transformation", "IDENTITY"),
                ))

    print("\nNodes (datasets):")
    for node in sorted(nodes):
        print(f"  [{node}]")

    print("\nEdges (table-level lineage):")
    for src, dst in sorted(edges):
        print(f"  {src} --> {dst}")

    if column_edges:
        print("\nEdges (column-level lineage):")
        for src, dst, t in column_edges:
            print(f"  {src} --[{t}]--> {dst}")

    print("=" * 60 + "\n")

def main():
    """主入口：读取 recipe，逐条写入血缘。"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    recipe_path = os.environ.get(
        "LINEAGE_RECIPE", os.path.join(project_root, "lineage_recipe.yaml")
    )

    print(f"Loading lineage recipe from: {recipe_path}")

    recipe = load_recipe(recipe_path)
    lineage_relationships = recipe.get("lineage_relationships", [])

    edges_with_upstream = [
        r for r in lineage_relationships if r.get("downstream") and r.get("upstream")
    ]
    print(
        f"Found {len(lineage_relationships)} relationships, "
        f"{len(edges_with_upstream)} with upstream edges"
    )

    emitter = DatahubRestEmitter(gms_server=GMS_HOST, timeout_sec=30)
    print(f"Connected to GMS: {GMS_HOST}\n")

    success = 0
    failed = 0
    column_success = 0

    for rel in edges_with_upstream:
        downstream = rel["downstream"]
        downstream_urn = build_urn(downstream["platform"], downstream["table"])
        down_key = f"{downstream['platform']}.{downstream['table']}"
        print(f"Processing: {down_key}")

        aspect = build_upstream_lineage_aspect(rel, downstream_urn)
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
            fgl_count = len(aspect.fineGrainedLineages or [])
            extra = (
                f", {fgl_count} fineGrainedLineages"
                if fgl_count
                else ""
            )
            print(
                f"  [GMS] Wrote upstreamLineage ({upstream_count} upstreams{extra})"
            )
            success += 1
            if fgl_count:
                column_success += fgl_count
        except Exception as e:
            print(f"  [GMS] FAILED: {e}")
            failed += 1

    print("\n" + "-" * 40)
    print("SUMMARY")
    print("-" * 40)
    print(f"  Table-level edges written:    {success}")
    print(f"  Column-level mappings written: {column_success}")
    print(f"  Edges failed:                 {failed}")

    print_lineage_graph(lineage_relationships)

    if failed:
        sys.exit(1)

if __name__ == "__main__":
    main()
