# PROMETHEUS-X

> **See Beyond the Expected. Detect the Unknown.**

PROMETHEUS-X is a universal industrial AI anomaly detection platform built from scratch for identifying both known and previously unseen defects across all **15 MVTec AD** product and texture categories.

## Technology Stack

- **Frontend:** React.js, JavaScript, HTML5, CSS3, Tailwind CSS, Vite
- **Backend:** Python 3.14.5, FastAPI, Uvicorn, Pydantic
- **Database & Auth:** Supabase (PostgreSQL + Auth + Storage)
- **AI/ML Engine:** PyTorch (`2.14.1+cu126`), ResNet18 pretrained feature extractor (`layer2` + `layer3`), PatchCore-inspired category-specific normal feature memory banks, anomaly heatmap generation
- **Target Hardware:** Windows + NVIDIA RTX 3050 Laptop GPU (4GB dedicated VRAM)

## Project Structure

```text
├── frontend/          # React + Tailwind CSS industrial dashboard
├── backend/           # FastAPI REST API, Pydantic schemas, Supabase & AI services
├── ai_engine/         # Isolated PyTorch ResNet18 + PatchCore inference & calibration
├── dataset_utils/     # MVTec AD 15-category registry & image preprocessing specs
├── supabase/          # PostgreSQL SQL migrations & Supabase config template
├── tests/             # FastAPI & module verification tests
└── docs/              # Architecture, DB schema, API design, and roadmap
```

## Documentation

- [System Architecture](docs/ARCHITECTURE.md)
- [Database Schema](docs/DATABASE_SCHEMA.md)
- [API Design](docs/API_DESIGN.md)
- [Development Roadmap](docs/ROADMAP.md)
- [Supabase Setup Guide](docs/SUPABASE_SETUP.md)

## Quick Start (Phase 4 — Full Stack)

### 1. Configure environment
```powershell
copy .env.example .env
# Edit .env — fill in SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_JWT_SECRET
```

### 2. Start the FastAPI backend (uses existing CUDA .venv)
```powershell
& "C:\Users\Chandu Y Hosamani\OneDrive\Desktop\PROMETHEUS-X\.venv\Scripts\python.exe" -m uvicorn backend.app.main:app --reload --port 8000
```
Backend API: `http://localhost:8000` · OpenAPI docs: `http://localhost:8000/docs`

### 3. Start the React frontend
```powershell
cd frontend
npm install      # first time only
npm run dev
```
Frontend: `http://localhost:5173`

### 4. Production frontend build
```powershell
cd frontend
npm run build
```

### Frontend Pages
| Route | Page | Auth Required |
|---|---|---|
| `/` | Dashboard — system status, model readiness, analytics overview | No |
| `/inspect` | Image Inspection — drag-and-drop upload, 15 MVTec categories | No |
| `/results` | Inspection Results — anomaly score, heatmap, defect regions | No |
| `/camera` | Live Camera — single-frame capture inspection | No |
| `/history` | Inspection History — browse, view detail, delete records | Yes |
| `/review` | False Positive Review — submit and view operator reviews | Yes |
| `/analytics` | Analytics — overview charts, distribution-shift monitoring | Yes |
| `/reports` | Reports — download text reports per inspection | Yes |
| `/login` | Operator Sign In (Supabase Auth) | No |
| `/register` | Operator Registration (Supabase Auth) | No |

### Model Status
No category memory banks are built yet. AI inspection returns a **409 Conflict** response until memory banks are built for a category using `MemoryBankTrainer`. The frontend clearly displays this state and never substitutes fake predictions.

---

## Supabase Setup

A complete, step-by-step guide is in [docs/SUPABASE_SETUP.md](docs/SUPABASE_SETUP.md).

### Quick reference — required environment variables

**Backend `.env` (server-side, never commit):**

| Variable | Source |
|---|---|
| `SUPABASE_URL` | Project Settings → API → Project URL |
| `SUPABASE_ANON_KEY` | Project Settings → API → anon public key |
| `SUPABASE_SERVICE_ROLE_KEY` | Project Settings → API → service_role secret ⚠️ |
| `SUPABASE_JWT_SECRET` | Project Settings → API → JWT Settings → JWT Secret |
| `SUPABASE_STORAGE_BUCKET` | `inspections` (the bucket you create) |
| `MAX_UPLOAD_BYTES` | `15728640` (15 MB default) |

**Frontend `frontend/.env` (Vite public — anon key only):**

| Variable | Source |
|---|---|
| `VITE_SUPABASE_URL` | Same Project URL |
| `VITE_SUPABASE_ANON_KEY` | Same anon public key |
| `VITE_API_BASE_URL` | `http://localhost:8000/api/v1` |

> **Security:** `SUPABASE_SERVICE_ROLE_KEY` and `SUPABASE_JWT_SECRET` must **never** appear in
> any frontend file. Both `.env` files are excluded from Git via `.gitignore`.

### Database migrations

Run in Supabase SQL Editor in this order:
1. `supabase/migrations/001_initial_schema.sql` — tables, indexes, baseline RLS
2. `supabase/migrations/002_rls_improvements.sql` — scoped RLS policies, auto-profile trigger
3. `supabase/storage_policies.sql` — storage bucket access policies (after creating the bucket)

### Manual Supabase Dashboard Steps Required
1. **Create Project:** Provision a Supabase project and copy the credentials above from **Project Settings → API**.
2. **SQL Editor:** Execute `001_initial_schema.sql` and `002_rls_improvements.sql`.
3. **Storage Bucket:** Go to **Storage → New bucket**, name it `inspections`, keep **Public bucket** unchecked (private), set a 15 MB limit, then run `supabase/storage_policies.sql`.
4. **Authentication:** Under **Authentication → URL Configuration**, set Site URL to `http://localhost:5173` and add `http://localhost:5173/**` to Redirect URLs (optionally disable email confirmation for local dev).

---w

## Known Limitations (Pre-Phase 7)
- **No Trained Memory Banks Yet:** Category memory banks are reserved for Phase 7. Until `MemoryBankTrainer` builds `.npz`/`.pt` artifacts for a category, `POST /api/v1/inspections` returns `409 Conflict` rather than fabricating predictions.
- **Live Camera Mode:** `LiveCameraPage` supports single-frame capture inspection only; continuous live-stream inference is not implemented.
- **Local Supabase Credentials Required:** History, Reviews, Analytics, Reports, and Storage persistence require real Supabase credentials in root `.env` and `frontend/.env`. Without them, public readiness/health endpoints work, while authenticated endpoints return `503` or `401`/`403`.
