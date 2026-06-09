import requests, json

ES_URL = 'http://localhost:29200'
GMS_URL = 'http://localhost:28080'
AUTH = ('datahub', 'datahub')

datasets = [
    ('lims', 'samples', ['lims', 'samples']),
    ('sap_erp', 'kna1', ['sap_erp', 'kna1']),
    ('sap_erp', 'vbak', ['sap_erp', 'vbak']),
    ('sap_erp', 'vbap', ['sap_erp', 'vbap']),
    ('pi_system', 'tags', ['pi_system', 'tags']),
    ('oa', 'doc_flow', ['oa', 'doc_flow']),
]

print('=== Direct ES browsePath update ===')
for platform, table, browse_path in datasets:
    urn = 'urn:li:dataset:(urn:li:dataPlatform:' + platform + ',' + table + ',PROD)'
    q = {'query': {'term': {'urn.keyword': urn}}, '_source': ['_id']}
    r = requests.post(ES_URL + '/datasetindex_v2/_search', json=q, timeout=10)
    d = r.json()
    hits = d.get('hits',{}).get('hits',[])
    if hits:
        doc_id = hits[0]['_id']
        update = {'doc': {'browsePath': [{'id': p} for p in browse_path]}}
        r2 = requests.post(ES_URL + '/datasetindex_v2/_update/' + doc_id, json=update, timeout=10)
        print(f'  {platform}/{table}: status={r2.status_code}')
        if r2.status_code not in (200, 201):
            print(f'    {r2.text[:100]}')
    else:
        print(f'  {platform}/{table}: NOT FOUND')

print()
print('=== Verification ===')
for platform, table, browse_path in datasets:
    urn = 'urn:li:dataset:(urn:li:dataPlatform:' + platform + ',' + table + ',PROD)'
    q = {'query': {'term': {'urn.keyword': urn}}, '_source': ['browsePath']}
    r = requests.post(ES_URL + '/datasetindex_v2/_search', json=q, timeout=10)
    d = r.json()
    hits = d.get('hits',{}).get('hits',[])
    if hits:
        bp = [e.get('id') for e in hits[0]['_source'].get('browsePath',[])]
        status = 'OK' if bp == browse_path else f'MISMATCH (got {bp})'
        print(f'  {platform}/{table}: {status}')
    else:
        print(f'  {platform}/{table}: NOT FOUND')
