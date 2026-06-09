"""
将所有 datasetKey.version=0 记录更新为完整数据。
使用 SQL JSON_OBJECT 确保 origin 始终是字符串。
"""
import mysql.connector

conn = mysql.connector.connect(
    host="localhost", port=23306,
    user="datahub", password="datahub",
    database="datahub", charset="utf8mb4",
)
cur = conn.cursor()

def extract_parts(urn):
    inner = urn.split('(')[1].rstrip(')')
    parts = inner.split(',')
    platform_urn = parts[0]
    platform = platform_urn.split(':')[-1]
    name = parts[1]
    origin = parts[2] if len(parts) > 2 else 'PROD'
    return platform, name, origin

# 查找所有 version=0 且 metadata='{}' 的 datasetKey
cur.execute("""
    SELECT urn FROM metadata_aspect_v2
    WHERE aspect='datasetKey' AND version=0 AND metadata='{}'
    AND urn LIKE 'urn:li:dataset:%'
""")
empty_keys = [row[0] for row in cur.fetchall()]
print(f"Found {len(empty_keys)} datasets with empty version=0")

updated = 0
for urn in empty_keys:
    platform, name, origin = extract_parts(urn)
    # 使用 SQL JSON_OBJECT 保证 origin 是字符串
    cur.execute(f"""
        UPDATE metadata_aspect_v2
        SET metadata=JSON_OBJECT('platform', %s, 'name', %s, 'origin', %s),
            createdby='urn:li:corpuser:datahub',
            createdfor='urn:li:corpuser:datahub'
        WHERE urn=%s AND aspect='datasetKey' AND version=0
    """, (f'urn:li:dataPlatform:{platform}', name, origin, urn))
    conn.commit()
    print(f"  {platform}/{name}: origin={origin}")
    updated += 1

# 也检查 metadata 中 origin 为 null 的情况
cur.execute("""
    SELECT urn, metadata FROM metadata_aspect_v2
    WHERE aspect='datasetKey' AND version=0 AND urn LIKE 'urn:li:dataset:%'
    AND JSON_EXTRACT(metadata, '$.origin') IS NULL
""")
null_origin = [row[0] for row in cur.fetchall()]
print(f"\nFound {len(null_origin)} datasets with null origin")

for urn in null_origin:
    platform, name, origin = extract_parts(urn)
    cur.execute(f"""
        UPDATE metadata_aspect_v2
        SET metadata=JSON_OBJECT('platform', %s, 'name', %s, 'origin', %s),
            createdby='urn:li:corpuser:datahub',
            createdfor='urn:li:corpuser:datahub'
        WHERE urn=%s AND aspect='datasetKey' AND version=0
    """, (f'urn:li:dataPlatform:{platform}', name, origin, urn))
    conn.commit()
    print(f"  Fixed null origin: {platform}/{name}")
    updated += 1

print(f"\nTotal updated: {updated}")
cur.close()
conn.close()
