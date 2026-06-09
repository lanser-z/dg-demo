import requests, time

GMS_URL = 'http://localhost:28080'
AUTH = ('datahub', 'datahub')

datasets = [
    ('lims', 'samples'),
    ('sap_erp', 'kna1'),
    ('sap_erp', 'vbak'),
    ('sap_erp', 'vbap'),
    ('pi_system', 'tags'),
    ('oa', 'doc_flow'),
]

print('=== 逐 URN restoreIndices (aspect=browsePathsV2) ===')
for platform, table in datasets:
    urn = 'urn:li:dataset:(urn:li:dataPlatform:' + platform + ',' + table + ',PROD)'
    pl = {'urn': urn, 'aspect': 'browsePathsV2', 'batchSize': 100}
    r = requests.post(
        GMS_URL + '/operations?action=restoreIndices',
        json=pl,
        auth=AUTH,
        timeout=60
    )
    status = 'OK' if r.status_code == 200 else f'FAIL({r.status_code})'
    print(f'  {platform}/{table}: {status}')
    time.sleep(1)

# Also restore datasetProperties
print('\n=== 逐 URN restoreIndices (aspect=datasetProperties) ===')
for platform, table in datasets:
    urn = 'urn:li:dataset:(urn:li:dataPlatform:' + platform + ',' + table + ',PROD)'
    pl = {'urn': urn, 'aspect': 'datasetProperties', 'batchSize': 100}
    r = requests.post(
        GMS_URL + '/operations?action=restoreIndices',
        json=pl,
        auth=AUTH,
        timeout=60
    )
    status = 'OK' if r.status_code == 200 else f'FAIL({r.status_code})'
    print(f'  {platform}/{table}: {status}')
    time.sleep(1)

print('\n等待 5 秒让 ES 索引完成...')
time.sleep(5)

# Verify in ES
ES_URL = 'http://localhost:29200'
print('\n=== ES browsePath 验证 ===')
for platform, table in datasets:
    urn = 'urn:li:dataset:(urn:li:dataPlatform:' + platform + ',' + table + ',PROD)'
    q = {'query': {'wildcard': {'urn.keyword': urn}}, '_source': ['urn','name','browsePath','description']}
    r = requests.post(ES_URL + '/datasetindex_v2/_search', json=q, timeout=10)
    d = r.json()
    hits = d.get('hits',{}).get('hits',[])
    if hits:
        s = hits[0]['_source']
        bp = [e.get('id') for e in s.get('browsePath',[])]
        desc = s.get('description','')[:50]
        print(f'  {platform}/{table}: browsePath={bp} | {desc}')
    else:
        print(f'  {platform}/{table}: NOT FOUND')
