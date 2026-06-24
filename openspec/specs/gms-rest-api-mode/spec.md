# gms-rest-api-mode

## ADDED Requirements

### Requirement: GMS REST API shall support entity read via GET /openapi/entities/v1/latest

GMS SHALL expose OpenAPI endpoint `GET /openapi/entities/v1/latest` to read dataset entities and their aspects.

#### Scenario: GET dataset entity with browsePaths
- **WHEN** client sends GET to `http://localhost:28080/openapi/entities/v1/latest?urns=<urn>`
- **THEN** GMS SHALL return entity with all current aspects and return 200 OK

### Requirement: GMS REST API shall support dataset browsePaths aspect

`browsePaths` aspect SHALL be readable via REST API for dataset entities.

#### Scenario: BrowsePaths readable via OpenAPI GET
- **WHEN** GET request is made for a dataset with browsePaths aspect
- **THEN** dataset browsePaths SHALL be included in the response aspects

### Requirement: GMS server shall be reachable at configured host:port

REST API client SHALL be able to reach GMS at configured `server` URL via health endpoint.

#### Scenario: GMS health check succeeds
- **WHEN** client sends GET to `http://localhost:28080/health`
- **THEN** GMS SHALL return 200 OK

### Requirement: REST API shall support optional authentication token

GMS SHALL support optional `token` config for authenticated requests when Metadata Service Auth is enabled。

#### Scenario: Auth token included in request
- **WHEN** request includes `Authorization: Bearer <token>` header
- **THEN** GMS SHALL validate token and process request if valid

---

### ADDED Notes

**关于写入**：GMS 不支持直接 POST `/entities` 写入。正确写入方式：
1. `datahub ingest -c delta-lake-ingestion.yaml`（Delta-Lake source → datahub-rest sink）
2. `datahub actions -c datahub-actions.yml`（Kafka 事件流驱动）
3. GraphQL `patchEntity` mutation（开发调试）

**关于 health endpoint**：GMS health endpoint 为 `/health`（非 `/ping`）。
