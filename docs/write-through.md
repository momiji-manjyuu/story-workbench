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

Adopt or reject a parked idea once the decision is no longer speculative:

```bash
python3 tools/story.py adopt flood-prophet \
  --into ledger-theft \
  --decision "Adopted as an in-world rumor network, not one person."

python3 tools/story.py reject flood-prophet \
  --reason "Too similar to the Office rumor mechanism."
```

Create a post-scene delta stub before updating state:

```bash
python3 tools/story.py delta scene-001
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

`handoff` is safe by default and hides parked idea details. Use `python3 tools/story.py handoff --with-ideas`
only when you explicitly want brainstorming context. A `--refresh --with-ideas` run keeps
`ops/handoff/current.*` safe and writes the idea-inclusive snapshot to `ops/handoff/ideas.*`.

## Files

- `ops/checkpoints/*.json`: immutable turn-level snapshots
- `ops/handoff/current.md`: human-readable resume note
- `ops/handoff/current.json`: machine-readable resume note
- `ops/handoff/ideas.md` and `ops/handoff/ideas.json`: optional idea-inclusive handoff output
- `ops/scene-deltas/*.json`: post-scene update stubs

## Minimal habit

1. Change story data.
2. Run `validate`.
3. Run `audit`.
4. Run `audit --ideas` if parked ideas were discussed.
5. Run `checkpoint`.

If a turn ends without `checkpoint`, the next session has to reconstruct intent from raw diffs, which
is avoidable.
