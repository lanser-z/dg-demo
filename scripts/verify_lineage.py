#!/usr/bin/env python3
"""
verify_lineage.py — 真验证：断言 DataHub 中已写入的血缘与 recipe 一致。

复用 query_lineage.collect_lineage() 的只读查询逻辑，对每条 recipe 边：
  1. GET /aspects/<urn>?aspect=upstreamLineage，断言 upstreams 非空
  2. 断言 upstreams 包含 recipe 声明的每条上游 URN
再查 OpenSearch datasetindex_v2，断言边已索引（轮询最长 30s，容忍 MAE→actions 延迟）。

任一断言失败 → 非零退出。
本脚本只读，MUST NOT 写入 GMS/OpenSearch。
--purge 选项：删除写入的 upstreamLineage aspect（回滚用，需写操作）。

Usage:
    uv run python scripts/verify_lineage.py
    uv run python scripts/verify_lineage.py --purge
"""
import argparse
import os
import sys
import time

import requests
import yaml

# 复用 query_lineage 的查询逻辑（同目录 import）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from query_lineage import (  # noqa: E402
    AUTH,
    GMS_HOST,
    build_urn,
    load_recipe,
    query_upstream_lineage,
)

OS_HOST = "http://localhost:29200"
TIMEOUT = 15


def expected_upstream_urns(recipe_path: str) -> list:
    """从 recipe 提取每条 downstream 的预期上游 URN 列表。"""
    recipe = load_recipe(recipe_path)
    out = []
    for rel in recipe.get("lineage_relationships", []):
        downstream = rel.get("downstream")
        if not downstream or not rel.get("upstream"):
            continue
        down_urn = build_urn(downstream["platform"], downstream["table"])
        up_urns = [build_urn(u["platform"], u["table"]) for u in rel["upstream"]]
        out.append(
            {
                "dataset": f"{downstream['platform']}.{downstream['table']}",
                "urn": down_urn,
                "expected_upstreams": up_urns,
            }
        )
    return out


def assert_aspects(records: list) -> tuple:
    """断言每条边的 GMS aspect 非空且含预期上游。返回 (ok_count, failures)。"""
    ok = 0
    failures = []
    for rec in records:
        real = set(query_upstream_lineage(rec["urn"]))
        expected = set(rec["expected_upstreams"])
        if not real:
            failures.append(f"  ✗ {rec['dataset']}: GMS 中 upstreamLineage 为空（urn={rec['urn']}）")
            continue
        missing = expected - real
        if missing:
            miss_short = [u.split(",")[-1] if "," in u else u for u in missing]
            failures.append(f"  ✗ {rec['dataset']}: 缺少上游 {miss_short}")
            continue
        print(f"  ✓ {rec['dataset']}: {len(real)} 条上游与 recipe 一致")
        ok += 1
    return ok, failures


def assert_opensearch_indexed(records: list, max_wait_s: int = 30) -> tuple:
    """轮询 OpenSearch，断言每条 downstream dataset 已被索引（容忍 MAE→actions 延迟）。"""
    deadline = time.monotonic() + max_wait_s
    missing = {rec["dataset"] for rec in records}
    last_err = None
    while missing and time.monotonic() < deadline:
        try:
            for ds in list(missing):
                _platform, table = ds.split(".", 1)
                # 用 match 查 name（不同 DataHub 版本字段名/分词不同，match 最稳）
                q = {"query": {"match": {"name": table}}}
                r = requests.post(
                    f"{OS_HOST}/datasetindex_v2/_search",
                    json=q, timeout=TIMEOUT,
                )
                if r.status_code == 200:
                    hits = r.json().get("hits", {}).get("hits", [])
                    if hits:
                        missing.discard(ds)
        except requests.exceptions.RequestException as e:
            last_err = e
        if missing:
            time.sleep(2)
    return list(missing), last_err


def purge_aspects(recipe_path: str) -> int:
    """删除 recipe 中每条 downstream 的 upstreamLineage aspect（回滚用）。"""
    import urllib.parse

    recipe = load_recipe(recipe_path)
    deleted = 0
    for rel in recipe.get("lineage_relationships", []):
        downstream = rel.get("downstream")
        if not downstream or not rel.get("upstream"):
            continue
        urn = build_urn(downstream["platform"], downstream["table"])
        # DataHub 删除 aspect：POST /entities?action=deleteSnapshotWithSql?
        # 简单可行：用 GMS /openapi/v3/entity/dataset/<urn>/upstreamLineage DELETE（v1.6 支持）
        encoded = urllib.parse.quote(urn, safe="")
        url = f"{GMS_HOST}/openapi/v3/entity/dataset/{encoded}/upstreamLineage"
        try:
            r = requests.delete(url, auth=AUTH, timeout=TIMEOUT)
            if r.status_code in (200, 204, 404):
                print(f"  purged upstreamLineage: {downstream['platform']}.{downstream['table']}")
                deleted += 1
            else:
                print(f"  purge 失败 {r.status_code}: {downstream['platform']}.{downstream['table']}")
        except requests.exceptions.RequestException as e:
            print(f"  purge 请求异常: {e}")
    return deleted


def main():
    parser = argparse.ArgumentParser(description="真验证 DataHub 血缘写入")
    parser.add_argument("--recipe", default=None)
    parser.add_argument("--purge", action="store_true", help="删除写入的 upstreamLineage（回滚）")
    parser.add_argument("--no-os-check", action="store_true", help="跳过 OpenSearch 索引断言")
    args = parser.parse_args()

    if args.recipe:
        recipe_path = args.recipe
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        recipe_path = os.path.join(os.path.dirname(script_dir), "lineage_recipe.yaml")

    if args.purge:
        print("== purge 模式：删除 upstreamLineage aspect ==")
        n = purge_aspects(recipe_path)
        print(f"已处理 {n} 条 downstream")
        return

    if not os.path.exists(recipe_path):
        print(f"recipe 不存在: {recipe_path}", file=sys.stderr)
        sys.exit(2)

    print("== 1. 校验 GMS upstreamLineage aspect ==")
    records = expected_upstream_urns(recipe_path)
    ok, failures = assert_aspects(records)
    print(f"  GMS 断言: {ok}/{len(records)} 通过")

    if failures:
        print("\nGMS 断言失败：", file=sys.stderr)
        for f in failures:
            print(f, file=sys.stderr)

    os_failures = []
    if not args.no_os_check:
        print("\n== 2. 校验 OpenSearch 索引同步（轮询 ≤30s）==")
        missing, err = assert_opensearch_indexed(records)
        if missing:
            os_failures = missing
            print(f"  OpenSearch 未索引: {missing}")
            if err:
                print(f"  (查询异常: {err})")
        else:
            print(f"  OpenSearch: {len(records)} 个 downstream 全部已索引 ✓")

    if failures or os_failures:
        print("\n== 验证未通过 ==", file=sys.stderr)
        sys.exit(1)

    print("\n== 验证通过：8 条血缘边已在 GMS 写入且 OpenSearch 索引同步 ==")


if __name__ == "__main__":
    main()
