# delta-lake-auto-discovery

## ADDED Requirements

### Requirement: Delta-Lake source shall ingest datasets from base_path

`delta-lake` source SHALL scan the configured `base_path` and ingest all datasets/tables/views as dataset entities。

#### Scenario: Source scans base_path and finds tables
- **WHEN** `base_path` is set to `/data/lakehouse/dwd`
- **THEN** source SHALL discover all Delta Lake tables under that path

### Requirement: Delta-Lake source shall use datahub-rest sink

Ingestion recipe SHALL use `datahub-rest` sink to push metadata to GMS via REST API（非 Kafka sink）。

#### Scenario: Ingestion pushes to GMS via REST
- **WHEN** delta-lake source discovers a new table
- **THEN** it SHALL emit metadata to `http://localhost:8080` via datahub-rest sink

### Requirement: Delta-Lake source shall support platform_instance

Source SHALL support `platform_instance` config to isolate assets from different environments。

#### Scenario: Platform instance separates prod and staging
- **WHEN** `platform_instance` is set to `prod-lakehouse`
- **THEN** all ingested datasets SHALL have URN prefix `urn:li:dataset:(urn:li:dataPlatform:delta-lake,prod-lakehouse/...)`

### Requirement: Delta-Lake source shall support env tag

Source SHALL support `env` config to tag all ingested assets with environment label。

#### Scenario: Env tag marks assets as PROD
- **WHEN** `env` is set to `"PROD"`
- **THEN** all datasets SHALL have `env: PROD` label
