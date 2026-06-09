#!/bin/bash
# Bulk update ES datasetindex_v2 with browsePath + name for all 6 datasets
# Uses docker exec to query MySQL from GMS container, pipes to ES bulk API

ES_URL="http://localhost:23308"
INDEX="datasetindex_v2"

# All 6 datasets: urn, name, browsePath
declare -A DATASETS
DATASETS["urn:li:dataset:(urn:li:dataPlatform:lims,samples,PROD)"]="samples,PROD|/lims/samples|lims"
DATASETS["urn:li:dataset:(urn:li:dataPlatform:sap_erp,kna1,PROD)"]="kna1,PROD|/sap_erp/kna1|sap_erp"
DATASETS["urn:li:dataset:(urn:li:dataPlatform:sap_erp,vbak,PROD)"]="vbak,PROD|/sap_erp/vbak|sap_erp"
DATASETS["urn:li:dataset:(urn:li:dataPlatform:sap_erp,vbap,PROD)"]="vbap,PROD|/sap_erp/vbap|sap_erp"
DATASETS["urn:li:dataset:(urn:li:dataPlatform:pi_system,tags,PROD)"]="tags,PROD|/pi_system/tags|pi_system"
DATASETS["urn:li:dataset:(urn:li:dataPlatform:oa,doc_flow,PROD)"]="doc_flow,PROD|/oa/doc_flow|oa"

bulk_body=""
count=0

for urn in "${!DATASETS[@]}"; do
 IFS='|' read -r name browse_path platform <<< "${DATASETS[$urn]}"
  doc_id=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$urn', safe=''))")

  # Build update action + doc
  action=$(cat <<EOF
{"update":{"_id":"$doc_id","_index":"$INDEX","retry_on_conflict":3}}
EOF
)

  doc=$(cat <<EOF
{"doc":{"urn":"$urn","name":"$name","browsePath":["$browse_path"],"platform":"$platform"},"doc_as_upsert":true}
EOF
)

  bulk_body="${bulk_body}${action}
${doc}
"
  count=$((count + 1))
done

echo "Updating $count datasets..."
echo -e "$bulk_body" | curl -s -X POST "$ES_URL/_bulk" \
  -H "Content-Type: application/x-ndjson" \
  --data-binary @- | python3 -c "
import json,sys
r=json.load(sys.stdin)
print('Status:', r.get('took'), 'ms')
print('Errors:', r.get('errors'))
for item in r.get('items',[]):
    a = list(item.keys())[0]
    i = item[a]
    result = i.get('result','?')
    did = i.get('_id','?')[:80]
    if i.get('error'):
        print(f'  FAIL {did}: {i[\"error\"].get(\"type\")}: {i[\"error\"].get(\"reason\",\"\")[:80]}')
    else:
        print(f'  OK   {did}: {result}')
"
