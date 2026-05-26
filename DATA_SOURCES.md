# DATA_SOURCES.md: Government Data Sources & Schemas

A comprehensive breakdown of all Singapore government data sources, external API interfaces, and local SQLite data seeding schemas utilized by the platform.

---

## 1. Government Data Sources Used

The platform extracts and aggregates quantitative policy indices across three major categories:

1. **MOM Statistics (Ministry of Manpower):** Labor market indicators, net headcount changes, unemployment rates, and median salary structures by sector (2020-2024).
2. **DOS SingStat (Department of Statistics Singapore):** Demographic resident population records, median ages, demographic dependency ratios, and Consumer Price Index (CPI) inflation rates.
3. **Data.gov.sg (Mock APIs):** Simulates fetching Southeast Asia average inflation rates and WEF Digital Economy benchmarks from external JSON API endpoints.

---

## 2. SQLite Database Schema Definitions

Factual data is persisted in a local SQLite file (`policy_data.db`). The tables represent structured data sheets:

### A. MOM Labor Market Statistics (`mom_employment`)
Provides sector-specific wage and headcount trends. 
* **Database Columns:**
  - `id` (INTEGER, Primary Key): Autoincrement index.
  - `year` (INTEGER, Index): Calendar year (2020-2024).
  - `sector` (VARCHAR, Index): Industry sector (Technology, Financial Services, Healthcare, Tourism & Hospitality).
  - `employment_change` (INTEGER): Net change in headcount (can be negative, representing sector contraction).
  - `unemployment_rate` (FLOAT): Percentage sector unemployment rate (e.g. `2.4`).
  - `median_salary` (FLOAT): Median monthly basic salary in Singapore Dollars (e.g. `8200`).

### B. Department of Statistics Population demographics (`singstat_population`)
Provides resident demographic records.
* **Database Columns:**
  - `id` (INTEGER, Primary Key): Autoincrement index.
  - `year` (INTEGER, Index): Calendar year (2020-2024).
  - `resident_population` (INTEGER): Total headcount of Singapore residents (citizens + permanent residents).
  - `median_age` (FLOAT): Median age of resident population.
  - `dependency_ratio` (FLOAT): Ratio of elderly dependents (65+) per 100 working residents.

### C. SingStat Consumer Price Index (`singstat_cpi`)
Provides monthly Consumer Price Index numbers to track inflation trends across goods categories.
* **Database Columns:**
  - `id` (INTEGER, Primary Key): Autoincrement index.
  - `year` (INTEGER, Index): Calendar year (2020-2024).
  - `month` (VARCHAR): Standard 3-letter month string (Jan, Feb, Mar...).
  - `cpi_index` (FLOAT): Normalized Consumer Price Index.
  - `category` (VARCHAR, Index): CPI Category (All Items, Food, Housing, Transport).

---

## 3. Mock External Web API Definitions

To demonstrate multi-format extraction, the platform hosts simulated HTTP API endpoints.

### A. GET `/api/v1/inflation/regional?year={year}`
* **Description:** Returns Southeast Asia regional average inflation rates to compare against Singapore's local CPI index.
* **Response Payload (200 OK JSON):**
  ```json
  {
    "year": 2022,
    "metric": "Southeast Asia Average Inflation (%)",
    "value": 4.8,
    "data_source": "ASEAN Statistical Portal (Mock API)",
    "api_status": "200 OK"
  }
  ```

### B. GET `/api/v1/talent/tech-index?year={year}`
* **Description:** Retrieves global talent indices from the World Economic Forum Digital Economy records.
* **Response Payload (200 OK JSON):**
  ```json
  {
    "year": 2024,
    "metric": "Global Tech Talent Demand Index (Base 100=2020)",
    "value": 125.8,
    "data_source": "World Economic Forum Digital Economy Index (Mock API)",
    "api_status": "200 OK"
  }
  ```

---

## 4. Seeding & Quality Control Mechanisms

* **Database Seeding (`seed_data.py`):** On backend container startup, SQLAlchemy parses database definitions, constructs the SQLite schema, and automatically seeds realistic mock statistics for 2020-2024 if the database is empty.
* **Data Cleaning & Handlers (`extraction.py`):** The Data Extraction Agent checks for column formats, normalizes naming formats, strips invalid character sequences (like dollar symbols `$`), and converts string values to programmatic python floats before passing the clean JSON package to the Analytics Agent.
