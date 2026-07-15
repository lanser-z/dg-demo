"""
LineageEmitter — 自动血缘采集上下文管理器（Phase 2 module 9 / Background §6.9）

ETL 入口插入 `with LineageEmitter(job, sql=...)` 即可在跑完时自动向 GMS 的
OpenLineage 端点（POST /openapi/openlineage/api/v1/lineage）emit START/COMPLETE
事件，GMS 内部 OpenLineageToDataHub 转换器自动写 `upstreamLineage` aspect。

设计选型见 openspec/changes/module9-auto-lineage/design.md：
- 决策 1：openlineage-python 官方 SDK
- 决策 2：sqlglot 解析 FROM/JOIN
- 决策 3：上下文管理器（非装饰器 / 回调）
- 决策 4：HTTP 直发到 GMS REST 端点
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Iterable

from openlineage.client.client import OpenLineageClient
from openlineage.client.run import Dataset, Job, Run, RunEvent, RunState
from openlineage.client.transport import HttpConfig, HttpTransport
from sqlglot import exp, parse
from sqlglot.errors import ParseError

GMS_URL = os.environ.get("DATAHUB_GMS_URL", "http://localhost:28080")
OL_ENDPOINT = "/openapi/openlineage/api/v1/lineage"
PRODUCER = "https://github.com/OpenLineage/OpenLineage/etl/python"
DEFAULT_NAMESPACE = "datahub"


def _build_client(gms_url: str = GMS_URL) -> OpenLineageClient:
    """HttpConfig 的 url 与 endpoint 是分离参数（design.md 决策 4）。"""
    cfg = HttpConfig(
        url=gms_url,
        endpoint=OL_ENDPOINT,
        retry={
            "total": 5,
            "backoff_factor": 0.3,
            "status_forcelist": [500, 502, 503, 504],
        },
    )
    return OpenLineageClient(transport=HttpTransport(cfg))


def _urn_to_namespace_table(urn: str) -> tuple[str, str]:
    """urn:li:dataset:(urn:li:dataPlatform:sap_erp,dwd_vbak,PROD) -> (sap_erp, dwd_vbak)

    DataHub 约定：dataset URN 最后一段是 env（PROD/DEV），用 rsplit(',', 1) 切分。
    """
    inner = urn.split("(", 1)[1].rsplit(")", 1)[0]
    parts = inner.split(":")
    db_part = parts[-1] if len(parts) >= 2 else parts[0]
    if "," in db_part:
        ns, table_with_env = db_part.split(",", 1)
        table = table_with_env.rsplit(",", 1)[0]
        return ns, table
    return DEFAULT_NAMESPACE, db_part


class LineageEmitter:
    """ETL 入口的 OpenLineage 自动血缘上下文管理器。

    用法：
        with LineageEmitter("dwd_vbak", sql=SQL_DWD_VBAK,
                             output_urn="urn:li:dataset:(...)") as e:
            ... ETL logic ...
            e.emit_output("urn:li:dataset:(...)", df)
    """

    def __init__(
        self,
        job_name: str,
        sql: str | None = None,
        output_urn: str | None = None,
        gms_url: str = GMS_URL,
        namespace: str = "dg-demo",
    ) -> None:
        self.job_name = job_name
        self.sql = sql
        self.output_urn = output_urn
        self.namespace = namespace
        self._client = _build_client(gms_url)
        self._run_id = str(uuid.uuid4())
        self._inputs_urns: list[str] = []
        self._outputs_urns: list[str] = []
        self._success = True
        self._emitted_start = False
        if sql:
            self._inputs_urns = self.from_sql(sql)

    def from_sql(self, sql: str) -> list[str]:
        """用 sqlglot 从 SQL 推导 inputs（urn:li:dataset 列表）；ParseError 降级返回 []。"""
        try:
            tree = parse(sql, dialect="duckdb")
        except ParseError:
            return []
        if not tree:
            return []
        cte_names = {cte.alias_or_name for cte in tree[0].find_all(exp.CTE)}
        inputs: list[str] = []
        for tab in tree[0].find_all(exp.Table):
            name = exp.table_name(tab)
            if not name or name in cte_names:
                continue
            ns, table = name.split(".", 1) if "." in name else (DEFAULT_NAMESPACE, name)
            inputs.append(
                f"urn:li:dataset:(urn:li:dataPlatform:{ns},{table},PROD)"
            )
        return list(dict.fromkeys(inputs))

    def emit_output(self, dataset_urn: str, df: Any = None) -> None:
        """注册一个 output dataset；df 参数为兼容签名，可空。"""
        self._outputs_urns.append(dataset_urn)
        if not self.output_urn:
            self.output_urn = dataset_urn

    def _to_dataset(self, urn: str) -> Dataset:
        ns, name = _urn_to_namespace_table(urn)
        return Dataset(namespace=ns, name=name)

    def _emit(self, state: RunState) -> None:
        run = Run(runId=self._run_id)
        job = Job(namespace=self.namespace, name=self.job_name)
        event = RunEvent(
            eventType=state,
            eventTime=datetime.now(timezone.utc).isoformat(),
            run=run,
            job=job,
            producer=PRODUCER,
            inputs=[self._to_dataset(u) for u in self._inputs_urns],
            outputs=[self._to_dataset(u) for u in self._outputs_urns],
        )
        self._client.emit(event)

    def __enter__(self) -> "LineageEmitter":
        try:
            self._emit(RunState.START)
            self._emitted_start = True
        except Exception:
            pass
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc_type is not None:
            self._success = False
        try:
            self._emit(
                RunState.COMPLETE if self._success else RunState.FAIL
            )
        except Exception:
            pass
