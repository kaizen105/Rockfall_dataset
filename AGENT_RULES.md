# Project
Noamundi Rockfall Simulation: a synthetic dataset generator (precursor engine + 2D trajectory engine). The dataset is simulated, not real. The code is the source of truth, and the data card must always match what the code actually produces.

# Hard rules
1. NEVER run `git push`, force-push, or change remotes. NEVER push to GitHub or upload to Hugging Face without my explicit approval in that message. Commit locally only when I ask. Work on a new branch, never on main.
2. NEVER overwrite, move, or delete existing data files (data_v2/, training_dataset.csv, spatial_metadata.csv, trajectories). New outputs go in a new directory. Ask before deleting anything.
3. Do not install, upgrade, or remove packages without telling me first.
4. Do not touch files outside this repo.
5. Before any command that takes more than ~5 minutes or writes more than ~1 GB, tell me what it will do and wait for a yes.
6. Do not add features, refactors, or roadmap items I did not ask for. Fix what is in scope and nothing more. If you see something else worth fixing, list it under "Out of scope findings" instead of doing it.

# Working style
- Explain your plan in a few lines before editing. Make small, reviewable changes.
- Never claim something works without running it and showing me the actual output.
- If a result surprises you or contradicts the plan, stop and tell me. Do not paper over it, tune until it looks good, or change thresholds to make a check pass.
- If a check fails, report the failure first, then propose a fix. Do not silently weaken the check.
- Keep a running log in CHANGELOG_V1.md: what changed, why, and the evidence.

# Validation rules
- Verify that the OUTPUT matches the design intent, not just that the code runs. Every design intent gets a measurable assertion that runs on the generated data.
- Assertions fail loudly (raise an error). No silent fallbacks: if a branch cannot run (for example an empty candidate list), log it explicitly and count it.
- Test on a small subset first (a few locations), then the full run.
- Reproducibility: every run is seeded with a recorded seed (seed BOTH `random` and `np.random`). The seed and all per-location random draws are saved to a metadata file, never into the hourly table.

# Data hygiene
- Never leave information about the label in same-timestamp features.
- Preserve row contiguity of each location's time series. Flag rows instead of deleting them.
- Terrain and weather inputs are real and must not be modified.

# Reporting
End every task with: what changed, what you ran, actual results, anything unexpected, and what you did NOT do.
