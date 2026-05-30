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

- update every changed `character_state`
- update every changed `item_state` when tracked objects move, hide, break, or change hands
- update the `scene_state` exit conditions or results
- move any `plot_thread` status if the mystery or relationship changed
- log any permanent consequence as a new timeline event
- audit the prose file against scene facts if you drafted into a file
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
