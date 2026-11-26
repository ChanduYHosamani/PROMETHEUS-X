# PROMETHEUS-X Development Roadmap

## Phase 1: Foundation & Architecture *(Completed)*
- Workspace inspection and verification of existing CUDA Python environment (`3.14.5`, `torch 2.14.1+cu126`, RTX 3050).
- Clean separation of `frontend/`, `backend/`, `ai_engine/`, `dataset_utils/`, `supabase/`, `tests/`, and `docs/`.
- React + Tailwind CSS initialization and FastAPI + Pydantic v1 API scaffold.
- Supabase PostgreSQL schema (`users`, `inspections`, `inspection_results`, `defect_detections`, `review_records`) with RLS policies.
- Complete architecture, database, API, and environment variable documentation.

## Phase 2: Core AI Engine & Inspection Pipeline
- Implement `ResNet18FeatureExtractor` (`layer2` + `layer3` forward hooks, FP16 inference mode).
- Implement `CategoryMemoryBankManager` with greedy coreset subsampling and 2-bank LRU VRAM cache for RTX 3050 4GB VRAM.
- Build normal feature memory banks across all 15 MVTec AD categories (`dataset_utils/` + `ai_engine/`).
- Implement anomaly heatmap generation, connected-component defect localization, and `POST /api/v1/inspections/predict`.
- Wire Supabase Auth JWT verification, PostgreSQL persistence, and Storage uploads for images and heatmaps.
- Connect React Upload Inspection & Inspection History views to FastAPI.

## Phase 3: Calibration, Drift Monitoring & Human-in-the-Loop Review
- Implement confidence calibration and severity estimation (`low`, `medium`, `high`, `critical`) per category.
- Implement unseen defect evaluation benchmarks (AUROC / pixel-AUROC on MVTec AD test splits).
- Implement distribution-shift monitoring (`GET /api/v1/analytics/distribution-shift`).
- Implement False-Positive Review workflow (`POST /api/v1/reviews`) and operator audit trail.

## Phase 4: Live Camera, Reports & Animated Industrial Dashboard
- Implement Live Camera Inspection mode in React (`getUserMedia` + throttled frame streaming + live heatmap overlay).
- Build downloadable Inspection Reports (JSON/CSV/PDF summary).
- Polish modern animated industrial dashboard with real-time GPU/VRAM telemetry, category filters, and hackathon demo mode.
