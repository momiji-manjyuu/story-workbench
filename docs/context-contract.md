# Context Contract

The `context` command is the default bundle builder for drafting.

It always tries to include:

- project premise and authoring rules
- active world pressure
- current episode intent
- active scene summary, tensions, unknowns, and exit conditions
- present characters with both canon and current state
- active location
- active plot threads
- cited timeline events

It intentionally does not include:

- `data/ideas/**`
- unrelated canon records
- resolved plot threads
- historical events not referenced by the scene
- all character biographies in full

Every default `context <scene-id>` output ends with `## Context Manifest`. The manifest lists included
records by `kind: id` and states the exclusion policy so drafting sessions can see which material was
deliberately left out. Use `--no-manifest` only when you need a compact output.

The goal is not completeness. The goal is enough truth to write the next scene without contradiction.
