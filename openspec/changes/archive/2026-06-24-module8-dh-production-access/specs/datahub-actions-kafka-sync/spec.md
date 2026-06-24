# datahub-actions-kafka-sync

## ADDED Requirements

### Requirement: Kafka consumer shall consume MetadataChangeLog_Versioned_v1 topic

datahub-actions pipeline SHALL consume events from Kafka topic `MetadataChangeLog_Versioned_v1`（非废弃的 `MetadataChangeLog_v4`）。

#### Scenario: Kafka source connects to MetadataChangeLog_Versioned_v1
- **WHEN** datahub-actions service starts with Kafka source configured
- **THEN** it SHALL connect to Kafka bootstrap server and subscribe to topic `MetadataChangeLog_Versioned_v1`

### Requirement: Pipeline shall filter for ENTITY_CHANGE and METADATA_CHANGE_LOG event types

Pipeline filter SHALL drop events that are not `ENTITY_CHANGE` or `METADATA_CHANGE_LOG` types。

#### Scenario: Filter drops non-entity-change events
- **WHEN** event with type `PLATFORM_EVENT` arrives
- **THEN** filter SHALL drop the event and not pass it to action

### Requirement: metadata_change_sync action shall emit to target GMS

Pipeline action of type `metadata_change_sync` SHALL emit `MetadataChangeProposal` objects to configured target GMS server via REST API。

#### Scenario: MCL event synced to GMS
- **WHEN** a `MetadataChangeLog` event passes the filter
- **THEN** action SHALL emit a `MetadataChangeProposal` to `http://target-gms:8080`

### Requirement: Actions shall support urn_regex filtering

`metadata_change_sync` action SHALL support `urn_regex` config to filter entities by URN pattern。

#### Scenario: URN regex filters dataset entities
- **WHEN** `urn_regex` is set to `urn:li:dataset:(prod|lakehouse).*`
- **THEN** only matching dataset URNs SHALL be synced to target GMS

### Requirement: Actions shall support aspects_to_exclude

`metadata_change_sync` action SHALL support `aspects_to_exclude` list to exclude sensitive aspects from sync。

#### Scenario: Exclude access token aspects
- **WHEN** `aspects_to_exclude` includes `dataHubAccessTokenInfo`
- **THEN** events containing only this aspect SHALL be dropped
