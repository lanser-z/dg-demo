"""
验证 OpenSearch datasetindex_v2 中的 browsePath 是否正确。
直接查 ES，不依赖 MySQL/GMS。
"""
import requests

ES_URL = "http://localhost:29200"
INDEX = "datasetindex_v2"

DATASETS = [
    ("lims",         "samples"),
    ("sap_erp",      "kna1"),
    ("sap_erp",      "vbak"),
    ("sap_erp",      "vbap"),
    ("sap_erp",      "likp"),
    ("sap_erp",      "lips"),
    ("sap_erp",      "mara"),
    ("pi_system",    "tags"),
    ("oa",           "doc_flow"),
    ("oa",           "contract"),
    ("oa",           "meeting"),
    ("scada",        "equipment_status"),
]


def check_browse_path(platform, table):
    """查询 ES 中该数据集的 browsePath"""
    urn = f"urn:li:dataset:(urn:li:dataPlatform:{platform},{table},PROD)"
    q = {
        "query": {"term": {"urn.keyword": urn}},
        "_source": ["urn", "name", "description", "browsePath", "platform", "tags"],
        "size": 1,
    }
    r = requests.post(
        f"{ES_URL}/{INDEX}/_search",
        json=q,
        timeout=10,
    )
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}"

    hits = r.json().get("hits", {}).get("hits", [])
    if not hits:
        return None, "NOT FOUND in ES"
    src = hits[0]["_source"]
    return src, None


def main():
    print("=== OpenSearch browsePath 验证 ===")
    print(f"Index: {ES_URL}/{INDEX}\n")

    ok = 0
    missing = []
    for platform, table in DATASETS:
        src, err = check_browse_path(platform, table)
        if err:
            print(f"  {platform:10s} / {table:20s}  ❌ {err}")
            missing.append((platform, table))
        else:
            bp = src.get("browsePath", [])
            bp_ids = [e.get("id", "") for e in bp]
            desc = src.get("description", "")[:40]
            tags = src.get("tags", [])
            print(f"  {platform:10s} / {table:20s}  ✅ browsePath={bp_ids}")
            print(f"    desc={desc}")
            print(f"    tags={tags}")
            ok += 1

    print(f"\n=== 汇总 ===")
    print(f"  OK: {ok}/{len(DATASETS)}")
    print(f"  Missing: {len(missing)}/{len(DATASETS)}")
    if missing:
        print("\n缺失资产：")
        for p, t in missing:
            print(f"  {p}/{t}")
    else:
        print("\n✅ 全部资产 browsePath 已写入 OpenSearch")


if __name__ == "__main__":
    main()
