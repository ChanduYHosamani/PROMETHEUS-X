-- PROMETHEUS-X Supabase Storage Bucket Policies
-- Run these statements in the Supabase SQL Editor AFTER creating the
-- "inspections" storage bucket in the Supabase dashboard.
--
-- Bucket creation is a manual step (see docs/SUPABASE_SETUP.md):
--   Dashboard → Storage → New bucket → Name: "inspections" → Private (not public)

-- ============================================================
-- Policy 1: Authenticated users can upload to their own folder
-- Path convention: {user_id}/{inspection_id}/input.{ext}
--                  {user_id}/{inspection_id}/heatmap.png
-- ============================================================
create policy "Authenticated users upload own files"
    on storage.objects
    for insert
    to authenticated
    with check (
        bucket_id = 'inspections'
        and (storage.foldername(name))[1] = auth.uid()::text
    );

-- ============================================================
-- Policy 2: Authenticated users can read their own files only
-- ============================================================
create policy "Authenticated users read own files"
    on storage.objects
    for select
    to authenticated
    using (
        bucket_id = 'inspections'
        and (storage.foldername(name))[1] = auth.uid()::text
    );

-- ============================================================
-- Policy 3: Authenticated users can delete their own files
-- ============================================================
create policy "Authenticated users delete own files"
    on storage.objects
    for delete
    to authenticated
    using (
        bucket_id = 'inspections'
        and (storage.foldername(name))[1] = auth.uid()::text
    );

-- ============================================================
-- Policy 4: Service role has unrestricted access (backend use)
-- The service_role key bypasses RLS automatically in Supabase,
-- so this policy is documented here for clarity only.
-- No explicit grant is needed for service_role.
-- ============================================================

-- ============================================================
-- Policy 5: Block all public (anonymous) access to this bucket
-- Supabase's "Private" bucket setting handles this, but this
-- explicit policy makes the intent clear.
-- ============================================================
-- (No insert/select policy for anon role = no public access.)
