#!/usr/bin/env python3
"""
Browse API Proxy — 解决 DataHub GMS v1.x 的 match_none bug
监听 23319 端口，将 Browse 请求用 ES direct query 实现
用法: python3 browse_proxy.py
然后将前端配置指向 localhost:23319，或直接用 curl 测试
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
from http.client import HTTPConnection
import json, re, urllib.parse

GMS = "http://localhost:28080"
ES = "http://localhost:29200"
IDX = "datasetindex_v2"

class ProxyHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[proxy] {fmt % args}")

    def do_POST(self):
        if self.path == "/api/graphql":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            
            try:
                data = json.loads(body)
            except:
                self.send_error(400, "Invalid JSON")
                return
            
            query = data.get("query", "")
            
            # 检查是否是 Browse + DATASET 查询
            if "browse(" in query and "type: DATASET" in query:
                total, entities, groups = self.es_browse(query)
                result = {"data": {"browse": {"total": total, "entities": entities, "groups": groups}}}
                response = json.dumps(result)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", len(response))
                self.end_headers()
                self.wfile.write(response.encode())
            else:
                # 非 Browse 请求，转发给 GMS
                self.proxy_to_gms(body)
        else:
            self.send_error(404)

    def es_browse(self, query):
        """用 ES 实现 Browse 逻辑"""
        
        # 解析 path
        path_match = re.search(r"path:\s*\[(.*?)\]", query, re.DOTALL)
        if path_match:
            path_str = path_match.group(1).strip()
            if path_str:
                path = [p.strip().strip('"').strip("'") for p in path_str.split(",")]
            else:
                path = []
        else:
            path = []

        # 解析 start/count
        start_match = re.search(r"start:\s*(\d+)", query)
        count_match = re.search(r"count:\s*(\d+)", query)
        start = int(start_match.group(1)) if start_match else 0
        count = int(count_match.group(1)) if count_match else 10

        # 构造 ES query
        if not path:
            es_query = {"match_all": {}}
        else:
            path_str = "/".join(path)
            es_query = {"prefix": {"browsePaths": f"/{path_str}"}}

        # ES 请求
        es_body = {
            "size": count,
            "from": start,
            "query": es_query,
            "_source": {"includes": ["urn", "browsePaths", "platform", "name"]},
            "sort": [{"urn": "asc"}]
        }

        try:
            import http.client
            conn = http.client.HTTPConnection("localhost", 29200, timeout=10)
            conn.request("POST", f"/{IDX}/_search", body=json.dumps(es_body),
                        headers={"Content-Type": "application/json"})
            resp = conn.getresponse()
            result = json.loads(resp.read())
            conn.close()
        except Exception as e:
            return 0, [], []

        hits = result.get("hits", {})
        total = hits.get("total", {}).get("value", 0)
        entities = []
        groups = {}

        for h in hits.get("hits", []):
            s = h.get("_source", {})
            urn = s.get("urn", "")
            platform = s.get("platform", "")
            name = s.get("name", "")
            browsePaths = s.get("browsePaths", [])

            entities.append({
                "urn": urn,
                "platform": {"name": platform},
                "name": name,
                "browsePaths": browsePaths,
                "__typename": "Dataset"
            })

            # 分组统计
            if platform:
                groups[platform] = groups.get(platform, 0) + 1

        group_list = [{"name": k, "count": v} for k, v in groups.items()]
        return total, entities, group_list

    def proxy_to_gms(self, body):
        """转发请求到 GMS"""
        try:
            import http.client
            conn = http.client.HTTPConnection("localhost", 28080, timeout=30)
            headers = {"Content-Type": "application/json"}
            conn.request("POST", "/api/graphql", body=body, headers=headers)
            resp = conn.getresponse()
            response_body = resp.read()
            conn.close()
            self.send_response(resp.status)
            for h, v in resp.getheaders():
                if h.lower() not in ("transfer-encoding", "connection"):
                    self.send_header(h, v)
            self.end_headers()
            self.wfile.write(response_body)
        except Exception as e:
            self.send_error(502, str(e))

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 23319), ProxyHandler)
    print("Browse API Proxy 启动: http://localhost:23319")
    print("将 /api/graphql 的 Browse 请求用 ES direct query 处理")
    print("其他请求转发到 GMS")
    server.serve_forever()
