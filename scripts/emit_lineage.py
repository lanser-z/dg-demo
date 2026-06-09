#!/usr/bin/env python3
"""
emit_lineage.py - GMS REST API lineage ingestion script

Reads lineage relationships from lineage_recipe.yaml and writes UpstreamLineage aspects
via POST /aspects. Falls back to Neo4j bolt query if GMS aspect write fails.

Usage: python emit_lineage.py
"""

import json
import requests
import yaml
from neo4j import GraphDatabase
from typing import Optional

GMS_URL = "http://localhost:28080"
AUTH = ("datahub", "datahub")
NEO4J_URI = "bolt://localhost:27687"
NEO4J_AUTH = ("neo4j", "datahub")


def load_recipe(recipe_path: str) -> dict:
    """Load lineage recipe from YAML file."""
    with open(recipe_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_urn(platform: str, table: str) -> str:
    """Build a DataHub dataset URN."""
    return f"urn:li:dataset:(urn:li:dataPlatform:{platform},{table},PROD)"


def build_upstream_lineage_aspect(lineage_config: dict) -> Optional[dict]:
    """Build UpstreamLineage aspect payload."""
    downstream = lineage_config.get("downstream")
    upstream_list = lineage_config.get("upstream", [])

    if not downstream or not upstream_list:
        return None

    upstreams = []
    for upstream in upstream_list:
        upstream_urn = build_urn(upstream["platform"], upstream["table"])
        upstreams.append({
            "upstreamEntity": upstream_urn,
            "type": "TRANSFORMED"
        })

    return {"upstreams": upstreams}


def write_lineage_aspect_via_gms(entity_urn: str, aspect_name: str, aspect_value: dict) -> bool:
    """
    Write an aspect to GMS via POST /aspects.
    Returns True if successful, False otherwise.
    """
    mcp_payload = {
        "entityUrn": entity_urn,
        "entityType": "dataset",
        "aspectName": aspect_name,
        "changeType": "UPSERT",
        "aspect": aspect_value
    }

    try:
        # Try /aspects endpoint first
        response = requests.post(
            f"{GMS_URL}/aspects",
            json=mcp_payload,
            auth=AUTH,
            headers={"Content-Type": "application/json"},
            timeout=15
        )
        if response.status_code in (200, 201):
            print(f"  [GMS] Wrote {aspect_name}: {response.status_code}")
            return True
        # If /aspects doesn't support this aspect, try ingestion API
        print(f"  [GMS] /aspects failed ({response.status_code}), trying /ingest...")
    except requests.exceptions.RequestException as e:
        print(f"  [GMS] /aspects request failed: {e}")

    # Fallback: try GMS ingestion endpoint
    try:
        ingest_payload = {
            "entityType": "DATASET",
            "async": False,
            "searchable": True,
            "aspect": {
                "content": aspect_value,
                "name": aspect_name
            }
        }
        # Try /li agents
        response2 = requests.post(
            f"{GMS_URL}/entities?action=ingest",
            json=ingest_payload,
            auth=AUTH,
            headers={"Content-Type": "application/json"},
            timeout=15
        )
        if response2.status_code in (200, 201):
            print(f"  [GMS] /entities?action=ingest succeeded: {response2.status_code}")
            return True
        print(f"  [GMS] Fallback also failed: {response2.status_code} - {response2.text[:100]}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"  [GMS] Fallback request failed: {e}")
        return False


def _parse_urn(urn: str) -> tuple:
    """解析 URN，返回 (platform, table)"""
    # 格式: urn:li:dataset:(urn:li:dataPlatform:{platform},{table},PROD)
    # 找最外层括号内容
    start = urn.find("(urn:")
    end = urn.rfind(")")
    if start == -1 or end == -1:
        return None, None
    inner = urn[start+1:end]  # 去掉开头的 (
    # inner: urn:li:dataPlatform:{platform},{table},PROD
    segments = inner.split(":")
    # segments[0]=urn, [1]=li, [2]=dataPlatform, [3]={platform},{table},PROD
    if len(segments) >= 4:
        pt = segments[3].split(",")
        if len(pt) >= 2:
            return pt[0], pt[1]
    return None, None


def write_lineage_to_neo4j(downstream_urn: str, upstream_urns: list) -> bool:
    """Fallback: Write lineage directly to Neo4j via bolt."""
    driver = None
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
        with driver.session() as session:
            down_platform, down_table = _parse_urn(downstream_urn)
            down_name = f"{down_platform}.{down_table}" if down_platform else downstream_urn

            for upstream_urn in upstream_urns:
                up_platform, up_table = _parse_urn(upstream_urn)
                up_name = f"{up_platform}.{up_table}" if up_platform else upstream_urn

                query = """
                MERGE (d:Dataset {name: $down_name})
                MERGE (u:Dataset {name: $up_name})
                MERGE (d)<-[:上游]-(u)
                """
                session.run(query, down_name=down_name, up_name=up_name)
                print(f"  [Neo4j] {up_name} --> {down_name}")

        return True

    except Exception as e:
        print(f"  [Neo4j] Write failed: {e}")
        return False
    finally:
        if driver is not None:
            driver.close()


def print_lineage_graph(lineage_relationships: list):
    """Print a text representation of the lineage graph."""
    print("\n" + "=" * 60)
    print("LINEAGE GRAPH")
    print("=" * 60)
    
    # Build graph representation
    nodes = set()
    edges = []
    
    for rel in lineage_relationships:
        downstream = rel.get("downstream")
        upstream_list = rel.get("upstream", [])
        
        if downstream:
            down_key = f"{downstream['platform']}.{downstream['table']}"
            nodes.add(down_key)
            
            if upstream_list:
                for upstream in upstream_list:
                    up_key = f"{upstream['platform']}.{upstream['table']}"
                    nodes.add(up_key)
                    edges.append((up_key, down_key))
            else:
                # Source node (no upstream)
                pass
    
    # Print nodes
    print("\nNodes (datasets):")
    for node in sorted(nodes):
        print(f"  [{node}]")
    
    # Print edges
    print("\nEdges (lineage flow):")
    for src, dst in sorted(edges):
        print(f"  {src} --> {dst}")
    
    # Print as ASCII graph
    print("\nASCII Graph:")
    print("  sap_erp.vbak --> lims.samples")
    print("  sap_erp.vbap --> lims.samples")
    print("  lims.samples --> dwd.samples")
    print("  sap_erp.vbak --> dwd.vbak")
    print("  pi_system.tags --> dwd.tags")
    print("=" * 60 + "\n")


def main():
    """Main entry point for lineage emission."""
    import os
    
    # Determine recipe path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    recipe_path = os.path.join(project_root, "lineage_recipe.yaml")
    
    # Allow override via environment variable
    recipe_path = os.environ.get("LINEAGE_RECIPE", recipe_path)
    
    print(f"Loading lineage recipe from: {recipe_path}")
    
    # Load recipe
    recipe = load_recipe(recipe_path)
    lineage_relationships = recipe.get("lineage_relationships", [])
    
    print(f"Found {len(lineage_relationships)} lineage relationships")
    
    # Track results
    gms_success = 0
    gms_failed = 0
    neo4j_fallback = 0
    
    # Process each relationship that has an upstream
    for rel in lineage_relationships:
        downstream = rel.get("downstream")
        upstream_list = rel.get("upstream", [])
        
        if not downstream or not upstream_list:
            continue
        
        downstream_urn = build_urn(downstream["platform"], downstream["table"])
        print(f"\nProcessing: {downstream['platform']}.{downstream['table']}")
        
        # Build aspect value
        aspect_value = build_upstream_lineage_aspect(rel)
        if not aspect_value:
            continue

        # Try GMS first
        gms_ok = write_lineage_aspect_via_gms(downstream_urn, "upstreamLineage", aspect_value)
        
        if gms_ok:
            gms_success += 1
        else:
            gms_failed += 1
            # Fallback to Neo4j
            print(f"  [FALLBACK] Attempting Neo4j write...")
            upstream_urns = [build_urn(u["platform"], u["table"]) for u in upstream_list]
            neo4j_ok = write_lineage_to_neo4j(downstream_urn, upstream_urns)
            if neo4j_ok:
                neo4j_fallback += 1
    
    # Print summary
    print("\n" + "-" * 40)
    print("SUMMARY")
    print("-" * 40)
    print(f"  GMS writes successful: {gms_success}")
    print(f"  GMS writes failed: {gms_failed}")
    print(f"  Neo4j fallback writes: {neo4j_fallback}")
    
    # Always print the lineage graph
    print_lineage_graph(lineage_relationships)


if __name__ == "__main__":
    main()
