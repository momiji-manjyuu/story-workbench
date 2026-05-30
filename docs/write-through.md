# Write-Through

This project uses a write-through protocol so conversation state does not vanish between sessions.

## Principle

If the story changes, the files change in the same turn.

That means:

- accepted truths update `canon`, `state`, `plot`, or `timeline`
- unstable thoughts become `idea` records
- every meaningful turn ends with a `checkpoint`

## Commands

Capture a parked idea:

```bash
python3 tools/story.py idea flood-prophet \
  --name "Flood Prophet rumor" \
  --summary "A witness figure that may be person, office myth, or distributed urban legend." \
  --spark "This could let the city speak back to the characters." \
  --question "Is the prophet one person or a title?" \
  --link memory-tithe-city
```

Capture the turn's outcome and next step:

```bash
python3 tools/story.py checkpoint "Opening scene outline aligned" \
  --scene scene-001 \
  --decision "Kept the gate confrontation as the opening set-piece." \
  --pending "Draft the first prose pass for scene-001." \
  --question "Does Jun search the satchel in public or in private?"
```

Read the current resume state:

```bash
python3 tools/story.py handoff
```

## Files

- `ops/checkpoints/*.json`: immutable turn-level snapshots
- `ops/handoff/current.md`: human-readable resume note
- `ops/handoff/current.json`: machine-readable resume note

## Minimal habit

1. Change story data.
2. Run `validate`.
3. Run `audit`.
4. Run `checkpoint`.

If a turn ends without `checkpoint`, the next session has to reconstruct intent from raw diffs, which
is avoidable.
