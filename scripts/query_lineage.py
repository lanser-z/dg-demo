#!/usr/bin/env python3
"""
query_lineage.py — 只读查询 DataHub 中已写入的血缘，输出 JSON 到 stdout。

对 lineage_recipe.yaml 中每条有 upstream 的 downstream dataset，
GET http://localhost:28080/aspects/<urn>?aspect=upstreamLineage 取真实上游，
汇总成 JSON 输出。

本脚本是只读的：MUST NOT 写入任何 GMS/OpenSearch 数据。
教学 notebook 通过 subprocess 调用本脚本获取「DataHub 真图」，
与离线从 recipe 自建的图做对比（notebook 不直连服务）。

Usage:
    uv run python scripts/query_lineage.py
    uv run python scripts/query_lineage.py --recipe path/to/lineage_recipe.yaml

stdout 输出形如：
    [
      {"dataset": "lims.samples", "urn": "urn:li:dataset:(...)",
       "upstreams": ["urn:li:dataset:(...vbak...)", "urn:li:dataset:(...vbap...)"]},
      ...
    ]
"""
import argparse
import json
import os
import sys
import urllib.parse

import requests
import yaml

GMS_HOST = "http://localhost:28080"
AUTH = ("datahub", "datahub")
TIMEOUT = 15


def load_recipe(recipe_path: str) -> dict:
    with open(recipe_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_urn(platform: str, table: str) -> str:
    return f"urn:li:dataset:(urn:li:dataPlatform:{platform},{table},PROD)"


def _short(urn: str) -> str:
    """urn → platform.table 简写，便于人读。"""
    # urn:li:dataset:(urn:li:dataPlatform:{platform},{table},PROD)
    try:
        inner = urn[urn.find("(urn:") + 1 : urn.rfind(")")]
        seg = inner.split(":")[-1].split(",")
        return f"{seg[0]}.{seg[1]}"
    except Exception:
        return urn


def query_upstream_lineage(urn: str) -> list:
    """GET /aspects/<urlencoded_urn>?aspect=upstreamLineage，返回上游 URN 列表。

    只读查询。GMS 未写入该 aspect 或 urn 不存在时返回空列表。
    """
    encoded = urllib.parse.quote(urn, safe="")
    url = f"{GMS_HOST}/aspects/{encoded}?aspect=upstreamLineage&version=0"
    try:
        resp = requests.get(url, auth=AUTH, timeout=TIMEOUT)
    except requests.exceptions.RequestException as e:
        print(f"[query] {url} 请求失败: {e}", file=sys.stderr)
        return []

    if resp.status_code == 404:
        return []
    if resp.status_code != 200:
        print(f"[query] {url} 返回 {resp.status_code}", file=sys.stderr)
        return []

    data = resp.json()
    # GMS 返回结构：{"aspectName":"upstreamLineage","value":{...},...} 或 {<aspect>: {...}}
    value = data.get("value", data)
    # value 可能是 dict（含 upstreams）或 JSON 字符串
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return []
    upstreams = value.get("upstreams", []) if isinstance(value, dict) else []
    return [u.get("dataset") for u in upstreams if u.get("dataset")]


def collect_lineage(recipe_path: str) -> list:
    """对 recipe 中每条有 upstream 的 downstream，查 GMS 真实上游，返回记录列表。"""
    recipe = load_recipe(recipe_path)
    rels = recipe.get("lineage_relationships", [])
    results = []
    for rel in rels:
        downstream = rel.get("downstream")
        if not downstream or not rel.get("upstream"):
            continue
        urn = build_urn(downstream["platform"], downstream["table"])
        real_upstreams = query_upstream_lineage(urn)
        results.append(
            {
                "dataset": f"{downstream['platform']}.{downstream['table']}",
                "urn": urn,
                "upstreams": real_upstreams,
                "upstreams_short": [_short(u) for u in real_upstreams],
            }
        )
    return results


def main():
    parser = argparse.ArgumentParser(description="只读查询 DataHub 血缘并输出 JSON")
    parser.add_argument(
        "--recipe",
        default=None,
        help="lineage_recipe.yaml 路径（默认项目根目录）",
    )
    args = parser.parse_args()

    if args.recipe:
        recipe_path = args.recipe
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        recipe_path = os.path.join(project_root, "lineage_recipe.yaml")

    if not os.path.exists(recipe_path):
        print(f"[query] recipe 不存在: {recipe_path}", file=sys.stderr)
        sys.exit(2)

    results = collect_lineage(recipe_path)
    json.dump(results, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
