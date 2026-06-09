import requests

ES_URL = 'http://localhost:29200'
GMS_URL = 'http://localhost:28080'
AUTH = ('datahub', 'datahub')

datasets = [
    ('lims', 'samples'),
    ('sap_erp', 'vbak'),
    ('sap_erp', 'kna1'),
    ('pi_system', 'tags'),
    ('oa', 'doc_flow'),
]

print('ES browsePath (by name match):')
for platform, table in datasets:
    q = {'query': {'match': {'name': table}}, 'size': 5, '_source': ['urn','name','platform','browsePath','description']}
    r = requests.post(ES_URL + '/datasetindex_v2/_search', json=q, timeout=10)
    d = r.json()
    for h in d.get('hits',{}).get('hits',[]):
        s = h['_source']
        if platform in s.get('urn',''):
            bp = [e.get('id') for e in s.get('browsePath',[])]
            desc = s.get('description','')[:60]
            print(f'  {platform}/{table}: browsePath={bp}')
            print(f'    desc={desc}')
            break
    else:
        print(f'  {platform}/{table}: NOT FOUND')
