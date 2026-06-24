# module8-teaching-notebook

## ADDED Requirements

### Requirement: Notebook shall present Phase 1 pain points story

`notebook/module8.ipynb` SHALL include a narrative section explaining Phase 1 manual mode problems。

#### Scenario: Pain points section present
- **WHEN** notebook is opened
- **THEN** there SHALL be a markdown cell describing: manual script trigger, ES/GMS inconsistency, unscalable manual process

### Requirement: Notebook shall explain DataHub architecture (GMS/MySQL/OpenSearch/Kafka)

Notebook SHALL include architecture explanation with diagram showing relationship between GMS, MySQL, OpenSearch, and Kafka。

#### Scenario: Architecture section with diagram
- **WHEN** user reads architecture section
- **THEN** there SHALL be a PlantUML or ASCII diagram showing data flow: source → Kafka → datahub-actions → GMS MySQL → OpenSearch

### Requirement: Notebook shall demonstrate Phase 1 direct_es_bulk.py

Notebook SHALL include a code cell demonstrating `direct_es_bulk.py` dry-run output。

#### Scenario: Phase 1 demo code cell
- **WHEN** code cell runs `uv run python scripts/direct_es_bulk.py --dry-run`
- **THEN** it SHALL print what would be written to OpenSearch (no actual ES write)

### Requirement: Notebook shall show datahub-actions configuration

Notebook SHALL include configuration display for datahub-actions pipeline, including correct topic name `MetadataChangeLog_Versioned_v1`。

#### Scenario: Actions config section with correct topic
- **WHEN** user reads actions config section
- **THEN** config SHALL show `MetadataChangeLog_Versioned_v1`（not deprecated v4）

### Requirement: Notebook shall include REST API Python example

Notebook SHALL include a code cell with Python `requests` example showing how to POST dataset entity to GMS REST API。

#### Scenario: REST API example cell
- **WHEN** code cell runs with GMS available
- **THEN** it SHALL POST a dataset entity and print response status

### Requirement: Notebook shall honestly declare Demo environment limitations

Notebook SHALL include a clear disclaimer that Demo cannot simulate real Kafka cluster and Phase 2 is architecture demonstration only。

#### Scenario: Limitation disclaimer present
- **WHEN** user scrolls to limitation section
- **THEN** there SHALL be markdown stating "Demo 环境无真实 Kafka，Phase 2 为架构演示"
