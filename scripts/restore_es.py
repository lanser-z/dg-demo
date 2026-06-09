import requests, json, time

GMS_URL = 'http://localhost:28080'
AUTH = ('datahub', 'datahub')
ES_URL = 'http://localhost:29200'

# restoreIndices for all dataPlatform URNs
pl = {'urnLike': 'urn:dataPlatform:%', 'aspect': 'browsePathsV2', 'batchSize': 100}
r = requests.post(GMS_URL + '/operations?action=restoreIndices', json=pl, auth=AUTH, timeout=60)
print('restoreIndices status:', r.status_code, r.text[:150])

specific_urns = [
    'urn:li:dataset:(urn:li:dataPlatform:lims,samples,PROD)',
    'urn:li:dataset:(urn:li:dataPlatform:sap_erp,vbak,PROD)',
    'urn:li:dataset:(urn:li:dataPlatform:sap_erp,kna1,PROD)',
    'urn:li:dataset:(urn:li:dataPlatform:sap_erp,vbap,PROD)',
    'urn:li:dataset:(urn:li:dataPlatform:pi_system,tags,PROD)',
    'urn:li:dataset:(urn:li:dataPlatform:oa,doc_flow,PROD)',
]
for urn in specific_urns:
    requests.post(GMS_URL + '/operations?action=restoreIndices', json={'urn': urn}, auth=AUTH, timeout=30)
    time.sleep(0.5)

time.sleep(3)

datasets = [
    ('lims', 'samples'),
    ('sap_erp', 'vbak'),
    ('sap_erp', 'kna1'),
    ('pi_system', 'tags'),
    ('oa', 'doc_flow'),
]
print('\nES browsePath 验证:')
for platform, table in datasets:
    urn = 'urn:li:dataset:(urn:li:dataPlatform:' + platform + ',' + table + ',PROD)'
    q = {'query': {'wildcard': {'urn.keyword': urn}}, '_source': ['urn','name','browsePath','description']}
    r3 = requests.post(ES_URL + '/datasetindex_v2/_search', json=q, timeout=10)
    d3 = r3.json()
    hits = d3.get('hits',{}).get('hits',[])
    if hits:
        s = hits[0]['_source']
        bp = [e.get('id') for e in s.get('browsePath', [])]
        desc = s.get('description', '')[:60]
        print(f'  {platform}/{table}: browsePath={bp} | {desc}')
    else:
        print(f'  {platform}/{table}: NOT FOUND in ES')
