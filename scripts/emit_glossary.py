"""
emit_glossary.py — 把字段业务词典（data/glossary_terms.yaml）写入 DataHub
                  的 glossaryTerms aspect。
                  用于 NL2SQL 智能问数的术语消解（列中文别名 + 业务术语映射）。
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

import yaml
from datahub.emitter.mce_builder import make_dataset_urn, make_term_urn
from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.emitter.rest_emitter import DatahubRestEmitter
from datahub.metadata.schema_classes import (
    AuditStampClass,
    GlossaryTermAssociationClass,
    GlossaryTermsClass,
)

logging.basicConfig(level=logging.WARN)

# ── 配置（与 emit_browsepaths.py / lineage_recipe.yaml 一致） ─────────────
GMS_URL = "http://localhost:28080"
TOKEN = ""
GLOSSARY_FILE = Path("data/glossary_terms.yaml")

# URN 命名空间（避免与 DataHub 官方/其他 demo 冲突）
TERM_NAMESPACE = "a-company.coal"

# 业务术语 → ASCII term_id 映射（用于构造稳定的 glossaryTerm URN）
# 优先查表；未命中时回退到 hash 后缀（仍可读，URL 安全）
PINYIN_MAP: dict[str, str] = {
    # ── 通用业务术语 ──
    "销售订单号": "sales-order-no",
    "销售单": "sales-order-no",
    "销售凭证": "sales-doc",
    "销售凭证号": "sales-doc-no",
    "订单号": "order-no",
    "订单日期": "order-date",
    "订单类型": "order-type",
    "凭证类型": "doc-type",
    "订单金额": "order-amount",
    "销售金额": "sales-amount",
    "销售额": "sales-amount",
    "订单数量": "order-qty",
    "销售数量": "sales-qty",
    "销售日期": "sales-date",
    "日期": "date",
    "创建日期": "create-date",
    "创建时间": "create-time",
    "录入时间": "input-time",
    "录入人": "input-user",
    "业务员": "salesman",
    "货币": "currency",
    "结算币种": "settlement-currency",
    "客户号": "customer-no",
    "客户编号": "customer-no",
    "客户编码": "customer-code",
    "客户名称": "customer-name",
    "客户名": "customer-name",
    "公司名称": "company-name",
    "公司简称": "company-short-name",
    "客户简称": "customer-short-name",
    "城市": "city",
    "注册地": "registered-address",
    "统一社会信用代码": "unified-social-credit-code",
    "税号": "tax-id",
    "物料号": "material-no",
    "物料编码": "material-no",
    "物料名称": "material-name",
    "物料描述": "material-desc",
    "物料组": "material-group",
    "物料类型": "material-type",
    "基本单位": "base-unit",
    "计量单位": "unit",
    "毛重": "gross-weight",
    "净重": "net-weight",
    "销售单位": "sales-unit",
    "单位": "unit",
    "批次": "batch",
    "批次号": "batch-no",
    "批号": "batch-no",
    "工厂": "plant",
    "工厂代码": "plant-code",
    "发货工厂": "shipping-plant",
    "库存地点": "storage-location",
    "库位": "storage-location",
    "销售组织": "sales-org",
    "销售分公司": "sales-subsidiary",
    "销售大区": "sales-region",
    "区域代码": "region-code",
    "销售渠道": "sales-channel",
    "分销渠道": "distribution-channel",
    "产品组": "product-group",
    "物料组": "material-group",
    "客户单号": "customer-ref-no",
    "采购单号": "purchase-order-no",
    # SAP LIKP/LIPS
    "交货单号": "delivery-no",
    "送货单号": "delivery-no",
    "交货日期": "delivery-date",
    "发货日期": "shipping-date",
    "计划交货日": "planned-delivery-date",
    "到货日期": "arrival-date",
    "计划到达日": "planned-arrival-date",
    "交货类型": "delivery-type",
    "发货类型": "shipping-type",
    "办事处": "sales-office",
    "发货点": "shipping-point",
    "行号": "line-no",
    "行项目": "line-item",
    "交货行号": "delivery-line-no",
    "交货数量": "delivery-qty",
    "实际数量": "actual-qty",
    # PI / SCADA
    "传感器编号": "sensor-no",
    "测点编号": "sensor-no",
    "测点": "sensor",
    "标签": "tag",
    "采集时间": "collect-time",
    "时间戳": "timestamp",
    "测量值": "measurement",
    "读数": "reading",
    "数值": "value",
    "状态码": "status-code",
    "质量码": "quality-code",
    "矿井编号": "mine-no",
    "矿别": "mine",
    "工作面": "working-face",
    "采面": "working-face",
    "设备编号": "equipment-no",
    "设备编码": "equipment-no",
    "设备类型": "equipment-type",
    "设备分类": "equipment-type",
    "设备状态": "equipment-status",
    "运行状态": "running-status",
    "矿井": "mine",
    "所属矿井": "mine-affiliation",
    "状态时间": "status-time",
    "运行小时": "running-hours",
    "累计运行时长": "total-running-hours",
    # LIMS 煤质
    "样品号": "sample-no",
    "化验编号": "test-no",
    "煤的种类": "coal-type",
    "煤炭类型": "coal-type",
    "煤种": "coal-type",
    "原煤": "raw-coal",
    "精煤": "clean-coal",
    "中煤": "middling-coal",
    "矸石": "gangue",
    "洗煤": "washed-coal",
    "灰分": "ash-content",
    "灰分含量": "ash-content",
    "AD灰分": "ash-content",
    "灰分均值": "avg-ash",
    "AD均值": "avg-ash",
    "平均灰分": "avg-ash",
    "挥发分": "volatile-content",
    "VD挥发分": "volatile-content",
    "发热量": "calorific-value",
    "热值": "calorific-value",
    "QGR": "calorific-value",
    "热值均值": "avg-calorific",
    "QGR均值": "avg-calorific",
    "平均发热量": "avg-calorific",
    "化验室": "lab",
    "检测单位": "testing-unit",
    "报告状态": "report-status",
    "审核状态": "audit-status",
    "矿井名称": "mine-name",
    "矿名": "mine-name",
    "月份": "month",
    "统计月份": "stat-month",
    "样品数": "sample-count",
    "化验次数": "test-count",
    # OA
    "单号": "doc-no",
    "流程号": "flow-no",
    "流程类型": "flow-type",
    "审批类型": "approval-type",
    "流程状态": "flow-status",
    "审批状态": "approval-status",
    "金额": "amount",
    "申请金额": "apply-amount",
    "发起部门": "initiator-dept",
    "申请部门": "apply-dept",
    "合同号": "contract-no",
    "合同编码": "contract-code",
    "合同类型": "contract-type",
    "合同分类": "contract-category",
    "签订日期": "sign-date",
    "签约日": "sign-date",
    "乙方": "party-b",
    "对方单位": "counterparty",
    "合同金额": "contract-amount",
    "总价": "total-price",
    "合同状态": "contract-status",
    "履约状态": "fulfillment-status",
    "会议号": "meeting-no",
    "会议编码": "meeting-code",
    "会议主题": "meeting-topic",
    "议题": "topic",
    "会议日期": "meeting-date",
    "召开日": "convene-date",
    "主持人": "host",
    "召集人": "convenor",
    "参会人": "attendee",
    "与会人员": "attendee",
    "会议纪要": "meeting-minutes",
    "纪要内容": "minutes-content",
    # DWA 业务术语
    "订单笔数": "order-count",
    "订单数": "order-count",
    "销售单数": "order-count",
    "客户数": "customer-count",
    "下单客户数": "ordering-customer-count",
    "销售总额": "total-sales",
    "销售总金额": "total-sales",
    "客单价": "avg-order-amount",
    "平均订单金额": "avg-order-amount",
    "ARPU": "arpu",
    "采样数": "sample-count",
    "记录数": "record-count",
    "缺失数": "missing-count",
    "掉线条数": "offline-count",
    "超标数": "over-threshold-count",
    "告警次数": "alarm-count",
    "日产量": "daily-production",
    "产量": "production",
    "产煤量": "coal-production",
    "总采样条数": "total-records",
}


def term_to_id(term_cn: str) -> str:
    """Chinese 业务术语 → ASCII term_id (pinyin 优先，回退到 sanitized 中文)."""
    if term_cn in PINYIN_MAP:
        return PINYIN_MAP[term_cn]
    # 回退：去除标点 + 截断（避免 URN 过长）
    safe = term_cn.strip().replace("/", "-").replace(" ", "-")
    if len(safe) > 32:
        safe = safe[:32]
    return f"term-{safe}"


def make_term_urn_for_cn(term_cn: str) -> str:
    """生成稳定的 glossaryTerm URN：urn:li:glossaryTerm:a-company.coal.{id}"""
    return make_term_urn(f"{TERM_NAMESPACE}.{term_to_id(term_cn)}")


def main() -> int:
    if not GLOSSARY_FILE.exists():
        print(f"❌ 词典文件不存在: {GLOSSARY_FILE}")
        return 1

    with GLOSSARY_FILE.open() as f:
        cfg = yaml.safe_load(f)
    entries = cfg.get("glossary", [])
    if not entries:
        print("❌ YAML 中无 glossary 条目")
        return 1

    # ── 1. 统计 ──
    n_tables = len(entries)
    n_columns = sum(len(e.get("columns", [])) for e in entries)
    n_term_associations = sum(
        len(c.get("business_terms", []))
        for e in entries
        for c in e.get("columns", [])
    )
    print(f"=== 字段业务词典 → DataHub glossaryTerms ===")
    print(f"  GMS: {GMS_URL}")
    print(f"  词典: {GLOSSARY_FILE}")
    print(f"  表数: {n_tables}    列数: {n_columns}    业务术语关联: {n_term_associations}")
    print()

    # ── 2. 检查 GMS 健康 ──
    emitter = DatahubRestEmitter(gms_server=GMS_URL, token=TOKEN)
    try:
        emitter.test_connection()  # 成功时返回 None；失败抛 RestliConnectionError
        print(f"  GMS 连接 OK")
    except Exception as e:
        print(f"❌ GMS 不可达: {GMS_URL} — {type(e).__name__}: {e}")
        return 1

    # ── 3. 逐表写入 glossaryTerms aspect ──
    audit_ts = int(time.time() * 1000)
    audit_stamp = AuditStampClass(time=audit_ts, actor="urn:li:corpuser:datahub")

    results = {"tables_ok": 0, "tables_fail": 0, "rows": []}
    for entry in entries:
        platform = entry["platform"]
        table = entry["table"]
        table_cn = entry.get("table_cn", table)
        columns = entry.get("columns", [])

        dataset_urn = make_dataset_urn(platform=platform, name=table, env="PROD")

        # 聚合 (column, term) → GlossaryTermAssociation
        # context 字段记录「<table>.<column>」便于反查
        # 如果该字段有 value_mappings，追加「|values:k1=v1,k2=v2」
        associations: list[GlossaryTermAssociationClass] = []
        for col in columns:
            col_name = col.get("column", "")
            col_cn = col.get("cn_name", "")
            ctx_parts = [f"column:{col_name}", f"cn:{col_cn}", f"table:{table}"]
            value_mappings = col.get("value_mappings") or {}
            if value_mappings:
                safe_pairs = []
                for k, v in value_mappings.items():
                    combined = str(k) + str(v)
                    if any(c in combined for c in "=|,"):
                        continue  # 跳过含特殊字符的映射项，避免解析歧义
                    safe_pairs.append(f"{k}={v}")
                if safe_pairs:
                    ctx_parts.append(f"values:{','.join(safe_pairs)}")
            ctx = "|".join(ctx_parts)
            for term_cn in col.get("business_terms", []):
                assoc = GlossaryTermAssociationClass(
                    urn=make_term_urn_for_cn(term_cn),
                    context=ctx,
                )
                associations.append(assoc)

        n_assoc = len(associations)
        if n_assoc == 0:
            print(f"[{platform}/{table}] ⚠️  无 business_terms，跳过")
            results["rows"].append({
                "table": f"{platform}/{table}",
                "table_cn": table_cn,
                "associations": 0,
                "status": "skipped (no terms)",
            })
            continue

        aspect = GlossaryTermsClass(terms=associations, auditStamp=audit_stamp)
        mcp = MetadataChangeProposalWrapper(entityUrn=dataset_urn, aspect=aspect)

        try:
            emitter.emit_mcp(mcp)
            print(f"[{platform}/{table:<28}] {table_cn:<20} {n_assoc:>3} term assocs  ✓")
            results["tables_ok"] += 1
            results["rows"].append({
                "table": f"{platform}/{table}",
                "table_cn": table_cn,
                "associations": n_assoc,
                "status": "ok",
            })
        except Exception as e:
            print(f"[{platform}/{table:<28}] {table_cn:<20} {n_assoc:>3} term assocs  ✗ {type(e).__name__}: {e}")
            results["tables_fail"] += 1
            results["rows"].append({
                "table": f"{platform}/{table}",
                "table_cn": table_cn,
                "associations": n_assoc,
                "status": f"error: {type(e).__name__}: {str(e)[:80]}",
            })

        time.sleep(0.2)

    # ── 4. 汇总 ──
    total_assoc = sum(r["associations"] for r in results["rows"])
    print()
    print("=== 汇总 ===")
    print(f"  表数: {results['tables_ok']}/{n_tables} 写入 OK"
          + (f"  ({results['tables_fail']} 失败)" if results["tables_fail"] else ""))
    print(f"  业务术语关联（去重前）: {total_assoc}")
    if results["tables_ok"] == n_tables:
        print("\n✅ 全部完成")
        return 0
    else:
        print(f"\n⚠️  {results['tables_fail']} 张表失败")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
