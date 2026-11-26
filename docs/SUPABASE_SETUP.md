# PROMETHEUS-X — Supabase Setup Guide

> **See Beyond the Expected. Detect the Unknown.**

This guide walks you through every step needed to connect PROMETHEUS-X to your
Supabase project. All steps are **manual** (dashboard + SQL editor); no Supabase
CLI or local Docker setup is required for the hackathon.

---

## Table of Contents

1. [Create a Supabase Project](#1-create-a-supabase-project)
2. [Collect Your Credentials](#2-collect-your-credentials)
3. [Run Database Migrations](#3-run-database-migrations)
4. [Configure Storage](#4-configure-storage)
5. [Configure Auth Settings](#5-configure-auth-settings)
6. [Configure the Backend `.env`](#6-configure-the-backend-env)
7. [Configure the Frontend `.env`](#7-configure-the-frontend-env)
8. [Verify the Connection](#8-verify-the-connection)
9. [End-to-End Smoke Test](#9-end-to-end-smoke-test)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Create a Supabase Project

1. Go to [https://supabase.com](https://supabase.com) and sign in (or create a free account).
2. Click **New project**.
3. Fill in:
   - **Name:** `prometheus-x` (or any name you like)
   - **Database password:** choose a strong password and **save it**
   - **Region:** pick the closest to you
4. Click **Create new project** and wait ~2 minutes for provisioning.

---

## 2. Collect Your Credentials

Navigate to **Project Settings → API** in the left sidebar.

| Variable | Where to find it |
|---|---|
| `SUPABASE_URL` | "Project URL" (e.g. `https://abcdefgh.supabase.co`) |
| `SUPABASE_ANON_KEY` | Under "Project API keys" → `anon public` |
| `SUPABASE_SERVICE_ROLE_KEY` | Under "Project API keys" → `service_role secret` ⚠️ **Never expose to frontend** |
| `SUPABASE_JWT_SECRET` | **Project Settings → API → JWT Settings → JWT Secret** |

> [!CAUTION]
> The `SERVICE_ROLE_KEY` bypasses all Row Level Security policies.
> It must only ever appear in your backend `.env` file and must never be committed to Git.

---

## 3. Run Database Migrations

Go to **SQL Editor** in the left sidebar and run each file in order.

### Step 3a — Initial schema

Paste the full contents of:
```
supabase/migrations/001_initial_schema.sql
```
Click **Run**. Expected output: no errors, tables created.

### Step 3b — RLS improvements

Paste the full contents of:
```
supabase/migrations/002_rls_improvements.sql
```
Click **Run**. This migration:
- Restricts `inspections` SELECT to the row owner only
- Restricts `inspection_results` and `defect_detections` SELECT via ownership chain
- Restricts `review_records` SELECT to the reviewer
- Adds `users` INSERT and UPDATE policies
- Adds `inspections` DELETE policy
- Adds an `updated_at` auto-trigger on `public.users`
- Adds an auto-profile trigger (`handle_new_user`) that creates a `public.users` row on signup

### Step 3c — Storage bucket policies (after creating the bucket in Step 4)

Paste the full contents of:
```
supabase/storage_policies.sql
```
Click **Run** after completing Step 4.

---

## 4. Configure Storage

1. Go to **Storage** in the left sidebar.
2. Click **New bucket**.
3. Fill in:
   - **Name:** `inspections`
   - **Public bucket:** ❌ **unchecked** (keep it private)
   - **File size limit:** `15` MB
   - **Allowed MIME types:** `image/jpeg, image/png, image/webp`
4. Click **Create bucket**.
5. Now go back to **SQL Editor** and run `supabase/storage_policies.sql` (Step 3c above).

Storage paths used by PROMETHEUS-X:
```
inspections/{user_id}/{inspection_id}/input.jpg
inspections/{user_id}/{inspection_id}/heatmap.png
```

---

## 5. Configure Auth Settings

1. Go to **Authentication → Providers** in the left sidebar.
2. Under **Email**, ensure **Enable Email provider** is turned on.
3. For hackathon development (optional but recommended):
   - Disable **Confirm email** to skip the confirmation email step.
   - Go to **Authentication → Email Templates** if you want to customize later.
4. Under **Authentication → URL Configuration**:
   - Set **Site URL** to `http://localhost:5173`
   - Add `http://localhost:5173/**` to **Redirect URLs**

---

## 6. Configure the Backend `.env`

Create a file named `.env` **in the project root** (next to `.env.example`):

```dotenv
# Application
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# Supabase — backend only
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here
SUPABASE_JWT_SECRET=your-jwt-secret-here
SUPABASE_STORAGE_BUCKET=inspections

# Frontend (Vite public — anon key only, never service_role)
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_SUPABASE_URL=https://your-project-ref.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key-here

# AI Engine
AI_DEVICE=cuda
AI_USE_FP16=true
AI_MAX_CACHED_BANKS=2
MVTEC_DATASET_DIR=C:/path/to/mvtec_anomaly_detection

# Upload limits
MAX_UPLOAD_BYTES=15728640
```

> [!IMPORTANT]
> The `.env` file is excluded from Git via `.gitignore`. Never commit it.

---

## 7. Configure the Frontend `.env`

Vite reads env vars from a `.env` file inside the `frontend/` folder.
Create `frontend/.env` with **only the public keys**:

```dotenv
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_SUPABASE_URL=https://your-project-ref.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key-here
```

> [!CAUTION]
> Do **NOT** add `SUPABASE_SERVICE_ROLE_KEY` or `SUPABASE_JWT_SECRET` here.
> Any `VITE_` variable is bundled into the browser JavaScript and is publicly visible.

---

## 8. Verify the Connection

### 8a — Backend health check

Start the FastAPI server:
```powershell
cd "c:\Users\Chandu Y Hosamani\OneDrive\Desktop\project cv"
& "C:\Users\Chandu Y Hosamani\OneDrive\Desktop\PROMETHEUS-X\.venv\Scripts\uvicorn.exe" backend.app.main:app --reload
```

Then open: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

Expected response:
```json
{
  "status": "ok",
  "supabase": {
    "configured": true,
    "url_set": true,
    "service_role_key_present": true,
    "jwt_secret_present": true
  }
}
```

### 8b — Supabase table verification

In the **Supabase Table Editor**, confirm these tables exist:
- `public.users`
- `public.inspections`
- `public.inspection_results`
- `public.defect_detections`
- `public.review_records`

### 8c — Run Phase 5 integration tests

```powershell
& "C:\Users\Chandu Y Hosamani\OneDrive\Desktop\PROMETHEUS-X\.venv\Scripts\python.exe" tests/test_supabase_integration.py
```

All 15 tests should pass with `ALL_PHASE5_TESTS_PASSED`.

---

## 9. End-to-End Smoke Test

After Phase 7 (memory bank training), you can run a full smoke test:

1. **Register a user** at `http://localhost:5173/register`
2. **Log in** at `http://localhost:5173/login`
3. **Go to Inspect** → select a category (e.g. `bottle`) → upload a test image
4. Click **Start Inspection**
5. Verify the result page shows anomaly score, heatmap, and severity
6. Check **Supabase Table Editor → inspections** — a new row should appear
7. Check **Storage → inspections bucket** — input image and heatmap should be uploaded
8. Go to **History** in the sidebar — the inspection should appear

---

## 10. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `503 Authentication not configured` | `SUPABASE_JWT_SECRET` missing from backend `.env` | Add the JWT secret from Project Settings → API → JWT Settings |
| `401 Invalid token signature` | Wrong JWT secret | Copy the exact secret from Supabase dashboard — no extra spaces |
| Backend health shows `configured: false` | Env var not loaded | Restart uvicorn after editing `.env`; check for typos in key names |
| Storage upload returns 403 | Bucket is public or policies not applied | Recheck bucket is private; re-run `storage_policies.sql` |
| User signup doesn't create `public.users` row | `002_rls_improvements.sql` not run | Run migration 002 in Supabase SQL Editor |
| `relation "public.users" does not exist` | Migrations not run at all | Run `001_initial_schema.sql` first, then `002_rls_improvements.sql` |
| Frontend shows "Supabase not configured" | `VITE_SUPABASE_URL` or `VITE_SUPABASE_ANON_KEY` missing in `frontend/.env` | Create `frontend/.env` with the public keys and restart `npm run dev` |

---

*PROMETHEUS-X — Industrial AI Anomaly Detection Platform*
*Phase 5: Supabase Database, Authentication & Storage*
