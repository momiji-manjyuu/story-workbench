# Story Workbench Agent Notes

This project is optimized for LLM-assisted fiction work.

## Operational rules

- Treat `data/canon/` as slow-moving truth. Do not update it casually during scene drafting.
- Treat `data/ideas/` as the parking lot for unstable ideas. Do not promote them into canon until adopted.
- Treat `data/state/` as the live present. After a scene changes facts on the ground, update it.
- Treat `data/plot/` as commitments and open questions. Keep statuses current.
- Treat `data/timeline/` as the causal backbone. Add dated events when new irreversible facts land.
- Treat `ops/handoff/current.md` as the resume point for new sessions.

## Write-through protocol

- If a story decision is accepted, write it through in the same turn.
- Stable changes go to `canon`, `state`, `plot`, or `timeline`.
- Unstable ideas go to `data/ideas/`.
- After any meaningful change, run `python3 tools/story.py checkpoint ...` to refresh handoff state.
- Before ending a turn with story progress, make sure `ops/handoff/current.md` reflects what changed and what remains pending.

## Before writing

1. Run `python3 tools/story.py validate`.
2. Read `python3 tools/story.py handoff`.
3. Run `python3 tools/story.py context <scene-id>` for the active scene.
4. Run `python3 tools/story.py audit <scene-id>` if the scene carries continuity risk.
5. Generate a drafting kit with `python3 tools/story.py draft <scene-id>`.
6. Inspect any directly involved records with `show`.

## After writing

1. Update the affected `scene_state` record.
2. Update every changed `character_state` record.
3. Advance any `plot_thread` statuses or notes.
4. Add a timeline event if the scene changes the world permanently.
5. Re-run `python3 tools/story.py validate`.
6. If prose was written to a file, run `python3 tools/story.py audit <scene-id> --draft <path>`.
7. Run `python3 tools/story.py checkpoint ...` with applied decisions and remaining pending actions.

## Scope discipline

- Do not overload scene records with whole-world lore.
- Do not hide current-state facts inside canon records.
- Prefer one record per entity, scene, thread, or event.
- If a fact is uncertain in-story, store that uncertainty explicitly instead of pretending it is canon.
- If an idea is interesting but premature, park it as an `idea` record instead of letting it leak into canon.
