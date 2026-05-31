# Drafting And Audit

Two new commands extend the project past storage and retrieval.

## `draft`

`draft <scene-id>` builds a writing packet from live project data.

Modes:

- `scaffold`: full drafting kit with continuity watchpoints, beat plan, dialogue pressure, and prose starter
- `beats`: just the scene beat plan
- `prose`: a compact prose seed for the opening movement of the scene

Example:

```bash
python3 tools/story.py draft scene-001 --mode scaffold
python3 tools/story.py draft scene-001 --mode prose --output drafts/scenes/scene-001.md
```

## `audit`

`audit` is a heuristic semantic continuity pass. It does not replace human judgment, but it catches
the kinds of drift that simple schema validation cannot see.

Checks include:

- POV and present-character logic
- scene chronology versus state snapshot timing
- scene location versus current character state
- scene goal drift versus current goals
- open plot threads that are not grounded in scene pressure
- item ownership versus holder, inventory, and location
- provisional, rumor, or meta records that are quietly driving scene truth
- optional prose-file checks against scene facts, legal pressure, and location constraints

Example:

```bash
python3 tools/story.py audit
python3 tools/story.py audit scene-001
python3 tools/story.py audit scene-001 --draft drafts/scenes/scene-001.md
python3 tools/story.py audit scene-001 --lang ja
python3 tools/story.py audit --ideas
```

The default audit language is `en`. In `--lang ja`, structural checks still run, but English-token
lexical overlap and contradiction heuristics are skipped so Japanese prose does not get a false sense
of semantic coverage.

`audit --ideas` runs the project-level idea leak audit. It warns when seed, exploring, parked, or
rejected idea markers appear outside `data/ideas/`, and when an adopted idea lacks `adopted_into`.

## `doctor`

`doctor` combines validation, project semantic audit, idea leak audit, documentation link checks, and
template checks.

```bash
python3 tools/story.py doctor
```

By default, idea leak findings are warnings and do not make `doctor` fail. Use
`python3 tools/story.py doctor --strict-ideas` when you want any idea leak finding to return exit code 1.

## Practical loop

1. `context`
2. `audit`
3. `draft`
4. write prose
5. update state
6. `validate`
7. `audit --draft`
8. `doctor`
