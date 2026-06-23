## ADDED Requirements

### Requirement: module7.ipynb SHALL demonstrate the pain point of heterogeneous mine/customer/material codes
The notebook SHALL present a scenario where analysts need to JOIN SAP KNA1, PI tags, and LIMS samples for cross-system sales-production analysis without dimension tables, showing verbose WHERE clauses for code mapping.

#### Scenario: Notebook opens with pain point story
- **WHEN** a user opens `notebook/module7.ipynb`
- **THEN** the notebook SHALL display a markdown cell describing the problem: heterogeneous field names (e.g., `mine` vs `mine_code` vs `WERKS`) across SAP/PI/LIMS requiring complex WHERE mapping

### Requirement: module7.ipynb SHALL demonstrate dimension table construction
The notebook SHALL include executable cells that call `scripts/build_dimension_tables.py` to build the 3 dimension tables and verify output row counts.

#### Scenario: Dimension table build is demonstrated in notebook
- **WHEN** user runs the build cells in sequence
- **THEN** dim_mine, dim_customer, and dim_material are written to `data/lakehouse/dwd/_dimensions/` with correct row counts displayed

### Requirement: module7.ipynb SHALL demonstrate improved JOIN with dimension tables
The notebook SHALL show a before/after SQL comparison: the verbose JOIN without dimension tables vs. the clean JOIN using dim_mine, dim_customer, dim_material.

#### Scenario: Before/after SQL comparison is shown
- **WHEN** user scrolls to the JOIN comparison section
- **THEN** the notebook SHALL display two SQL cells: the pain-point version with multiple WHERE field mappings, and the dimension-table version using simple natural JOINs on dim_* keys

### Requirement: module7.ipynb SHALL include an honest disclaimer
The notebook SHALL include a markdown cell explicitly stating this is a demo/educational notebook and does not represent production data治理 pipeline.

#### Scenario: Disclaimer is visible in notebook
- **WHEN** user reaches the end of `notebook/module7.ipynb`
- **THEN** there SHALL be a clearly labeled "免责声明" or "Honest Disclaimer" cell stating the notebook is for demonstration purposes only
