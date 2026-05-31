# Workflow

## Add new stable lore

1. Create a record from `templates/`.
2. Fill the required fields.
3. Keep the summary short and factual.
4. Validate the project.
5. Write a checkpoint if this changes active work.

## Add a new scene

1. Create or update an `episode`.
2. Create a `scene_state`.
3. Assign a `sort_key` so state snapshots can resolve against chronology.
4. Make sure the scene references the exact character, location, and plot thread ids it touches.
5. Generate context from the scene before drafting prose.
6. Run a semantic audit if the scene depends on delicate continuity.
7. Park unresolved alternatives as `idea` records instead of stuffing them into canon notes.

## Advance the story

After a scene is written:

- create a scene delta stub with `python3 tools/story.py delta <scene-id>` if you want a checklist
  for post-scene changes
- update every changed `character_state`
- update every changed `item_state` when tracked objects move, hide, break, or change hands
- update the `scene_state` exit conditions or results
- record `reader_reveals` and `character_reveals` on `scene_state` when a mystery beat changes
  what the reader or a character knows
- move any `plot_thread` status if the mystery or relationship changed
- log any permanent consequence as a new timeline event
- audit the prose file against scene facts if you drafted into a file
- run `threads` to check open thread coverage when plot pressure changes
- checkpoint the accepted changes and the next pending action
- if `checkpoint` refuses to write, fix the validation or semantic errors first unless you intentionally want `--allow-findings`

## Truth levels

Every canon-like record carries `truth_status`:

- `canon`: authoritative truth
- `provisional`: likely true but still movable
- `rumor`: in-world claim with uncertain truth
- `meta`: author-side planning note

This prevents "author note" and "actual lore" from blending together.

## Unstable ideas

If an idea is not settled, put it in `data/ideas/parking/` with status `seed`, `exploring`, or
`parked`. Adopt it into canon only after the story commits to it.

Use `adopt` when an idea becomes part of stable project state:

```bash
python3 tools/story.py adopt flood-prophet \
  --into ledger-theft \
  --decision "Adopted as an in-world rumor network, not one person."
```

Use `reject` when a parked idea is closed out:

```bash
python3 tools/story.py reject flood-prophet \
  --reason "Too similar to the Office rumor mechanism."
```

Run `python3 tools/story.py audit --ideas` to check whether seed, exploring, parked, or rejected
idea markers have leaked into canon, state, plot, or timeline records.

## Health checks

`python3 tools/story.py doctor` runs validation, semantic audit, idea leak audit, documentation link
checks, and template checks in one pass. It is useful before committing changes or handing the
workspace to another session.
