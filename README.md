# Congressional Record NLP Database & Dashboard

This project assembles and analyzes a comprehensive database of Congressional Records spanning from the **43rd to the 119th Congress**. It includes tools for data ingestion, a SQLite database for storage, and a Streamlit dashboard for interactive NLP analysis.

## Features

- **Extensive Database**: Contains speeches and metadata from the 43rd Congress to the .
- **Data Ingestion**: Scripts to scrape and update records using the GovInfo API.
- **Interactive Dashboard**: A Streamlit app to explore the data:
  - **Search by ID**: Lookup specific speech records.
  - **Phrase Trends**: Analyze the usage of specific phrases over time.
  - **Partisan Analysis**: Compare speech patterns between parties.
  - **Session Search**: Filter and browse speeches by congressional session.

## Database Schema

The core data is stored in a SQLite database (`congress_master.db`) with the following schema:

```sql
CREATE TABLE "speeches" (
  "speech_id" TEXT PRIMARY KEY,  -- Unique identifier for the speech
  "speech" TEXT,                 -- Full text content of the speech
  "date" INTEGER,                -- Date of the speech (YYYYMMDD format)
  "speakerid" REAL,              -- Bioguide ID or internal identifier
  "speaker" TEXT,                -- Full name of the speaker
  "is_mapped" INTEGER,           -- Boolean flag indicating if speaker is mapped to metadata
  "party" TEXT,                  -- Political party affiliation
  "state_x" TEXT,                -- State abbreviation
  "lastname" TEXT,               -- Speaker's last name
  "firstname" TEXT,              -- Speaker's first name
  "congress_session" INTEGER     -- Congress number (e.g., 118)
);
```

## Project Structure

```
legNLP/
├── streamlitMain.py           # Main entry point for the Streamlit dashboard
├── congress_master.db         # SQLite database (not included in repo, generated)
├── utils/
│   └── scrapeNewSessions.py   # Script to ingest modern records via GovInfo API
├── notebooks/
│   └── legNLP.ipynb           # Jupyter notebook for exploratory data analysis
├── src/                       # Application source code
│   ├── database.py            # Database connection and query management
│   └── components.py          # UI components for the Streamlit app
├── raw/                       # Raw data files (Speaker maps, n-grams)
└── processed/                 # Processed CSV datasets
```

## Setup & Usage

### Prerequisites

- Python 3.8+
- API Key for [GovInfo](https://api.govinfo.gov/) (for running the scraper)

### Installation

1. Clone the repository.
2. Install the required Python packages (e.g., `streamlit`, `pandas`, `requests`, `beautifulsoup4`, `tqdm`).

### Running the Dashboard

To launch the interactive dashboard:

```bash
streamlit run streamlitMain.py
```

### Updating the Database

To ingest new congressional records (requires API key configuration in the script):

```bash
python utils/scrapeNewSessions.py
```

## Data Sources

- **Modern Records**: 112th-119th Congresses sourced from the [GovInfo API](https://api.govinfo.gov/).
- **Historical Records**: 43rd-111th Congresses sourced from [Stanford University Libraries Social Science Data Collection](https://data.stanford.edu/congress_text).