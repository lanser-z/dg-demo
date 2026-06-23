## ADDED Requirements

### Requirement: dim_material table SHALL be built from SAP VBAP source data
The system SHALL extract matnr (material_code), mat_desc (material_description inferred from VBAP), and mat_type from `data/lakehouse/dwd/sap_erp/dwd_vbap/`, deduplicate by matnr, and write to Delta Lake at `data/lakehouse/dwd/_dimensions/dim_material/`.

Note: SAP MARA (material master) is not available in this demo environment. Material code is sourced from VBAP (`MATNR` field). mat_desc is set to the matnr value (no description source without MARA). mat_type is inferred from the first 4 characters of matnr.

#### Scenario: Extract and deduplicate material data from SAP VBAP
- **WHEN** `scripts/build_dimension_tables.py` runs with `--dimension material`
- **THEN** it reads `data/lakehouse/dwd/sap_erp/dwd_vbap/`, extracts unique (matnr, mat_desc, mat_type) tuples, and writes to `data/lakehouse/dwd/_dimensions/dim_material/` as Delta Lake

### Requirement: dim_material fields SHALL include standard material attributes
The dim_material table SHALL contain the following fields: matnr, mat_desc, mat_type.

#### Scenario: All material attributes are present in output
- **WHEN** dim_material is successfully written
- **THEN** each row SHALL contain non-null matnr, mat_desc, and mat_type values
