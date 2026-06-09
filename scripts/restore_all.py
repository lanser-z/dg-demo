import requests, time

GMS_URL = 'http://localhost:28080'
AUTH = ('datahub', 'datahub')
ES_URL = 'http://localhost:29200'

datasets = [
    ('lims', 'samples'),
    ('sap_erp', 'kna1'),
    ('sap_erp', 'vbak'),
    ('sap_erp', 'vbap'),
    ('pi_system', 'tags'),
    ('oa', 'doc_flow'),
]

# Try restoreIndices WITHOUT specifying aspect - restore all aspects
print('=== restoreIndices (all aspects) per URN ===')
for platform, table in datasets:
    urn = 'urn:li:dataset:(urn:li:dataPlatform:' + platform + ',' + table + ',PROD)'
    # Don't specify aspect - restore everything
    pl = {'urn': urn}
    r = requests.post(
        GMS_URL + '/operations?action=restoreIndices',
        json=pl,
        auth=AUTH,
        timeout=120
    )
    print(f'  {platform}/{table}: {r.status_code} - {r.text[:80]}')
    time.sleep(2)

print('\n等待 10 秒...')
time.sleep(10)

print('\n=== ES browsePath 验证 ===')
for platform, table in datasets:
    q = {'query': {'match': {'name': table}}, 'size': 5, '_source': ['urn','name','browsePath']}
    r = requests.post(ES_URL + '/datasetindex_v2/_search', json=q, timeout=10)
    d = r.json()
    for h in d.get('hits',{}).get('hits',[]):
        s = h['_source']
        if platform in s.get('urn',''):
            bp = [e.get('id') for e in s.get('browsePath',[])]
            print(f'  {platform}/{table}: browsePath={bp}')
            break
    else:
        print(f'  {platform}/{table}: NOT FOUND')
