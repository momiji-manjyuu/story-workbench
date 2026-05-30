# Architecture

The project uses a four-layer model so retrieval stays narrow and updates stay honest.

## 1. Canon

`data/canon/` holds stable facts:

- world rules
- characters
- locations
- factions
- items

These records should answer "what is generally true in this setting?"

## 2. State

`data/state/` holds the present tense:

- current world pressure
- current character conditions
- tracked item position, holder, and visibility
- current scene composition

These records should answer "what is true right now at this point in the story?"

Scenes carry a `sort_key`, and state snapshots point back to the scene where they changed. That
lets the tooling recover the latest valid state for a given scene instead of assuming only one
global "current" snapshot exists.

## 3. Plot

`data/plot/` holds promises and motion:

- unresolved questions
- episode intent
- payoff targets

These records should answer "what is the story trying to move or resolve?"

## 4. Timeline

`data/timeline/` is the causal spine. It captures events with date labels and sort keys so scene
logic can be checked against history.

## Retrieval strategy

When preparing to write a scene, pull data in this order:

1. project config
2. active scene state
3. POV and present character records plus their states
4. current location
5. active plot threads
6. relevant timeline events
7. world record only if a scene rule needs it

This keeps context small enough to reason over and avoids flooding scene work with irrelevant lore.
