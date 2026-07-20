# ARGUS — Zero-Harm Intelligence Layer

ARGUS is an industrial safety intelligence platform that fuses live sensor telemetry, permit state, operational context, and a causal risk graph into a unified safety monitoring experience.

## What’s been improved

- Elevated the risk-scoring engine from a heuristic surface to a calibrated, explainable zone scoring pipeline.
- Added geometry normalization so map polygons render as closed, stable shapes.
- Enhanced the live heatmap UI with richer status metadata and a stronger operator workflow.
- Introduced regression tests around scoring and geometry behavior to guard quality over time.

## Architecture overview

- Backend API: FastAPI endpoints for alerts, permits, heatmap, feedback, reports, and health.
- Simulation engine: Replays sensor, permit, weather, and shift streams into the agent stack.
- Risk graph: Evaluates causal conditions and produces hazard matches with explainable causal chains.
- Frontend: React + Leaflet dashboard for real-time geospatial risk monitoring.

## Run locally

1. Install dependencies:
   - `pip install -r requirements.txt`
   - `npm install`
2. Start the backend:
   - `uvicorn backend.api.main:app --reload`
3. Start the frontend:
   - `npm run dev`

## Quality goals

- Improve signal quality through more robust anomaly pressure and risk drivers.
- Improve result quality by aligning alerts with causal evidence and real plant context.
- Improve geospatial fidelity with normalized polygon geometry and richer zone metadata.
