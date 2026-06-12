## ADDED Requirements

### Requirement: dg_education.ge_scan 模块必须提供 run_ge_scan 函数

`src/dg_education/ge_scan.py` MUST 提供 `run_ge_scan(systems: list[str] | None = None, output_json: str | None = None) -> dict` 函数。

函数 MUST 内部用 `importlib.util` 把 `scripts/run_great_expectations.py` 加载到同进程，调用其 `run_check()` 并用 `_to_native()` 规范化 numpy/pandas 类型后，把结果组装为 Python dict 返回。同进程 import 优于 subprocess 方案：避免 numpy bool_/int64/float64 序列化问题，省掉 2-3s 子进程启动开销，且与 CLI 共享同一份 RULES 字典。

#### Scenario: 不指定 systems 时扫描全部 4 系统
- **WHEN** 调用 `run_ge_scan()` 不传参
- **THEN** MUST 扫描全部 4 系统，返回的 dict MUST 包含 `sap_erp` / `pi_system` / `lims` / `oa` 4 个 key

#### Scenario: 指定单系统时只扫描该系统
- **WHEN** 调用 `run_ge_scan(systems=['sap_erp'])`
- **THEN** MUST 仅扫描 `sap_erp`，返回的 dict MUST 仅包含 `sap_erp` 1 个 key

#### Scenario: 指定 output_json 时生成报告文件
- **WHEN** 调用 `run_ge_scan(output_json='/tmp/report.json')`
- **THEN** MUST 在 `/tmp/report.json` 写入合法 JSON 报告，且文件 MUST 存在

#### Scenario: 单表规则失败时降级返回错误条目
- **WHEN** 某个表的 `run_check()` 抛异常
- **THEN** MUST 在该系统的 results 列表里追加 1 个 `error` 字段非空的条目（不中断整体扫描），其他表正常返回

### Requirement: dg_education.quality 必须提供 4 个根因分析函数

`src/dg_education/quality.py` MUST 提供以下 4 个根因分析函数：

| 函数 | 输入 | 输出（dict 必含字段） |
|------|------|---------------------|
| `analyze_vbap_invalid_links(vbap: pd.DataFrame) -> dict` | VBAP 行项目 | `total_invalid`, `invalid_pct`, `by_mat_prefix`, `sample_vbeln` |
| `analyze_pi_missing_tags(pi_df: pd.DataFrame) -> dict` | PI tags | `total_missing`, `missing_pct`, `by_tag`, `by_hour` |
| `analyze_pi_anomalies(pi_df: pd.DataFrame) -> dict` | PI tags | `total_anomalies`, `anomaly_pct`, `median_wagas`, `threshold`, `by_tag` |
| `analyze_lims_ad_outliers(lims_df: pd.DataFrame) -> dict` | LIMS samples | `total_outliers`, `outlier_pct`, `by_sample_type` |

#### Scenario: analyze_vbap_invalid_links 必须识别 VBELN='0000000000'
- **WHEN** 传入含 VBELN='0000000000' 的 VBAP DataFrame
- **THEN** `total_invalid` MUST 等于该值出现次数，`invalid_pct` MUST ≈ 该次数/总行数×100

#### Scenario: analyze_pi_missing_tags 必须识别 status=-1
- **WHEN** 传入含 status=-1 的 PI tags DataFrame
- **THEN** `total_missing` MUST 等于 status=-1 出现次数

#### Scenario: analyze_pi_anomalies 必须计算 3x 中位数阈值
- **WHEN** 传入 PI tags DataFrame
- **THEN** `threshold` MUST = WAGAS 子集 value 列的 3 × 中位数

#### Scenario: analyze_lims_ad_outliers 必须按煤种判断
- **WHEN** 传入 LIMS samples DataFrame
- **THEN** `by_sample_type` MUST 是按煤种（原煤/精煤/中煤/矸石/洗煤）分组的 outlier 计数

### Requirement: dg_education.visualization 必须提供 3 个根因/告警 plot 函数

`src/dg_education/visualization.py` MUST 提供以下 3 个 plot 函数：

| 函数 | 输入 | 输出 |
|------|------|------|
| `plot_root_cause_distribution(by_xxx: pd.Series, title: str) -> Figure` | 分组 Series + 标题 | matplotlib Figure（水平柱状图） |
| `plot_alert_heatmap(matrix: pd.DataFrame) -> Figure` | 系统×告警 DataFrame | matplotlib Figure（热力图） |
| `plot_system_alert_summary(report: dict) -> Figure` | GE 扫描报告 | matplotlib Figure（双柱状图：总规则数 + 失败规则数） |

#### Scenario: plot_root_cause_distribution 必须支持中文标题
- **WHEN** 传入 `title='SAP VBAP 孤儿行订单类型分布'`
- **THEN** 渲染的图表 MUST 正确显示中文字符（依赖 `_ensure_chinese_font()`）

#### Scenario: plot_alert_heatmap 配色必须红黄绿渐变
- **WHEN** 传入 `matrix` DataFrame
- **THEN** 图表 MUST 使用红黄绿渐变（值大=红，值小=绿），色条 MUST 可见

#### Scenario: plot_system_alert_summary 必须按系统聚合失败规则
- **WHEN** 传入 GE 扫描报告 dict
- **THEN** 图表 MUST 展示 4 个系统的「总规则数 + 失败规则数」双柱状对比

### Requirement: dg_education.__init__ 必须导出新 API

`src/dg_education/__init__.py` MUST 导出以下 8 个新 API：

从 `ge_scan`：
- `run_ge_scan`

从 `quality`（4 个新增根因函数）：
- `analyze_vbap_invalid_links`
- `analyze_pi_missing_tags`
- `analyze_pi_anomalies`
- `analyze_lims_ad_outliers`

从 `visualization`（3 个新增 plot 函数）：
- `plot_root_cause_distribution`
- `plot_alert_heatmap`
- `plot_system_alert_summary`

#### Scenario: 一行 import 即可获得全部新 API
- **WHEN** 执行 `from dg_education import run_ge_scan, analyze_vbap_invalid_links, plot_root_cause_distribution`
- **THEN** MUST 0 错误，3 个符号 MUST 全部可用
