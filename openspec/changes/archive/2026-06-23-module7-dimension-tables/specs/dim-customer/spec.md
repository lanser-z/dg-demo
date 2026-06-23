## ADDED Requirements

### Requirement: dim_customer table SHALL be built from SAP KNA1 source data
The system SHALL extract customer_code (kunnr), customer_name, region, and credit_level from `data/lakehouse/dwd/sap_erp/dwd_kna1/`, deduplicate by kunnr, and write to Delta Lake at `data/lakehouse/dwd/_dimensions/dim_customer/`.

#### Scenario: Extract and deduplicate customer data from SAP KNA1
- **WHEN** `scripts/build_dimension_tables.py` runs with `--dimension customer`
- **THEN** it reads `data/lakehouse/dwd/sap_erp/dwd_kna1/`, extracts unique (kunnr, customer_name, region, credit_level) tuples, and writes to `data/lakehouse/dwd/_dimensions/dim_customer/` as Delta Lake

### Requirement: dim_customer fields SHALL include standard customer attributes
The dim_customer table SHALL contain the following fields: kunnr, customer_name, region, credit_level.

#### Scenario: All customer attributes are present in output
- **WHEN** dim_customer is successfully written
- **THEN** each row SHALL contain non-null kunnr, customer_name, region, and credit_level values
