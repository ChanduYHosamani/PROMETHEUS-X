# PROMETHEUS-X API Design Documentation

Base URL (Development): `http://localhost:8000/api/v1`

Interactive OpenAPI Docs (when backend is running): `http://localhost:8000/docs`

## 1. Authentication & Headers

Protected endpoints (`GET/DELETE /inspections`, `POST/GET /reviews`, `GET /analytics/*`) require a valid Supabase Auth HS256 JWT verified against `SUPABASE_JWT_SECRET`:
```http
Authorization: Bearer <supabase_access_token>
```

## 2. Implemented Endpoints (Phase 3)

### 2.1 Health & Model Management
- **`GET /api/v1/health`**
  - Returns service status, CUDA availability, GPU name, and non-secret Supabase configuration status.
- **`GET /api/v1/models/status`**
  - Returns ResNet18 backbone load state, device/FP16 settings, RTX 3050 VRAM telemetry, cached categories, and ready category count (`0..15`).
- **`POST /api/v1/models/{category_id}/load`**
  - Preloads a category's memory bank into the VRAM LRU cache (`409 Conflict` if the artifact has not been built yet).

### 2.2 Categories
- **`GET /api/v1/categories`**
  - Returns all 15 MVTec AD categories with `id`, `display_name`, `domain_type`, `default_input_size`, and `memory_bank_ready`.
- **`GET /api/v1/categories/{category_id}`**
  - Returns metadata for a single category or `404 Not Found`.

### 2.3 Inspections & History
- **`POST /api/v1/inspections`**
  - **Content-Type:** `multipart/form-data`
  - **Fields:** `category_id` (15 MVTec categories), `source_type` (`upload` | `camera`), `file` (PNG/JPEG/WEBP/BMP/TIFF, max 15 MB)
  - **Behavior:** Validates image & category, checks memory bank readiness (`409 Conflict` if unavailable), runs `PatchCoreDetector`, and persists image + heatmap + results to Supabase if configured.
  - **Response `200 OK`:** `InspectionPredictOut` (`inspection_id`, `is_anomalous`, `anomaly_score`, `calibrated_confidence`, `severity`, `heatmap_base64`, `heatmap_storage_path`, `detections[]`, `inference_time_ms`, `persisted_to_supabase`).
- **`GET /api/v1/inspections`** *(Auth required)*
  - Query params: `category_id`, `limit` (`1..100`), `offset`. Returns user-scoped inspection history from Supabase.
- **`GET /api/v1/inspections/{inspection_id}`** *(Auth required)*
  - Returns full inspection record, results, detections, and reviews (`404` if not found).
- **`DELETE /api/v1/inspections/{inspection_id}`** *(Auth required)*
  - Deletes a user-owned inspection record from Supabase.

### 2.4 False-Positive Reviews *(Auth required)*
- **`POST /api/v1/reviews`**
  - Body: `{ "inspection_id": "uuid", "verdict": "confirmed_defect" | "false_positive" | "uncertain", "corrected_severity": "...", "notes": "..." }`
  - Response `201 Created`: `ReviewOut`.
- **`GET /api/v1/reviews`**
  - Query params: `inspection_id`, `limit`. Returns operator review records from Supabase.

### 2.5 Analytics *(Auth required)*
- **`GET /api/v1/analytics/overview`**
  - Computes real inspection totals, anomaly rate, severity breakdown, and category counts from Supabase. Returns `status: "insufficient_data"` or `"unavailable"` when no stored records exist.
- **`GET /api/v1/analytics/distribution-shift`**
  - Computes per-category anomaly score drift from stored results (`status: "insufficient_data"` if fewer than 5 completed inspections exist).

## 3. Standard Error Format

```json
{
  "detail": "Human-readable error description"
}
```
- `400 Bad Request`: Invalid image format, corrupt file, empty upload, or unsupported category.
- `401 Unauthorized`: Missing, expired, or invalid Supabase JWT.
- `404 Not Found`: Unknown category or inspection ID.
- `409 Conflict`: Category memory bank has not been built yet.
- `413 Request Entity Too Large`: Uploaded image exceeds `MAX_UPLOAD_BYTES`.
- `503 Service Unavailable`: Supabase credentials or JWT secret not configured.
