-- Owner decision 2026-10-11: these maker-sourced rows have no age statement on the maker's page, so the seeded ages
-- (release numbers / older labels, not stated by the maker) are cleared to NAS. facts_verified_at-guarded.
update cellar.products set age_years = null, age_label = 'NAS', nas = true
where id in ('758ca907-a8df-469f-ad77-0896ca3d413f',  -- Abraham Bowman High Rye (seed 9)
             '03e85320-6c4d-4c2a-bc1e-ea008582e075',  -- Abraham Bowman Port Finished 2013 (seed 7)
             '522ae75c-da8b-4184-bc86-468c97a2cd47',  -- John J. Bowman Single Barrel (seed 9)
             '7065da6d-ce22-4c64-8c94-b2e6d71e587b')  -- Jefferson's Very Small Batch (seed 6)
  and facts_verified_at is null;
