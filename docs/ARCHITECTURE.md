# PROMETHEUS-X System Architecture

> **Tagline:** See Beyond the Expected. Detect the Unknown.

## 1. High-Level Architecture

PROMETHEUS-X uses a strictly decoupled three-tier architecture:

```text
+---------------------------+        REST / JSON / Multipart        +---------------------------+
|     React.js Frontend     | <-----------------------------------> |      FastAPI Backend      |
|  Tailwind CSS + Vite UI   |     (+ Supabase JWT Bearer Token)     |  Routes, Auth, Services   |
+---------------------------+                                       +-------------+-------------+
        |                                                                         |
        | (Auth Session: Anon Key)                                 +--------------+--------------+
        v                                                          |                             |
+---------------------------+                                      v                             v
|     Supabase Platform     | <---- Service Role / PostgREST ----+ |    Isolated AI/ML Engine    |
|  Auth, PostgreSQL, Storage|                                      |  ResNet18 + PatchCore (GPU) |
+---------------------------+                                      +-----------------------------+
```

## 2. Layer Communication Contracts

### 2.1 React Frontend <-> FastAPI Backend
- **Protocol:** HTTP/1.1 REST over JSON (`application/json`) and `multipart/form-data` for image/camera-frame uploads.
- **Dev Proxy & CORS:** Vite proxies `/api` to `http://localhost:8000` in development; FastAPI enforces explicit `CORS_ORIGINS` from environment variables.
- **Authentication:** React obtains a JWT access token via Supabase Auth (`VITE_SUPABASE_ANON_KEY`) and attaches `Authorization: Bearer <jwt>` to every protected FastAPI request via Axios interceptors (`frontend/src/api/client.js`).
- **Live Camera Mode:** React captures frames from `navigator.mediaDevices.getUserMedia` onto an HTML5 `<canvas>`, encodes JPEG/PNG blobs, and posts them to `POST /api/v1/inspections/predict` at a throttled cadence to avoid saturating the 4GB GPU.

### 2.2 FastAPI Backend <-> Supabase
- **PostgreSQL Persistence:** FastAPI uses `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` exclusively on the server side (`backend/app/services/supabase_service.py`) to insert `inspections`, `inspection_results`, `defect_detections`, and `review_records`.
- **JWT Verification:** FastAPI validates incoming `Authorization: Bearer <jwt>` tokens using `SUPABASE_JWT_SECRET` (`backend/app/core/security.py`) before attributing records to `user_id`.
- **Object Storage:** Original inspection images and generated anomaly heatmap overlays are stored in the private Supabase Storage bucket (`inspections`), with signed URLs returned to the frontend.

### 2.3 FastAPI Backend <-> AI Inference Engine
- **Isolation:** `ai_engine/` has zero dependency on FastAPI or Supabase. It exposes pure Python/PyTorch interfaces (`PatchCoreDetector`, `CategoryMemoryBankManager`, `ResNet18FeatureExtractor`).
- **Service Bridge:** `InferenceService` (`backend/app/services/inference_service.py`) owns the singleton `PatchCoreDetector` instance and executes inference inside `anyio.to_thread.run_sync` (with a GPU lock) so PyTorch CUDA calls never block FastAPI's async event loop.

## 3. Windows & NVIDIA RTX 3050 (4GB VRAM) Optimization Strategy

To support all **15 MVTec AD categories** reliably within **4GB dedicated VRAM** on Windows:
1. **Lightweight Backbone:** `ResNet18` pretrained on ImageNet, extracting only `layer2` (128 channels) and `layer3` (256 channels) features—keeping backbone weights under ~45 MB.
2. **FP16 Half-Precision:** Feature extraction and k-NN distance computation run in `torch.float16` (`AI_USE_FP16=true`) inside `torch.inference_mode()`.
3. **Coreset Subsampling:** Category-specific normal memory banks are compressed using greedy coreset subsampling (`coreset_sampling_ratio=0.1`) so each bank occupies only a few megabytes.
4. **LRU VRAM Cache:** `CategoryMemoryBankManager` keeps at most `AI_MAX_CACHED_BANKS=2` category memory banks pinned in GPU VRAM at once, evicting least-recently-used banks to CPU/disk and calling `torch.cuda.empty_cache()` when switching categories.
5. **Sequential GPU Lock:** An async semaphore/lock ensures concurrent uploads/camera frames do not cause simultaneous VRAM allocation spikes.

## 4. Secure Environment Variable Management

- **Never commit `.env`:** `.gitignore` excludes `.env`, `.env.local`, and `.env.*.local`.
- **Template:** `.env.example` documents every required variable without real credentials.
- **Privilege Separation:**
  - `VITE_*` variables are public browser-safe values (`VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_API_BASE_URL`).
  - `SUPABASE_SERVICE_ROLE_KEY` and `SUPABASE_JWT_SECRET` exist **only** in backend server environment variables and are never exposed to React.
