# React Refactor Status

## Current State

The original Streamlit application is still intact and remains the safest fallback:

- Streamlit entry: `app.py`
- New API entry: `api_server.py`
- New React frontend: `frontend/`

This means we now have two UI paths in parallel:

1. Legacy UI: `Streamlit + Python services`
2. New UI: `React + ECharts + Python API`

## New Architecture

### Backend API

The new backend layer lives in `backend/api/` and wraps the existing Python service layer instead of replacing it.

Key files:

- `backend/api/main.py`
- `backend/api/schemas.py`
- `api_server.py`

Available endpoints right now:

- `GET /api/health`
- `GET /api/dashboard/overview`
- `GET /api/dashboard/system-status`
- `GET /api/sessions`
- `POST /api/sessions`
- `GET /api/sessions/{session_id}`
- `PUT /api/sessions/{session_id}`
- `DELETE /api/sessions/{session_id}`
- `POST /api/chat`
- `POST /api/chat/stream`
- `GET /api/financial/{target}`
- `GET /api/comparison/{symbol}`
- `POST /api/report`

### Frontend

The React app is built with:

- `React`
- `TypeScript`
- `Vite`
- `ECharts`
- `echarts-for-react`

Key files:

- `frontend/src/App.tsx`
- `frontend/src/lib/api.ts`
- `frontend/src/components/EChartCard.tsx`
- `frontend/src/styles.css`

## How To Run

### 1. Keep the old version available

Run the existing Streamlit app:

```powershell
streamlit run app.py
```

### 2. Run the new API

```powershell
python api_server.py
```

Default API URL:

- `http://127.0.0.1:8000`

### 3. Run the new React frontend

```powershell
Set-Location frontend
npm.cmd run dev
```

Default frontend URL:

- `http://127.0.0.1:5173`

If you need to point the frontend at another API address, set:

```powershell
$env:VITE_API_BASE="http://127.0.0.1:8000"
```

before running `npm.cmd run dev`.

## What Has Been Verified

- Python API imports successfully.
- Health and session listing work.
- Chat endpoint returns structured payload and chart data.
- Financial endpoint returns structured rows.
- React production build passes with `npm.cmd run build`.

## Known Follow-Up Work

- The comparison page is scaffolded but still needs richer cards and chart visuals.
- The report page can render generated HTML, but export and print workflows are not built yet.
- The frontend bundle is currently large because ECharts is included in the main chunk.
- `npm audit` reports 2 moderate vulnerabilities in the current frontend dependency tree.

## Safety Notes

- The original Streamlit version was not removed.
- A timestamped backup snapshot already exists under `backups/`.
- New work should continue on the React/API path without overwriting the existing Streamlit UI.
