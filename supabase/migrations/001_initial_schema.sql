-- PROMETHEUS-X Initial PostgreSQL Schema for Supabase
-- Covers: Users (profiles), Inspections, Inspection Results, Defect Detections, Review Records

create extension if not exists "pgcrypto";

-- 1. Users / Operator Profiles (linked 1:1 with Supabase auth.users)
create table if not exists public.users (
    id uuid primary key references auth.users(id) on delete cascade,
    email text unique not null,
    full_name text,
    role text not null default 'inspector' check (role in ('admin', 'engineer', 'inspector')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- 2. Inspections (one row per uploaded image or live camera frame)
create table if not exists public.inspections (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references public.users(id) on delete set null,
    category_id text not null check (category_id in (
        'bottle', 'cable', 'capsule', 'carpet', 'grid',
        'hazelnut', 'leather', 'metal_nut', 'pill', 'screw',
        'tile', 'toothbrush', 'transistor', 'wood', 'zipper'
    )),
    source_type text not null check (source_type in ('upload', 'camera')),
    status text not null default 'pending' check (status in ('pending', 'processing', 'completed', 'failed')),
    image_storage_path text,
    image_width integer,
    image_height integer,
    created_at timestamptz not null default now()
);

-- 3. Inspection Results (1:1 with completed inspection)
create table if not exists public.inspection_results (
    id uuid primary key default gen_random_uuid(),
    inspection_id uuid not null unique references public.inspections(id) on delete cascade,
    is_anomalous boolean not null,
    anomaly_score double precision not null,
    calibrated_confidence double precision not null check (calibrated_confidence >= 0.0 and calibrated_confidence <= 1.0),
    severity text not null check (severity in ('low', 'medium', 'high', 'critical')),
    heatmap_storage_path text,
    distribution_shift_score double precision,
    inference_time_ms double precision not null,
    model_version text not null default 'resnet18-patchcore-v1',
    created_at timestamptz not null default now()
);

-- 4. Defect Detections (0..N localized defect regions per inspection result)
create table if not exists public.defect_detections (
    id uuid primary key default gen_random_uuid(),
    inspection_result_id uuid not null references public.inspection_results(id) on delete cascade,
    bbox_x double precision not null,
    bbox_y double precision not null,
    bbox_w double precision not null,
    bbox_h double precision not null,
    area_ratio double precision not null,
    peak_score double precision not null,
    label text
);

-- 5. Review Records (human-in-the-loop false-positive & severity verification)
create table if not exists public.review_records (
    id uuid primary key default gen_random_uuid(),
    inspection_id uuid not null references public.inspections(id) on delete cascade,
    reviewer_id uuid not null references public.users(id) on delete cascade,
    verdict text not null check (verdict in ('confirmed_defect', 'false_positive', 'uncertain')),
    corrected_severity text check (corrected_severity in ('low', 'medium', 'high', 'critical')),
    notes text,
    created_at timestamptz not null default now()
);

-- Indexes for fast dashboard queries
create index if not exists idx_inspections_category_created on public.inspections(category_id, created_at desc);
create index if not exists idx_inspections_user_created on public.inspections(user_id, created_at desc);
create index if not exists idx_results_severity on public.inspection_results(severity, is_anomalous);
create index if not exists idx_detections_result on public.defect_detections(inspection_result_id);
create index if not exists idx_reviews_inspection on public.review_records(inspection_id);

-- Enable Row Level Security (RLS)
alter table public.users enable row level security;
alter table public.inspections enable row level security;
alter table public.inspection_results enable row level security;
alter table public.defect_detections enable row level security;
alter table public.review_records enable row level security;

-- Baseline RLS policies (authenticated users can read/write their own data; service_role bypasses RLS)
create policy "Users read own profile" on public.users
    for select using (auth.uid() = id);

create policy "Authenticated users read inspections" on public.inspections
    for select using (auth.role() = 'authenticated');

create policy "Users insert own inspections" on public.inspections
    for insert with check (auth.uid() = user_id);

create policy "Authenticated users read results" on public.inspection_results
    for select using (auth.role() = 'authenticated');

create policy "Authenticated users read detections" on public.defect_detections
    for select using (auth.role() = 'authenticated');

create policy "Authenticated users read reviews" on public.review_records
    for select using (auth.role() = 'authenticated');

create policy "Users insert own reviews" on public.review_records
    for insert with check (auth.uid() = reviewer_id);
