-- PROMETHEUS-X RLS Improvements Migration
-- Run this AFTER 001_initial_schema.sql in the Supabase SQL Editor.
-- Fixes overly-broad SELECT policies and adds missing INSERT/UPDATE/DELETE policies.

-- ============================================================
-- 1. FIX: inspections SELECT — scope to owner only
-- ============================================================
drop policy if exists "Authenticated users read inspections" on public.inspections;

create policy "Users read own inspections" on public.inspections
    for select using (auth.uid() = user_id);

-- ============================================================
-- 2. ADD: inspections DELETE — owner can delete their own rows
-- ============================================================
create policy "Users delete own inspections" on public.inspections
    for delete using (auth.uid() = user_id);

-- ============================================================
-- 3. FIX: inspection_results SELECT — scope via inspection owner
-- ============================================================
drop policy if exists "Authenticated users read results" on public.inspection_results;

create policy "Users read own inspection results" on public.inspection_results
    for select using (
        exists (
            select 1 from public.inspections i
            where i.id = inspection_id
              and i.user_id = auth.uid()
        )
    );

-- ============================================================
-- 4. FIX: defect_detections SELECT — scope via inspection chain
-- ============================================================
drop policy if exists "Authenticated users read detections" on public.defect_detections;

create policy "Users read own defect detections" on public.defect_detections
    for select using (
        exists (
            select 1
            from public.inspection_results ir
            join public.inspections i on i.id = ir.inspection_id
            where ir.id = inspection_result_id
              and i.user_id = auth.uid()
        )
    );

-- ============================================================
-- 5. FIX: review_records SELECT — reviewer sees only their own
-- ============================================================
drop policy if exists "Authenticated users read reviews" on public.review_records;

create policy "Users read own reviews" on public.review_records
    for select using (reviewer_id = auth.uid());

-- ============================================================
-- 6. ADD: users INSERT — only self-insert on signup
-- ============================================================
create policy "Users insert own profile" on public.users
    for insert with check (auth.uid() = id);

-- ============================================================
-- 7. ADD: users UPDATE — owner can update their own profile
-- ============================================================
create policy "Users update own profile" on public.users
    for update using (auth.uid() = id)
    with check (auth.uid() = id);

-- ============================================================
-- 8. ADD: updated_at auto-trigger on public.users
-- ============================================================
create or replace function public.set_updated_at()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists trg_users_updated_at on public.users;
create trigger trg_users_updated_at
    before update on public.users
    for each row execute procedure public.set_updated_at();

-- ============================================================
-- 9. ADD: auto-create user profile on Supabase auth signup
--    This fires when a new row is inserted into auth.users
--    and creates a matching row in public.users automatically.
-- ============================================================
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
    insert into public.users (id, email, full_name, role)
    values (
        new.id,
        new.email,
        coalesce(new.raw_user_meta_data->>'full_name', ''),
        'inspector'
    )
    on conflict (id) do nothing;
    return new;
end;
$$;

drop trigger if exists trg_on_auth_user_created on auth.users;
create trigger trg_on_auth_user_created
    after insert on auth.users
    for each row execute procedure public.handle_new_user();
