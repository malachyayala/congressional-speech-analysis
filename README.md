# Congressional Record NLP Database & Dashboard

**A high-performance NLP pipeline and analytical dashboard processing 17+ million records of U.S. Congressional history (43rd–119th Congress).**

This project aggregates 140+ years of legislative data into a unified SQLite database, enabling semantic analysis of partisan trends and policy shifts. It features a hybrid ETL pipeline and a GPU-accelerated deep learning classification system to filter procedural noise from substantive debate.

---

## Technical Highlights

* **Scale:** Successfully ingested and indexed **17 million+ rows** of text data.
* **Hybrid Data Engineering:** Merged historical OCR data (Stanford) with modern API streams (GovInfo), normalizing schema across centuries of format changes.
* **Deep Learning Pipeline:** Implemented Zero-Shot Classification using **DistilBART (`valhalla/distilbart-mnli-12-1`)** to distinguish administrative procedure from policy debate.
* **Hardware Optimization:** Leveraged **NVIDIA RTX 4080 Super** with FP16 precision and dynamic batching to accelerate inference on the 17M dataset.
* **Concurrency:** Built a robust scraping engine with multi-threading and automated rate-limit handling (sleep logic) to manage GovInfo's 36k/hour request cap.

---

## System Architecture

### 1. Data Ingestion (The ETL Layer)
The system aggregates data from two distinct sources into a unified `congress_master.db` SQLite database:
* **Historical (43rd–111th):** Parsed from the Stanford University Libraries Social Science Data Collection.
* **Modern (112th–119th):** Sourced via the **GovInfo API**.
    * *Challenge:* The API enforces a limit of 36,000 requests/hour.
    * *Solution:* Developed a multi-threaded ingestion script with smart error handling that detects rate limits and sleeps for 45-minute intervals to maximize throughput without triggering bans.

### 2. The NLP Filtering Pipeline
To separate "Parliamentary Skeleton" (procedural noise) from "Policy Signal," the system uses a two-stage filter:
1.  **Heuristic SQL Filter:** A fast-pass SQL script flags rows containing high-frequency procedural stopwords (e.g., "yield back", "quorum call").
2.  **Zero-Shot Classification (semantic-filter):** Remaining speeches are passed through a `DistilBART` Zero-Shot classifier to assign a probability score of "Substantive" vs. "Procedural."
    * *Optimization:* Inference is optimized via CUDA on an RTX 4080 Super, utilizing mixed precision (FP16) for memory efficiency.

### 3. Frontend Dashboard
A Streamlit application (`streamlitMain.py`) provides an interactive interface for researchers to:
* **Search by ID:** Instant lookup of specific speech records.
* **Phrase Trends:** Visualize the rise and fall of specific bigrams over 140 years.
* **Partisan Analysis:** Compare semantic patterns between parties.
* **Session Search:** Filter speeches by congressional session.

---

## Project Structure

```text
legNLP/
├── streamlitMain.py        # Main entry point for the Dashboard
├── congress_master.db      # SQLite Warehouse (17M+ rows)
├── utils/
│   ├── scrapeNewSessions.py # Multi-threaded API scraper (GovInfo)
│   └── filterProcedure.py    # Torch/CUDA inference script for Zero-Shot
├── notebooks/
│   └── legNLP.ipynb        # EDA and Prototype Logic
├── src/
│   ├── database.py         # Connection pooling and SQL query management
│   └── components.py       # Reusable Streamlit UI components