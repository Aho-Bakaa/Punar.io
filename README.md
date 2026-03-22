# EPR Compliance System API

A stateless FastAPI microservice for analyzing e-waste device compliance, predicting carbon impact, and estimating material recovery.

## Features
- **Stateless Analysis Engine**: Exposes `/api/analyze/device` and `/api/analyze/batch` endpoints that process physical devices entirely in-memory without requiring database writes.
- **Built-in Device Lookup**: Uses an in-memory `DeviceMasterRepository` to perform exact and fuzzy matching to identify devices from a local CSV master dataset.
- **Automated Calculations**: Automatically calculates accountable weights based on device condition and estimates rare earth material recovery (Gold, Copper, Lithium).

## Setup & Running Locally

1. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the FastAPI development server:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

3. View standard API Documentation:
   Visit `http://localhost:8000/docs` in your browser to view the interactive Swagger UI and test endpoints directly.

## API Endpoints Overview

- `POST /api/analyze/device`: Analyze a single device. Returns recognized category, condition-adjusted weights, and environmental impact.
- `POST /api/analyze/batch`: Analyze a batch of devices. Returns aggregated sustainability summaries alongside per-device breakdowns.
- `GET /api/health`: Basic health check.
