## Purpose

Define the dimension table for mines used in cross-system sales-production analysis.

## ADDED Requirements

### Requirement: dim_mine table SHALL be built from PI/LIMS source data
The system SHALL aggregate mine_code and mine_name from PI (dwd_tags) and LIMS (dwd_samples) source parquet files, deduplicate by mine_code, and write to Delta Lake at `data/lakehouse/dwd/_dimensions/dim_mine/`.

Note: SAP KNA1 is a customer table and does not contain mine data. Mine data is sourced from PI (`data/lakehouse/dwd/pi_system/dwd_tags/` — `mine` field) and LIMS (`data/lakehouse/dwd/lims/dwd_samples/` — `MINE_CODE`, `MINE_NAME` fields).

#### Scenario: Extract and deduplicate mine data from PI tags
- **WHEN** `scripts/build_dimension_tables.py` runs with `--dimension mine`
- **THEN** it reads `data/lakehouse/dwd/pi_system/dwd_tags/`, extracts unique (mine_code, mine_name) pairs, and writes to `data/lakehouse/dwd/_dimensions/dim_mine/` as Delta Lake

#### Scenario: Extract and deduplicate mine data from LIMS samples
- **WHEN** `scripts/build_dimension_tables.py` runs with `--dimension mine`
- **THEN** it reads `data/lakehouse/dwd/lims/dwd_samples/`, extracts unique (mine_code, mine_name) pairs, and merges into `data/lakehouse/dwd/_dimensions/dim_mine/` as Delta Lake

### Requirement: dim_mine fields SHALL include mine metadata for cross-system mapping
The dim_mine table SHALL contain the following fields: mine_code, mine_name, mine_type, sap_mine_field, pi_mine_field, lims_mine_field.

#### Scenario: All three source system field names are recorded
- **WHEN** dim_mine is successfully written
- **THEN** each row SHALL contain non-null sap_mine_field, pi_mine_field, and lims_mine_field values identifying which source field name corresponds to this mine_code
