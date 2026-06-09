"""
修复 datasetindex_v2 中缺失的 datasetKey/datasetProperties/datasetUrn。
直接写 MySQL metadata_aspect_v2 表来补全缺失的 aspects。
"""
import json
import urllib.parse
import requests
import time

GMS_URL = "http://localhost:28080"
ES_URL  = "http://localhost:29200"
INDEX   = "datasetindex_v2"

# ── 从 ES 读取已存在的文档 ──────────────────────────────────────────
r = requests.get(f"{ES_URL}/{INDEX}/_search", params={"size": 50, "_source": "platform,name,urn"}, timeout=10)
hits = r.json()["hits"]["hits"]
print(f"ES 文档数: {len(hits)}")
for h in hits:
    src = h["_source"]
    print(f"  {src['platform']:10s}  urn={src['urn']}")

# ── 写入 MySQL metadata_aspect_v2 ──────────────────────────────────
# DataHub v1.6.0: MySQL 直连 (容器网络)
import mysql.connector

conn = mysql.connector.connect(
    host="localhost",
    port=23306,
    user="datahub",
    password="datahub",
    database="datahub",
    charset="utf8mb4",
)
cur = conn.cursor()

def aspect_exists(urn, aspect_type):
    cur.execute(
        "SELECT COUNT(*) FROM metadata_aspect_v2 WHERE urn=%s AND aspect=%s",
        (urn, aspect_type),
    )
    return cur.fetchone()[0] > 0

def upsert_aspect(urn, aspect_type, value_json, actor="datahub"):
    """写入 metadata_aspect_v2，replace if exists"""
    # MetadataAspectV2 schema:
    # urn, aspect, version, metadata (longtext), createdon, createdby, createdfor, systemmetadata
    import datetime
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    metadata_str = json.dumps(value_json)
    cur.execute("""
        INSERT INTO metadata_aspect_v2
          (urn, aspect, version, metadata, createdon, createdby, createdfor)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
          metadata=VALUES(metadata),
          version=VALUES(version)
    """, (urn, aspect_type, 1, metadata_str, now, actor, actor))
    conn.commit()

def build_dataset_key(platform, name):
    """DatasetKey aspect: platform urn + dataset name + origin"""
    return {
        "platform": f"urn:li:dataPlatform:{platform}",
        "name": name.split(",")[0] if "," in name else name,
        "origin": None,
    }

def build_dataset_properties(name, description):
    """DatasetProperties aspect"""
    return {
        "name": name,
        "description": description,
        "customProperties": [],
    }

# ── 补全每个 dataset ─────────────────────────────────────────────────
for h in hits:
    src = h["_source"]
    platform = src["platform"]
    name     = src["name"]        # e.g. "kna1,PROD"
    urn      = src["urn"]
    desc     = src.get("description", "")

    table_name = name.split(",")[0]  # strip ",PROD" suffix

    # 1. datasetKey
    key_aspect = build_dataset_key(platform, table_name)
    upsert_aspect(urn, "datasetKey", key_aspect)
    print(f"  ✓ datasetKey: {urn}")

    # 2. datasetProperties
    props_aspect = build_dataset_properties(table_name, desc)
    upsert_aspect(urn, "datasetProperties", props_aspect)
    print(f"  ✓ datasetProperties: {urn}")

    # 3. dataPlatformInstance
    plat_inst = {"platform": f"urn:li:dataPlatform:{platform}"}
    upsert_aspect(urn, "dataPlatformInstance", plat_inst)
    print(f"  ✓ dataPlatformInstance: {urn}")

print("\n所有 aspects 已写入 MySQL")

# ── 触发 ES 同步 ───────────────────────────────────────────────────
time.sleep(2)
requests.post(
    f"{GMS_URL}/operations?action=restoreIndices",
    headers={"Content-Type": "application/json"},
    timeout=30,
)
print("已触发 restoreIndices 同步到 OpenSearch")

# ── 验证 ────────────────────────────────────────────────────────────
time.sleep(3)
r2 = requests.get(
    f"{GMS_URL}/openapi/datasets/urn:li:dataset:(urn:li:dataPlatform:sap_erp,kna1,PROD)",
    timeout=10,
)
print(f"\n验证 GET dataset: {r2.status_code}")
if r2.status_code == 200:
    d = r2.json()
    print(f"  name: {d.get('name')}")
    print(f"  platform: {d.get('platform')}")

cur.close()
conn.close()
print("\n完成")
