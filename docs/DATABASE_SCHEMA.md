# PROMETHEUS-X Database Schema Documentation

Database engine: **Supabase PostgreSQL 15+** (SQL migration: `supabase/migrations/001_initial_schema.sql`).

## 1. Entity-Relationship Overview

```text
auth.users (Supabase Auth)
    │ 1:1
    ▼
public.users ──< public.inspections ── 1:1 ──> public.inspection_results ──< public.defect_detections
                        │
                        └──< public.review_records >── public.users (reviewer_id)
```

## 2. Tables

### 2.1 `public.users`
Stores operator and admin profile metadata linked 1:1 to `auth.users`.
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `uuid` | PK, FK -> `auth.users(id)` | Supabase Auth user ID |
| `email` | `text` | UNIQUE, NOT NULL | Operator email |
| `full_name` | `text` | | Display name |
| `role` | `text` | DEFAULT `'inspector'` | `admin`, `engineer`, or `inspector` |
| `created_at` | `timestamptz` | DEFAULT `now()` | Profile creation timestamp |
| `updated_at` | `timestamptz` | DEFAULT `now()` | Last update timestamp |

### 2.2 `public.inspections`
Tracks every image upload or live camera frame submitted for inspection.
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `uuid` | PK, DEFAULT `gen_random_uuid()` | Inspection ID |
| `user_id` | `uuid` | FK -> `public.users(id)` | Submitting operator |
| `category_id` | `text` | CHECK (15 MVTec categories) | Target industrial category |
| `source_type` | `text` | CHECK (`upload`, `camera`) | Input source |
| `status` | `text` | CHECK (`pending`, `processing`, `completed`, `failed`) | Pipeline state |
| `image_storage_path` | `text` | | Path in Supabase Storage |
| `image_width` | `integer` | | Original width in px |
| `image_height` | `integer` | | Original height in px |
| `created_at` | `timestamptz` | DEFAULT `now()` | Submission timestamp |

### 2.3 `public.inspection_results`
Stores the quantitative AI output for each completed inspection.
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `uuid` | PK | Result ID |
| `inspection_id` | `uuid` | UNIQUE, FK -> `public.inspections(id)` | Parent inspection |
| `is_anomalous` | `boolean` | NOT NULL | Binary anomaly decision |
| `anomaly_score` | `double precision` | NOT NULL | Raw PatchCore distance score |
| `calibrated_confidence` | `double precision` | CHECK (`0.0 <= x <= 1.0`) | Calibrated confidence |
| `severity` | `text` | CHECK (`low`, `medium`, `high`, `critical`) | Severity tier |
| `heatmap_storage_path` | `text` | | Path to generated heatmap PNG |
| `distribution_shift_score` | `double precision` | | Drift metric vs normal bank |
| `inference_time_ms` | `double precision` | NOT NULL | End-to-end GPU latency |
| `model_version` | `text` | DEFAULT `'resnet18-patchcore-v1'` | Model/bank identifier |
| `created_at` | `timestamptz` | DEFAULT `now()` | Completion timestamp |

### 2.4 `public.defect_detections`
Stores localized bounding boxes extracted from the anomaly heatmap.
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `uuid` | PK | Detection ID |
| `inspection_result_id` | `uuid` | FK -> `public.inspection_results(id)` | Parent result |
| `bbox_x`, `bbox_y`, `bbox_w`, `bbox_h` | `double precision` | NOT NULL | Normalized `[0, 1]` bounding box |
| `area_ratio` | `double precision` | NOT NULL | Fraction of image area |
| `peak_score` | `double precision` | NOT NULL | Peak heatmap intensity in region |
| `label` | `text` | | Optional defect tag |

### 2.5 `public.review_records`
Stores human-in-the-loop reviews for false-positive tracking and threshold tuning.
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `uuid` | PK | Review ID |
| `inspection_id` | `uuid` | FK -> `public.inspections(id)` | Reviewed inspection |
| `reviewer_id` | `uuid` | FK -> `public.users(id)` | Reviewing engineer/inspector |
| `verdict` | `text` | CHECK (`confirmed_defect`, `false_positive`, `uncertain`) | Operator verdict |
| `corrected_severity` | `text` | CHECK (`low`, `medium`, `high`, `critical`) | Optional severity override |
| `notes` | `text` | | Operator comments |
| `created_at` | `timestamptz` | DEFAULT `now()` | Review timestamp |

## 3. Row Level Security (RLS)

All 5 tables have RLS enabled. Authenticated users can read inspection data and insert records attributed to their own `auth.uid()`. The FastAPI backend uses `SUPABASE_SERVICE_ROLE_KEY` for trusted server-side writes after verifying the user's JWT.
