import json, urllib.parse, requests

ES_URL = 'http://localhost:29200'
INDEX = 'datasetindex_v2'
ASSET = {
    'platform': 'sap_erp',
    'table': 'kna1',
    'urn': 'urn:li:dataset:(urn:li:dataPlatform:sap_erp,kna1,PROD)',
    'name': 'kna1,PROD',
    'description': 'test',
    'browsePath': [{'id': 'sap_erp'}, {'id': 'kna1'}],
    'browsePathV2': ['sap_erp', 'kna1'],
    'tags': [],
}

doc_id = urllib.parse.quote(ASSET['urn'], safe='')
bulk_lines = [
    json.dumps({'update': {'_id': doc_id, '_index': INDEX}}),
    json.dumps({'doc': ASSET, 'doc_as_upsert': True}),
]
body = '\n'.join(bulk_lines) + '\n'
resp = requests.post(f'{ES_URL}/_bulk', headers={'Content-Type': 'application/x-ndjson'}, data=body.encode(), timeout=30)
print('HTTP:', resp.status_code)
r = resp.json()
print('Response:', json.dumps(r, indent=2, ensure_ascii=False)[:3000])
