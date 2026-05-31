# Story Workbench

`Story Workbench` is a file-first project scaffold for collaborative fiction work with an LLM.
It separates stable canon, mutable story state, and plot progression so scene writing does not
collapse into a single monolithic notes file.

Japanese version: [README.ja.md](README.ja.md)

## Why this shape

- `data/canon/` stores durable world facts.
- `data/ideas/` stores unstable or parked ideas that should not contaminate canon yet.
- `data/state/` stores the current live situation and scene-local truth, including tracked item snapshots.
- `data/plot/` stores open questions, episode plans, and payoff targets.
- `data/timeline/` stores dated events so causality stays explicit.
- `ops/checkpoints/` and `ops/handoff/` preserve accepted decisions and pending work across sessions.
- `tools/story.py` is the main interface for validation, listing, search, context assembly, and stubs.

## Project boundary

One Story Workbench workspace is one story project. Do not mix unrelated stories inside the same
`data/` tree or split records with a `project_id`; the context, audit, checkpoint, and handoff
commands assume every record belongs to the same story. Start a separate repository or workspace for
another story.

## Suggested working loop

1. Run `python3 tools/story.py validate`.
2. Inspect what matters with `list`, `show`, `search`, and `context`.
3. Run `python3 tools/story.py audit <scene-id>` before prose work if continuity is fragile.
4. Build a drafting kit with `python3 tools/story.py draft <scene-id>`.
5. Draft or revise prose.
6. Use `python3 tools/story.py delta <scene-id>` if you want a structured post-scene update stub.
7. Update `data/state/` and `data/plot/` to reflect what changed.
8. Adopt or reject parked ideas with `adopt` / `reject` once a decision lands.
9. Run `python3 tools/story.py checkpoint ...` so the next session can resume cleanly.
   `checkpoint` now blocks if validation or semantic errors remain, unless you deliberately use `--allow-findings`.
10. Re-run `python3 tools/story.py validate`, `audit`, or `doctor`.

## Core commands

```bash
python3 tools/story.py validate
python3 tools/story.py list character
python3 tools/story.py show character mira-quill
python3 tools/story.py search ledger
python3 tools/story.py context scene-001
python3 tools/story.py audit scene-001
python3 tools/story.py draft scene-001 --mode scaffold
python3 tools/story.py audit scene-001 --draft drafts/scenes/scene-001.md
python3 tools/story.py audit --ideas
python3 tools/story.py idea flood-prophet --name "Flood Prophet rumor" --summary "A possible witness figure" --spark "What if the city has a human rumor engine?" --question "Is this a person or a distributed legend?"
python3 tools/story.py adopt flood-prophet --into ledger-theft --decision "Adopted as an in-world rumor network, not one person."
python3 tools/story.py reject flood-prophet --reason "Too similar to another rumor mechanism."
python3 tools/story.py delta scene-001
python3 tools/story.py threads
python3 tools/story.py checkpoint "Opening beat aligned" --scene scene-001 --decision "Kept Jun at Tidegate as the gate obstacle" --pending "Write the actual scene prose"
python3 tools/story.py handoff
python3 tools/story.py handoff --with-ideas
python3 tools/story.py doctor
python3 tools/story.py stub character lio-vann --name "Lio Vann"
```

## Design documents

- [`docs/architecture.md`](docs/architecture.md)
- [`docs/workflow.md`](docs/workflow.md)
- [`docs/context-contract.md`](docs/context-contract.md)
- [`docs/drafting-and-audit.md`](docs/drafting-and-audit.md)
- [`docs/write-through.md`](docs/write-through.md)

## Layout

```text
story-workbench/
├── AGENTS.md
├── config/
├── data/
│   ├── canon/
│   ├── ideas/
│   ├── plot/
│   ├── state/
│   └── timeline/
├── docs/
├── drafts/
├── ops/
├── schemas/
├── src/
├── templates/
├── tests/
└── tools/
```

## Storage policy

JSON is the authoritative format because it is strict, easy to validate, and easy for tools to
diff. Markdown is used for documentation and operating rules, not for canon itself.

`scene_state.sort_key` now anchors chronology, and `character_state`, `world_state`, and
`item_state` snapshots resolve against the latest state at or before that scene.

## Cross-session continuity

Use `checkpoint` whenever a story decision is accepted or a scene result changes the project. That
refreshes `ops/handoff/current.md` and `ops/handoff/current.json`, which are the first files to read
when resuming from a new session.

Handoff files are safe by default: parked idea details are hidden from `handoff`, checkpoint refreshes,
and `ops/handoff/current.*`. Use `python3 tools/story.py handoff --with-ideas` only when you explicitly
want brainstorming context.

Safe handoff hides structured idea details, idea ids, and idea-related touched records, but it does not
redact free-text checkpoint fields such as summaries, decisions, pending actions, open questions, or
artifacts. Do not write speculative idea details into checkpoint free text unless they are safe to read
when resuming. Keep speculative material in `data/ideas/**` and use `handoff --with-ideas` only when you
intentionally want brainstorming context.
