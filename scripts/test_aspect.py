import requests, json

GMS_URL = 'http://localhost:28080'
AUTH=('datahub', 'datahub')
ES_URL = 'http://localhost:29200'

datasets = [
    {'platform': 'lims', 'table': 'samples'},
    {'platform': 'sap_erp', 'table': 'kna1'},
    {'platform': 'sap_erp', 'table': 'vbak'},
    {'platform': 'sap_erp', 'table': 'vbap'},
    {'platform': 'pi_system', 'table': 'tags'},
    {'platform': 'oa', 'table': 'doc_flow'},
]

for ds in datasets:
    platform = ds['platform']
    table = ds['table']
    urn = 'urn:li:dataset:(urn:li:dataPlatform:' + platform + ',' + table + ',PROD)'
    print(f'\n处理: {platform}/{table}')

    mcp_payload = {
        'entityUrn': urn,
        'entityType': 'dataset',
        'aspectName': 'browsePathsV2',
        'changeType': 'UPSERT',
        'aspect': {
            'path': [{'id': platform}]
        }
    }
    
    r = requests.post(
        f'{GMS_URL}/aspects',
        json=mcp_payload,
        auth=AUTH,
        headers={'Content-Type': 'application/json'},
        timeout=15
    )
    print(f'  /aspects: {r.status_code} - {r.text[:150]}')
