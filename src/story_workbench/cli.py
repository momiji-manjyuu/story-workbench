from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "before",
    "but",
    "by",
    "for",
    "from",
    "had",
    "has",
    "have",
    "her",
    "his",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "she",
    "that",
    "the",
    "their",
    "them",
    "there",
    "they",
    "this",
    "to",
    "under",
    "was",
    "were",
    "with",
}

TOKEN_ALIASES = {
    "allied": "ally",
    "allies": "ally",
    "barge": "ship",
    "checking": "inspect",
    "checks": "inspect",
    "courier": "runner",
    "crowds": "queue",
    "detained": "detain",
    "detains": "detain",
    "disappearance": "missing",
    "disappeared": "missing",
    "doubled": "increase",
    "forged": "illegal",
    "friendship": "friend",
    "inspection": "inspect",
    "inspections": "inspect",
    "inspector": "inspect",
    "inspectors": "inspect",
    "ledger": "record",
    "ledgers": "record",
    "mistrust": "hostile",
    "queues": "queue",
    "recognized": "notice",
    "recognizes": "notice",
    "searches": "inspect",
    "seized": "seize",
    "stole": "steal",
    "stolen": "steal",
    "surge": "increase",
    "surges": "increase",
    "theft": "steal",
    "tunnels": "tunnel",
    "vanish": "missing",
    "vanished": "missing",
}

CONTRADICTION_GROUPS = [
    (
        {"open", "unlock", "unseal", "free", "clear"},
        {"close", "shut", "lock", "seal", "bar", "chain"},
    ),
    (
        {"alive", "live"},
        {"dead", "kill", "corpse"},
    ),
    (
        {"legal", "lawful", "license", "official"},
        {"illegal", "illicit", "unlawful", "smuggle"},
    ),
    (
        {"public", "known", "reveal"},
        {"secret", "hidden", "private", "buried"},
    ),
    (
        {"trust", "ally", "friend"},
        {"hostile", "enemy", "distrust"},
    ),
    (
        {"dawn", "morning", "day"},
        {"night", "midnight", "dusk"},
    ),
    (
        {"intact", "whole"},
        {"broken", "destroy", "burn", "ruin"},
    ),
]


@dataclass(frozen=True)
class KindMeta:
    name: str
    directory: Path
    schema: Path
    template: Path


@dataclass(frozen=True)
class AuditFinding:
    severity: str
    scope: str
    code: str
    message: str


@dataclass(frozen=True)
class CheckpointPaths:
    checkpoint: Path
    handoff_markdown: Path
    handoff_json: Path


class ProjectError(RuntimeError):
    """Raised when the project is invalid or missing required records."""


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def now_local() -> datetime:
    return datetime.now().astimezone().replace(microsecond=0)


def now_iso() -> str:
    return now_local().isoformat()


def now_stamp() -> str:
    return now_local().strftime("%Y%m%dT%H%M%S%z")


def slugify(text: str, fallback: str = "entry") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.casefold()).strip("-")
    return slug or fallback


def project_root(root: Path | None = None) -> Path:
    return root or PROJECT_ROOT


def checkpoints_dir(root: Path | None = None) -> Path:
    return project_root(root) / "ops" / "checkpoints"


def handoff_markdown_path(root: Path | None = None) -> Path:
    return project_root(root) / "ops" / "handoff" / "current.md"


def handoff_json_path(root: Path | None = None) -> Path:
    return project_root(root) / "ops" / "handoff" / "current.json"


def load_kind_map(root: Path | None = None) -> dict[str, KindMeta]:
    root = project_root(root)
    raw = load_json(root / "config" / "kinds.json")
    kind_map: dict[str, KindMeta] = {}
    for kind, meta in raw.items():
        kind_map[kind] = KindMeta(
            name=kind,
            directory=root / meta["directory"],
            schema=root / meta["schema"],
            template=root / meta["template"],
        )
    return kind_map


def load_project_config(root: Path | None = None) -> dict[str, Any]:
    root = project_root(root)
    return load_json(root / "config" / "story_project.json")


def iter_records(root: Path | None = None, kind: str | None = None) -> list[tuple[str, Path, dict[str, Any]]]:
    root = project_root(root)
    kind_map = load_kind_map(root)
    if kind and kind not in kind_map:
        raise ProjectError(f"Unknown kind: {kind}")
    selected = [kind] if kind else list(kind_map)
    rows: list[tuple[str, Path, dict[str, Any]]] = []
    for kind_name in selected:
        meta = kind_map[kind_name]
        for path in sorted(meta.directory.glob("*.json")):
            rows.append((kind_name, path, load_json(path)))
    return rows


def build_indexes(root: Path | None = None) -> tuple[dict[str, dict[str, Any]], dict[str, list[str]]]:
    records_by_id: dict[str, dict[str, Any]] = {}
    kinds_by_id: dict[str, list[str]] = {}
    for kind, _path, record in iter_records(root):
        record_id = record.get("id")
        if record_id is None:
            continue
        kinds_by_id.setdefault(record_id, []).append(kind)
        if record_id not in records_by_id:
            records_by_id[record_id] = record
    return records_by_id, kinds_by_id


def get_record(kind: str, record_id: str, root: Path | None = None) -> dict[str, Any]:
    for found_kind, _path, record in iter_records(root, kind=kind):
        if found_kind == kind and record.get("id") == record_id:
            return record
    raise ProjectError(f"Record not found: kind={kind} id={record_id}")


def flatten_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        rows: list[str] = []
        for item in value:
            rows.extend(flatten_strings(item))
        return rows
    if isinstance(value, dict):
        rows = []
        for item in value.values():
            rows.extend(flatten_strings(item))
        return rows
    return []


def validate_type(value: Any, expected: str) -> bool:
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "array":
        return isinstance(value, list)
    if expected == "object":
        return isinstance(value, dict)
    return True


def validate_against_schema(value: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    errors: list[str] = []
    expected_type = schema.get("type")
    if expected_type and not validate_type(value, expected_type):
        return [f"{path}: expected {expected_type}, got {type(value).__name__}"]

    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: expected constant {schema['const']!r}, got {value!r}")

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: expected one of {schema['enum']}, got {value!r}")

    if expected_type == "object":
        required = schema.get("required", [])
        props = schema.get("properties", {})
        for key in required:
            if key not in value:
                errors.append(f"{path}: missing required key {key!r}")
        for key, item in value.items():
            if key in props:
                errors.extend(validate_against_schema(item, props[key], f"{path}.{key}"))
    elif expected_type == "array":
        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(value):
                errors.extend(validate_against_schema(item, item_schema, f"{path}[{index}]"))
    return errors


def resolve_ref(
    records_by_id: dict[str, dict[str, Any]],
    kinds_by_id: dict[str, list[str]],
    target_id: str,
    expected_kinds: set[str] | None = None,
) -> str | None:
    if target_id not in records_by_id:
        return f"unknown id {target_id!r}"
    if expected_kinds and not (expected_kinds & set(kinds_by_id.get(target_id, []))):
        return (
            f"id {target_id!r} exists as {sorted(kinds_by_id.get(target_id, []))} "
            f"but expected one of {sorted(expected_kinds)}"
        )
    return None


def validate_references(root: Path | None = None) -> list[str]:
    errors: list[str] = []
    records_by_id, kinds_by_id = build_indexes(root)
    for record_kind, path, record in iter_records(root):
        record_id = record.get("id", path.stem)

        if path.stem != record_id:
            errors.append(f"{path}: filename stem {path.stem!r} does not match id {record_id!r}")

        def check(target_id: str, label: str, expected: set[str] | None = None) -> None:
            issue = resolve_ref(records_by_id, kinds_by_id, target_id, expected)
            if issue:
                errors.append(f"{path}: {label} -> {issue}")

        if record_kind == "character":
            for index, rel in enumerate(record.get("relationships", [])):
                target = rel.get("target")
                if target:
                    check(target, f"relationships[{index}].target")
        elif record_kind == "location":
            for index, target in enumerate(record.get("linked_factions", [])):
                check(target, f"linked_factions[{index}]", {"faction"})
            for index, target in enumerate(record.get("linked_items", [])):
                check(target, f"linked_items[{index}]", {"item"})
        elif record_kind == "item":
            owner = record.get("owner")
            if owner:
                check(owner, "owner")
        elif record_kind == "idea":
            for index, target in enumerate(record.get("linked_records", [])):
                check(target, f"linked_records[{index}]")
        elif record_kind == "character_state":
            check(record.get("character_id", ""), "character_id", {"character"})
            check(record.get("current_location", ""), "current_location", {"location"})
            updated_at = record.get("updated_at")
            if updated_at:
                check(updated_at, "updated_at", {"scene_state"})
        elif record_kind == "item_state":
            check(record.get("item_id", ""), "item_id", {"item"})
            holder = record.get("current_holder")
            if holder:
                check(holder, "current_holder", {"character"})
            check(record.get("current_location", ""), "current_location", {"location"})
            updated_at = record.get("updated_at")
            if updated_at:
                check(updated_at, "updated_at", {"scene_state"})
        elif record_kind == "scene_state":
            check(record.get("episode", ""), "episode", {"episode"})
            check(record.get("pov_character", ""), "pov_character", {"character"})
            check(record.get("location", ""), "location", {"location"})
            for index, target in enumerate(record.get("present_characters", [])):
                check(target, f"present_characters[{index}]", {"character"})
            for index, target in enumerate(record.get("active_threads", [])):
                check(target, f"active_threads[{index}]", {"plot_thread"})
            for index, target in enumerate(record.get("relevant_events", [])):
                check(target, f"relevant_events[{index}]", {"event"})
            for index, goal in enumerate(record.get("goals", [])):
                actor = goal.get("actor")
                if actor:
                    check(actor, f"goals[{index}].actor", {"character", "faction"})
        elif record_kind == "plot_thread":
            introduced_in = record.get("introduced_in")
            if introduced_in:
                check(introduced_in, "introduced_in", {"episode", "event"})
            for index, target in enumerate(record.get("linked_records", [])):
                check(target, f"linked_records[{index}]")
        elif record_kind == "episode":
            for index, target in enumerate(record.get("scenes", [])):
                check(target, f"scenes[{index}]", {"scene_state"})
            for index, target in enumerate(record.get("payoff_targets", [])):
                check(target, f"payoff_targets[{index}]", {"plot_thread"})
        elif record_kind == "event":
            for index, target in enumerate(record.get("participants", [])):
                check(target, f"participants[{index}]")
        elif record_kind == "world_state":
            updated_at = record.get("updated_at")
            if updated_at:
                check(updated_at, "updated_at", {"scene_state"})
    for record_id, kinds in sorted(kinds_by_id.items()):
        if len(kinds) > 1:
            errors.append(f"duplicate id {record_id!r} appears in multiple kinds: {sorted(kinds)}")
    return errors


def validate_project(root: Path | None = None) -> list[str]:
    root = project_root(root)
    kind_map = load_kind_map(root)
    errors: list[str] = []
    for kind, path, record in iter_records(root):
        schema = load_json(kind_map[kind].schema)
        errors.extend(f"{path}: {message}" for message in validate_against_schema(record, schema))
    errors.extend(validate_references(root))
    return errors


def summarize_record(record: dict[str, Any]) -> str:
    return json.dumps(record, indent=2)


def list_records(kind: str, root: Path | None = None) -> str:
    rows = []
    for _kind, _path, record in iter_records(root, kind=kind):
        rows.append((record.get("id", ""), record.get("name", ""), record.get("summary", "")))
    rows.sort(key=lambda row: row[0])
    return "\n".join(f"{record_id}\t{name}\t{summary}" for record_id, name, summary in rows)


def search_records(term: str, kind: str | None = None, root: Path | None = None) -> str:
    needle = term.casefold()
    rows = []
    for record_kind, path, record in iter_records(root, kind=kind):
        haystack = " ".join(flatten_strings(record)).casefold()
        if needle in haystack:
            rows.append(
                (
                    record_kind,
                    record.get("id", path.stem),
                    record.get("name", ""),
                    record.get("summary", ""),
                )
            )
    rows.sort(key=lambda row: (row[0], row[1]))
    return "\n".join(
        f"{record_kind}\t{record_id}\t{name}\t{summary}"
        for record_kind, record_id, name, summary in rows
    )


def find_character_state(
    character_id: str,
    root: Path | None = None,
    scene_id: str | None = None,
) -> dict[str, Any] | None:
    return latest_subject_state(
        "character_state",
        "character_id",
        character_id,
        root=root,
        scene_id=scene_id,
    )


def find_item_state(
    item_id: str,
    root: Path | None = None,
    scene_id: str | None = None,
) -> dict[str, Any] | None:
    return latest_subject_state(
        "item_state",
        "item_id",
        item_id,
        root=root,
        scene_id=scene_id,
    )


def find_world_state(root: Path | None = None, scene_id: str | None = None) -> dict[str, Any] | None:
    rows = [record for _kind, _path, record in iter_records(root, kind="world_state")]
    snapshot = select_state_snapshot(rows, root=root, scene_id=scene_id)
    if snapshot is not None:
        return snapshot
    if scene_id:
        return None
    return rows[0] if rows else None


def first_record(kind: str, root: Path | None = None) -> dict[str, Any] | None:
    rows = iter_records(root, kind=kind)
    return rows[0][2] if rows else None


def truth_suffix(record: dict[str, Any]) -> str:
    status = record.get("truth_status")
    return f" [{status}]" if status else ""


def normalize_token(token: str) -> str:
    token = token.casefold()
    token = TOKEN_ALIASES.get(token, token)
    for suffix in ("ing", "ed", "es", "s"):
        if len(token) <= len(suffix) + 2 or not token.endswith(suffix):
            continue
        stem = token[: -len(suffix)]
        if len(stem) < 3:
            continue
        token = TOKEN_ALIASES.get(stem, stem)
        break
    return token


def scene_sort_key(scene_or_id: str | dict[str, Any], root: Path | None = None) -> int:
    scene = scene_or_id if isinstance(scene_or_id, dict) else get_record("scene_state", scene_or_id, root)
    return int(scene["sort_key"])


def state_record_sort_key(record: dict[str, Any], root: Path | None = None) -> int | None:
    updated_at = record.get("updated_at")
    if not updated_at:
        return None
    return scene_sort_key(updated_at, root)


def select_state_snapshot(
    rows: list[dict[str, Any]],
    root: Path | None = None,
    scene_id: str | None = None,
) -> dict[str, Any] | None:
    target_key = scene_sort_key(scene_id, root) if scene_id else None
    ranked: list[tuple[int, str, str, dict[str, Any]]] = []
    for record in rows:
        sort_key = state_record_sort_key(record, root)
        if sort_key is None:
            continue
        if target_key is not None and sort_key > target_key:
            continue
        ranked.append((sort_key, record.get("updated_at", ""), record.get("id", ""), record))
    if not ranked:
        return None
    ranked.sort(key=lambda row: (row[0], row[1], row[2]))
    return ranked[-1][3]


def latest_subject_state(
    kind: str,
    subject_field: str,
    subject_id: str,
    root: Path | None = None,
    scene_id: str | None = None,
) -> dict[str, Any] | None:
    rows = [
        record
        for _kind, _path, record in iter_records(root, kind=kind)
        if record.get(subject_field) == subject_id
    ]
    return select_state_snapshot(rows, root=root, scene_id=scene_id)


def bullet_section(title: str, lines: list[str]) -> list[str]:
    section = [title]
    if not lines:
        section.append("- none")
    else:
        section.extend(f"- {line}" for line in lines)
    return section


def unique_strings(values: list[str]) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value and value not in seen:
            seen.add(value)
            rows.append(value)
    return rows


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.casefold())


def content_tokens(text: str) -> set[str]:
    return {
        normalize_token(token)
        for token in tokenize(text)
        if len(token) > 2 and token not in STOPWORDS
    }


def has_meaning_overlap(left: str, right: str, minimum: int = 1) -> bool:
    return len(content_tokens(left) & content_tokens(right)) >= minimum


def record_terms(record: dict[str, Any]) -> list[str]:
    terms = []
    name = record.get("name")
    if name:
        terms.append(name)
    for alias in record.get("aliases", []):
        if alias:
            terms.append(alias)
    return terms


def mentions_term(text: str, term: str) -> bool:
    return re.search(rf"\b{re.escape(term.casefold())}\b", text.casefold()) is not None


def strip_terminal_punctuation(text: str) -> str:
    return text.rstrip(" .!?")


def lower_initial(text: str) -> str:
    cleaned = strip_terminal_punctuation(text)
    if not cleaned:
        return cleaned
    return cleaned[0].lower() + cleaned[1:]


def infinitive_goal(text: str) -> str:
    cleaned = strip_terminal_punctuation(text)
    if not cleaned:
        return cleaned
    parts = cleaned.split(maxsplit=1)
    if parts and parts[0].lower() in {
        "get",
        "keep",
        "find",
        "move",
        "learn",
        "stay",
        "catch",
        "identify",
        "use",
        "abandon",
        "pass",
        "work",
        "force",
        "reach",
    }:
        remainder = f" {parts[1]}" if len(parts) > 1 else ""
        return f"to {parts[0].lower()}{remainder}"
    return cleaned


def polarity_tags(text: str) -> set[tuple[int, int]]:
    tokens = content_tokens(text)
    tags: set[tuple[int, int]] = set()
    for index, (positive, negative) in enumerate(CONTRADICTION_GROUPS):
        if tokens & positive:
            tags.add((index, 1))
        if tokens & negative:
            tags.add((index, -1))
    return tags


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [part.strip() for part in parts if part.strip()]


def dedupe_findings(findings: list[AuditFinding]) -> list[AuditFinding]:
    seen: set[tuple[str, str, str, str]] = set()
    rows: list[AuditFinding] = []
    for finding in findings:
        key = (finding.severity, finding.scope, finding.code, finding.message)
        if key not in seen:
            seen.add(key)
            rows.append(finding)
    return rows


def scene_goal_for_actor(scene: dict[str, Any], actor_id: str) -> list[str]:
    rows = []
    for goal in scene.get("goals", []):
        if goal.get("actor") == actor_id and goal.get("goal"):
            rows.append(goal["goal"])
    return rows


def scene_anchor_ids(packet: dict[str, Any]) -> set[str]:
    scene = packet["scene"]
    location = packet["location"]
    anchors = {
        scene["id"],
        scene["episode"],
        scene["location"],
        scene["pov_character"],
    }
    anchors.update(scene.get("present_characters", []))
    anchors.update(scene.get("active_threads", []))
    anchors.update(scene.get("relevant_events", []))
    anchors.update(location.get("linked_factions", []))
    anchors.update(location.get("linked_items", []))
    for bundle in packet["characters"]:
        state = bundle.get("state")
        if state:
            anchors.update(state.get("inventory", []))
    return anchors


def build_scene_packet(scene_id: str, root: Path | None = None) -> dict[str, Any]:
    root = project_root(root)
    config = load_project_config(root)
    scene = get_record("scene_state", scene_id, root)
    episode = get_record("episode", scene["episode"], root)
    world = first_record("world", root)
    world_state = find_world_state(root, scene_id=scene_id)
    location = get_record("location", scene["location"], root)

    characters: list[dict[str, Any]] = []
    seen_character_ids: list[str] = []
    for character_id in scene.get("present_characters", []):
        if character_id not in seen_character_ids:
            seen_character_ids.append(character_id)
    if scene["pov_character"] not in seen_character_ids:
        seen_character_ids.append(scene["pov_character"])
    for character_id in seen_character_ids:
        canon = get_record("character", character_id, root)
        characters.append(
            {
                "id": character_id,
                "canon": canon,
                "state": find_character_state(character_id, root, scene_id=scene_id),
            }
        )

    factions = [get_record("faction", faction_id, root) for faction_id in location.get("linked_factions", [])]
    location_items = [
        {
            "canon": get_record("item", item_id, root),
            "state": find_item_state(item_id, root, scene_id=scene_id),
        }
        for item_id in location.get("linked_items", [])
    ]
    threads = [get_record("plot_thread", thread_id, root) for thread_id in scene.get("active_threads", [])]
    events = [get_record("event", event_id, root) for event_id in scene.get("relevant_events", [])]

    return {
        "config": config,
        "scene": scene,
        "episode": episode,
        "world": world,
        "world_state": world_state,
        "location": location,
        "characters": characters,
        "factions": factions,
        "location_items": location_items,
        "threads": threads,
        "events": events,
        "pov_state": find_character_state(scene["pov_character"], root, scene_id=scene_id),
    }


def packet_truth_records(packet: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    rows: list[tuple[str, dict[str, Any]]] = []
    if packet["world"]:
        rows.append(("world", packet["world"]))
    rows.append(("location", packet["location"]))
    rows.extend(("character", bundle["canon"]) for bundle in packet["characters"])
    rows.extend(("faction", faction) for faction in packet["factions"])
    rows.extend(("item", bundle["canon"]) for bundle in packet["location_items"])
    deduped: list[tuple[str, dict[str, Any]]] = []
    seen: set[str] = set()
    for label, record in rows:
        record_id = record.get("id")
        if not record_id or record_id in seen:
            continue
        seen.add(record_id)
        deduped.append((label, record))
    return deduped


def build_scene_context(scene_id: str, root: Path | None = None) -> str:
    packet = build_scene_packet(scene_id, root)
    config = packet["config"]
    scene = packet["scene"]
    episode = packet["episode"]
    world = packet["world"]
    world_state = packet["world_state"]
    location = packet["location"]

    lines: list[str] = []
    lines.append(f"# Scene Context: {scene['name']}")
    lines.append("")
    lines.append("## Project")
    lines.append(f"- Project: {config['project_name']}")
    lines.append(f"- Premise: {config['premise']}")
    lines.append(f"- Genre: {config['genre']}")
    lines.append(f"- Tone: {', '.join(config.get('tone', []))}")
    lines.extend(bullet_section("## Authoring Rules", config.get("authoring_rules", [])))

    if world:
        lines.append("")
        lines.append("## World")
        lines.append(f"- {world['name']}{truth_suffix(world)}: {world['summary']}")
        lines.extend(f"- premise: {value}" for value in world.get("premises", []))
        lines.extend(f"- rule: {value}" for value in world.get("rules", []))
        lines.extend(f"- taboo: {value}" for value in world.get("taboos", []))

    if world_state:
        lines.append("")
        lines.append("## Current World State")
        lines.append(f"- Date: {world_state['calendar_date']}")
        lines.append(f"- Summary: {world_state['summary']}")
        lines.extend(f"- crisis: {value}" for value in world_state.get("active_crises", []))
        lines.extend(f"- legal pressure: {value}" for value in world_state.get("legal_pressure", []))
        lines.extend(
            f"- environmental note: {value}" for value in world_state.get("environmental_notes", [])
        )
        lines.extend(
            f"- rumor in circulation: {value}"
            for value in world_state.get("rumors_in_circulation", [])
        )

    lines.append("")
    lines.append("## Episode")
    lines.append(f"- {episode['name']}: {episode['summary']}")
    lines.append(f"- Purpose: {episode['purpose']}")
    lines.extend(f"- target change: {value}" for value in episode.get("target_changes", []))

    lines.append("")
    lines.append("## Scene")
    lines.append(f"- Summary: {scene['summary']}")
    lines.append(f"- Sort Key: {scene['sort_key']}")
    if scene.get("calendar_date"):
        lines.append(f"- Date: {scene['calendar_date']}")
    lines.append(f"- POV: {scene['pov_character']}")
    lines.append(f"- Location: {scene['location']}")
    lines.extend(f"- tension: {value}" for value in scene.get("tensions", []))
    lines.extend(f"- fact in play: {value}" for value in scene.get("facts_in_play", []))
    lines.extend(f"- unknown: {value}" for value in scene.get("unknowns", []))
    lines.extend(f"- exit condition: {value}" for value in scene.get("exit_conditions", []))
    for goal in scene.get("goals", []):
        lines.append(f"- goal: {goal['actor']} -> {goal['goal']}")

    lines.append("")
    lines.append("## Location")
    lines.append(f"- {location['name']}{truth_suffix(location)}: {location['summary']}")
    lines.extend(f"- sensory cue: {value}" for value in location.get("sensory_cues", []))
    lines.extend(f"- constraint: {value}" for value in location.get("constraints", []))

    if packet["factions"]:
        lines.append("")
        lines.append("## Linked Factions")
        for faction in packet["factions"]:
            lines.append(f"- {faction['name']}{truth_suffix(faction)}: {faction['summary']}")
            lines.extend(f"  agenda: {value}" for value in faction.get("agenda", []))

    if packet["location_items"]:
        lines.append("")
        lines.append("## Linked Items")
        for bundle in packet["location_items"]:
            item = bundle["canon"]
            item_state = bundle["state"]
            lines.append(f"- {item['name']}{truth_suffix(item)}: {item['summary']}")
            lines.append(f"  significance: {item['significance']}")
            lines.extend(f"  limit: {value}" for value in item.get("limits", []))
            if item_state:
                if item_state.get("current_holder"):
                    lines.append(f"  current holder: {item_state['current_holder']}")
                lines.append(f"  current location: {item_state['current_location']}")
                lines.append(f"  status: {item_state['status']}")
                lines.append(f"  visibility: {item_state['visibility']}")

    lines.append("")
    lines.append("## Characters")
    for bundle in packet["characters"]:
        record = bundle["canon"]
        state = bundle["state"]
        lines.append(f"- {record['name']}{truth_suffix(record)} ({record['id']})")
        lines.append(f"  canon: {record['summary']}")
        lines.append(f"  role: {record['role']}")
        lines.extend(f"  goal: {value}" for value in record.get("goals", []))
        if state:
            lines.append(f"  current location: {state['current_location']}")
            lines.append(f"  emotional state: {state['emotional_state']}")
            lines.append(f"  current goal: {state['current_goal']}")
            lines.append(f"  obstacle: {state['current_obstacle']}")
            lines.extend(f"  secret carried: {value}" for value in state.get("secrets_carried", []))
            lines.extend(f"  known fact: {value}" for value in state.get("known_facts", []))
            lines.extend(f"  inventory: {value}" for value in state.get("inventory", []))

    lines.append("")
    lines.append("## Active Plot Threads")
    for thread in packet["threads"]:
        lines.append(f"- {thread['name']} [{thread['status']}]")
        lines.append(f"  question: {thread['question']}")
        lines.append(f"  summary: {thread['summary']}")
        lines.extend(f"  stake: {value}" for value in thread.get("stakes", []))
        planned = thread.get("planned_reveal")
        if planned:
            lines.append(f"  planned reveal: {planned}")

    lines.append("")
    lines.append("## Timeline Signals")
    for event in packet["events"]:
        lines.append(f"- {event['date_label']} | {event['name']}")
        lines.append(f"  summary: {event['summary']}")
        lines.extend(f"  consequence: {value}" for value in event.get("consequences", []))

    return "\n".join(lines) + "\n"


def build_continuity_watchpoints(packet: dict[str, Any]) -> list[str]:
    scene = packet["scene"]
    location = packet["location"]
    world_state = packet["world_state"]
    pov_bundle = next(bundle for bundle in packet["characters"] if bundle["id"] == scene["pov_character"])
    pov = pov_bundle["canon"]
    pov_state = pov_bundle["state"]

    watchpoints: list[str] = []
    watchpoints.append(f"POV is {pov['name']}; keep the voice {pov['voice']['tone']}.")
    if pov_state:
        watchpoints.append(f"{pov['name']} must want {strip_terminal_punctuation(pov_state['current_goal'])}.")
        watchpoints.append(f"The active obstacle is {strip_terminal_punctuation(pov_state['current_obstacle'])}.")
    if world_state and world_state.get("active_crises"):
        watchpoints.append(f"World pressure: {world_state['active_crises'][0]}")
    if location.get("sensory_cues"):
        watchpoints.append(f"Open on the feel of {location['sensory_cues'][0]}")
    if location.get("constraints"):
        watchpoints.append(f"Respect location constraint: {location['constraints'][0]}")
    if scene.get("facts_in_play"):
        watchpoints.append(f"Do not lose this fact: {strip_terminal_punctuation(scene['facts_in_play'][0])}.")
    if packet["threads"]:
        watchpoints.append(f"Thread pressure: {strip_terminal_punctuation(packet['threads'][0]['question'])}?")
    if scene.get("exit_conditions"):
        watchpoints.append(f"Land the scene on one exit vector: {strip_terminal_punctuation(scene['exit_conditions'][0])}.")
    return watchpoints


def build_scene_beats(packet: dict[str, Any]) -> list[str]:
    scene = packet["scene"]
    location = packet["location"]
    world_state = packet["world_state"]
    pov_bundle = next(bundle for bundle in packet["characters"] if bundle["id"] == scene["pov_character"])
    pov = pov_bundle["canon"]
    pov_state = pov_bundle["state"]
    other_characters = [bundle["canon"] for bundle in packet["characters"] if bundle["id"] != scene["pov_character"]]
    opposition = other_characters[0] if other_characters else None
    opening_cue = location.get("sensory_cues", ["the pressure in the air"])[0]
    world_pressure = ""
    if world_state and world_state.get("active_crises"):
        world_pressure = world_state["active_crises"][0]
    first_tension = scene.get("tensions", ["The pressure should appear immediately."])[0]
    first_unknown = scene.get("unknowns", ["Something important remains unresolved."])[0]
    exit_vector = scene.get("exit_conditions", ["The scene ends on a costly choice."])[0]

    beats = [
        f"Opening image: establish {location['name']} through {opening_cue} while {pov['name']} enters already carrying pressure.",
        f"Contact beat: reveal that {first_tension}",
    ]
    if opposition:
        beats.append(
            f"Counterpressure: let {opposition['name']} pursue "
            f"{strip_terminal_punctuation(scene_goal_for_actor(scene, opposition['id'])[0])} "
            f"while {pov['name']} tries to keep "
            f"{strip_terminal_punctuation(pov_state['current_goal']) if pov_state else 'control'}."
        )
    if world_pressure:
        beats.append(f"External pressure: fold in the wider crisis that {world_pressure}")
    beats.append(f"Decision turn: force the POV to confront {strip_terminal_punctuation(first_unknown)}")
    beats.append(f"Exit: choose or threaten this outcome -> {strip_terminal_punctuation(exit_vector)}")
    return beats


def build_dialogue_pressure(packet: dict[str, Any]) -> list[str]:
    scene = packet["scene"]
    bundles = packet["characters"]
    lines: list[str] = []
    for bundle in bundles[:2]:
        canon = bundle["canon"]
        state = bundle["state"]
        taboo = canon["voice"]["taboos"][0] if canon["voice"].get("taboos") else "stay inside the character's restraint"
        current_goal = state["current_goal"] if state else canon["goals"][0]
        lines.append(
            f"{canon['name']}: speaks in a {canon['voice']['tone']} register, pushes toward '{current_goal}', "
            f"and should avoid '{taboo}'."
        )
    if len(bundles) >= 2:
        left = bundles[0]["canon"]["name"]
        right = bundles[1]["canon"]["name"]
        lines.append(f"Let {left} and {right} trade information unevenly; neither should say the whole truth first.")
    return lines


def build_opening_seed(packet: dict[str, Any]) -> str:
    scene = packet["scene"]
    location = packet["location"]
    pov_bundle = next(bundle for bundle in packet["characters"] if bundle["id"] == scene["pov_character"])
    pov = pov_bundle["canon"]
    pov_state = pov_bundle["state"]
    other_characters = [bundle["canon"] for bundle in packet["characters"] if bundle["id"] != scene["pov_character"]]
    opposition = other_characters[0] if other_characters else None
    cue_one = location.get("sensory_cues", ["damp air"])[0]
    cue_two = location.get("sensory_cues", ["crowded noise"])[1 if len(location.get("sensory_cues", [])) > 1 else 0]
    obstacle = pov_state["current_obstacle"] if pov_state else scene.get("tensions", ["pressure arrived early"])[0]
    first_unknown = scene.get("unknowns", ["the truth has not surfaced yet"])[0]

    lines = [
        f"{cue_one.capitalize()} turned {location['name']} into a place that felt cleaner than it was, "
        f"and {pov['name']} stepped into it already measuring which lies she could afford.",
        f"She wanted {infinitive_goal(pov_state['current_goal']) if pov_state else scene['summary'].casefold()}, "
        f"but {strip_terminal_punctuation(obstacle)}.",
    ]
    if opposition:
        lines.append(
            f"Then {opposition['name']} entered the frame of the moment, and the routine at the gate stopped "
            f"looking like routine at all."
        )
    lines.append(
        f"The opening paragraph should make the reader feel that {lower_initial(first_unknown)}."
    )
    return " ".join(lines)


def build_prose_seed(packet: dict[str, Any]) -> str:
    scene = packet["scene"]
    location = packet["location"]
    world_state = packet["world_state"]
    pov_bundle = next(bundle for bundle in packet["characters"] if bundle["id"] == scene["pov_character"])
    pov = pov_bundle["canon"]
    pov_state = pov_bundle["state"]
    other_characters = [bundle["canon"] for bundle in packet["characters"] if bundle["id"] != scene["pov_character"]]
    opposition = other_characters[0] if other_characters else None
    cue_one = location.get("sensory_cues", ["damp air"])[0]
    cue_two = location.get("sensory_cues", ["clerks under pressure"])[1 if len(location.get("sensory_cues", [])) > 1 else 0]
    world_pressure = world_state.get("active_crises", [scene["summary"]])[0] if world_state else scene["summary"]
    tension = scene.get("tensions", ["the pressure was obvious"])[0]
    exit_vector = scene.get("exit_conditions", ["someone makes the costly move"])[0]

    paragraph_one = (
        f"{cue_one.capitalize()} hung over {location['name']}, and {cue_two} made the morning sound busier than it felt. "
        f"{pov['name']} kept moving because stopping would look like fear, and fear was the one thing a gate full of clerks "
        f"and inspectors could smell faster than bad wax."
    )

    paragraph_two = (
        f"She needed {infinitive_goal(pov_state['current_goal']) if pov_state else scene['summary'].lower()}, "
        f"but {lower_initial(world_pressure)} had stripped the checkpoint of every lazy habit it used to have. "
        f"{strip_terminal_punctuation(tension)}."
    )

    if opposition:
        paragraph_three = (
            f"Then {opposition['name']} made the moment personal. He was not just another uniform in bad weather; "
            f"he was the person most likely to notice the old pattern on her satchel and most likely to understand why she "
            f"could not let him notice. If the scene breaks cleanly, it should break toward this possibility: "
            f"{strip_terminal_punctuation(exit_vector)}."
        )
    else:
        paragraph_three = (
            f"The scene should keep tightening until {pov['name']} is forced into a choice that feels narrower than the street. "
            f"The most useful exit vector is this: {exit_vector.lower()}."
        )

    return "\n\n".join([paragraph_one, paragraph_two, paragraph_three])


def render_scene_draft(scene_id: str, mode: str = "scaffold", root: Path | None = None) -> str:
    packet = build_scene_packet(scene_id, root)
    scene = packet["scene"]
    if mode not in {"scaffold", "beats", "prose"}:
        raise ProjectError(f"Unknown draft mode: {mode}")

    if mode == "beats":
        lines = [f"# Beat Plan: {scene['name']}", ""]
        lines.extend(f"{index}. {beat}" for index, beat in enumerate(build_scene_beats(packet), start=1))
        return "\n".join(lines) + "\n"

    if mode == "prose":
        return build_prose_seed(packet) + "\n"

    findings = audit_scene_semantics(scene_id, root)
    lines: list[str] = [f"# Draft Kit: {scene['name']}", ""]
    lines.append("## Intent")
    lines.append(f"- {scene['summary']}")
    lines.append("")
    lines.extend(bullet_section("## Continuity Watchpoints", build_continuity_watchpoints(packet)))
    lines.append("")
    lines.append("## Beat Plan")
    lines.extend(f"{index}. {beat}" for index, beat in enumerate(build_scene_beats(packet), start=1))
    lines.append("")
    lines.extend(bullet_section("## Dialogue Pressure", build_dialogue_pressure(packet)))
    lines.append("")
    lines.append("## Opening Paragraph Seed")
    lines.append(build_opening_seed(packet))
    lines.append("")
    lines.append("## Prose Starter")
    lines.append(build_prose_seed(packet))
    lines.append("")
    lines.append("## Current Audit")
    if findings:
        lines.extend(f"- [{finding.severity}] {finding.message}" for finding in findings)
    else:
        lines.append("- No semantic findings.")
    return "\n".join(lines) + "\n"


def contradiction_between(source_text: str, sentence: str) -> bool:
    overlap = content_tokens(source_text) & content_tokens(sentence)
    if len(overlap) < 2:
        return False
    source_tags = polarity_tags(source_text)
    sentence_tags = polarity_tags(sentence)
    for group, side in source_tags:
        if (group, -side) in sentence_tags:
            return True
    source_negative = any(token in {"no", "not", "never", "without"} for token in tokenize(source_text))
    sentence_negative = any(token in {"no", "not", "never", "without"} for token in tokenize(sentence))
    return source_negative != sentence_negative and len(overlap) >= 3


def semantic_sources_for_scene(packet: dict[str, Any]) -> list[tuple[str, str]]:
    scene = packet["scene"]
    location = packet["location"]
    world_state = packet["world_state"]
    rows: list[tuple[str, str]] = []
    for fact in scene.get("facts_in_play", []):
        rows.append(("scene fact", fact))
    for constraint in location.get("constraints", []):
        rows.append(("location constraint", constraint))
    if world_state:
        for crisis in world_state.get("active_crises", []):
            rows.append(("world crisis", crisis))
        for pressure in world_state.get("legal_pressure", []):
            rows.append(("legal pressure", pressure))
    for bundle in packet["characters"]:
        state = bundle["state"]
        if state:
            rows.append((f"{bundle['canon']['name']} obstacle", state["current_obstacle"]))
            rows.append((f"{bundle['canon']['name']} current goal", state["current_goal"]))
    return rows


def audit_scene_draft_text(scene_id: str, draft_text: str, root: Path | None = None) -> list[AuditFinding]:
    packet = build_scene_packet(scene_id, root)
    scene = packet["scene"]
    findings: list[AuditFinding] = []
    draft_lower = draft_text.casefold()

    present_ids = {bundle["id"] for bundle in packet["characters"]}
    for _kind, _path, record in iter_records(root, kind="character"):
        if record["id"] in present_ids:
            continue
        for term in record_terms(record):
            if mentions_term(draft_lower, term):
                findings.append(
                    AuditFinding(
                        severity="WARNING",
                        scope=scene_id,
                        code="draft-offscene-character",
                        message=f"Draft mentions off-scene character '{term}' who is not listed in present_characters.",
                    )
                )
                break

    for _kind, _path, record in iter_records(root, kind="location"):
        if record["id"] == scene["location"]:
            continue
        if mentions_term(draft_lower, record["name"]):
            findings.append(
                AuditFinding(
                    severity="WARNING",
                    scope=scene_id,
                    code="draft-location-drift",
                    message=f"Draft mentions location '{record['name']}' even though the active scene location is '{packet['location']['name']}'.",
                )
            )

    for label, source_text in semantic_sources_for_scene(packet):
        for sentence in split_sentences(draft_text):
            if contradiction_between(source_text, sentence):
                findings.append(
                    AuditFinding(
                        severity="WARNING",
                        scope=scene_id,
                        code="draft-contradiction",
                        message=f"Draft sentence may contradict the {label}: '{source_text}'",
                    )
                )

    return dedupe_findings(findings)


def audit_scene_semantics(scene_id: str, root: Path | None = None) -> list[AuditFinding]:
    packet = build_scene_packet(scene_id, root)
    scene = packet["scene"]
    world_state = packet["world_state"]
    findings: list[AuditFinding] = []
    listed_present_ids = set(scene.get("present_characters", []))

    if scene["pov_character"] not in listed_present_ids:
        findings.append(
            AuditFinding(
                severity="ERROR",
                scope=scene_id,
                code="pov-missing",
                message=f"POV character '{scene['pov_character']}' is not present in the scene roster.",
            )
        )

    for label, record in packet_truth_records(packet):
        truth_status = record.get("truth_status")
        if truth_status == "meta":
            findings.append(
                AuditFinding(
                    severity="WARNING",
                    scope=scene_id,
                    code="meta-record-in-scene",
                    message=(
                        f"Scene '{scene_id}' pulls {label} '{record['id']}' from a meta record. "
                        "Meta records should not drive in-story continuity."
                    ),
                )
            )
        elif truth_status in {"provisional", "rumor"}:
            findings.append(
                AuditFinding(
                    severity="NOTE",
                    scope=scene_id,
                    code="uncertain-record-in-scene",
                    message=(
                        f"Scene '{scene_id}' relies on {truth_status} {label} '{record['id']}'. "
                        "Keep that uncertainty explicit in context or prose."
                    ),
                )
            )

    for bundle in packet["characters"]:
        canon = bundle["canon"]
        state = bundle["state"]
        if not state:
            findings.append(
                AuditFinding(
                    severity="WARNING",
                    scope=scene_id,
                    code="missing-character-state",
                    message=f"Character '{canon['id']}' is in the scene but has no current state record.",
                )
            )
            continue

        if state["current_location"] != scene["location"]:
            findings.append(
                AuditFinding(
                    severity="ERROR",
                    scope=scene_id,
                    code="character-location-mismatch",
                    message=(
                        f"Character '{canon['id']}' is present in scene '{scene_id}' at '{scene['location']}' "
                        f"but current_state says '{state['current_location']}'."
                    ),
                )
            )

        actor_goals = scene_goal_for_actor(scene, canon["id"])
        if actor_goals and not any(has_meaning_overlap(goal, state["current_goal"]) for goal in actor_goals):
            findings.append(
                AuditFinding(
                    severity="WARNING",
                    scope=scene_id,
                    code="goal-drift",
                    message=(
                        f"Scene goal for '{canon['id']}' does not line up clearly with the current_state goal. "
                        "Confirm the shift is intentional."
                    ),
                )
            )

        if canon.get("goals") and not any(has_meaning_overlap(state["current_goal"], goal) for goal in canon["goals"]):
            findings.append(
                AuditFinding(
                    severity="NOTE",
                    scope=scene_id,
                    code="canon-goal-drift",
                    message=(
                        f"Current goal for '{canon['id']}' has little lexical overlap with canon goals. "
                        "This may be fine, but it usually deserves an explicit transition."
                    ),
                )
            )

    anchors = scene_anchor_ids(packet)
    scene_pressure_lines = (
        scene.get("tensions", [])
        + scene.get("facts_in_play", [])
        + scene.get("unknowns", [])
        + (world_state.get("active_crises", []) if world_state else [])
    )
    scene_pressure_text = " ".join(scene_pressure_lines)

    for thread in packet["threads"]:
        if not (set(thread.get("linked_records", [])) & anchors):
            findings.append(
                AuditFinding(
                    severity="WARNING",
                    scope=scene_id,
                    code="thread-ungrounded",
                    message=f"Active plot thread '{thread['id']}' is not grounded in any current scene entity or location anchor.",
                )
            )

        thread_text = " ".join([thread["question"], thread["summary"], *thread.get("stakes", [])])
        if not has_meaning_overlap(thread_text, scene_pressure_text):
            findings.append(
                AuditFinding(
                    severity="WARNING",
                    scope=scene_id,
                    code="thread-pressure-missing",
                    message=f"Active plot thread '{thread['id']}' is not clearly expressed in tensions, facts_in_play, or unknowns.",
                )
            )

    for event in packet["events"]:
        consequence_text = " ".join(event.get("consequences", []))
        if (
            consequence_text
            and "history" not in event.get("tags", [])
            and "backstory" not in event.get("tags", [])
            and not has_meaning_overlap(consequence_text, scene_pressure_text)
        ):
            findings.append(
                AuditFinding(
                    severity="NOTE",
                    scope=scene_id,
                    code="event-pressure-weak",
                    message=f"Relevant event '{event['id']}' is referenced but its consequences do not visibly pressure the scene.",
                    )
                )

    for item_bundle in packet["location_items"]:
        item = item_bundle["canon"]
        item_state = item_bundle["state"]
        if item_state and item_state["current_location"] != scene["location"]:
            findings.append(
                AuditFinding(
                    severity="NOTE",
                    scope=scene_id,
                    code="linked-item-offsite",
                    message=(
                        f"Linked item '{item['id']}' is canonically tied to '{scene['location']}' "
                        f"but its latest tracked location is '{item_state['current_location']}'."
                    ),
                )
            )

    pov_state = packet["pov_state"]
    if pov_state:
        known_text = " ".join(pov_state.get("known_facts", []))
        for unknown in scene.get("unknowns", []):
            if has_meaning_overlap(unknown, known_text, minimum=2):
                findings.append(
                    AuditFinding(
                        severity="NOTE",
                        scope=scene_id,
                        code="unknown-already-known",
                        message=f"Scene unknown '{unknown}' overlaps heavily with POV known_facts. Check whether it is still truly unknown in scene.",
                    )
                )

    return dedupe_findings(findings)


def audit_project_semantics(root: Path | None = None) -> list[AuditFinding]:
    root = project_root(root)
    findings: list[AuditFinding] = []
    scene_ids = [record["id"] for _kind, _path, record in iter_records(root, kind="scene_state")]

    for scene_id in scene_ids:
        findings.extend(audit_scene_semantics(scene_id, root))

    active_thread_ids: set[str] = set()
    for _kind, _path, scene in iter_records(root, kind="scene_state"):
        active_thread_ids.update(scene.get("active_threads", []))

    for _kind, _path, thread in iter_records(root, kind="plot_thread"):
        if thread["status"] in {"open", "advancing"} and thread["id"] not in active_thread_ids:
            findings.append(
                AuditFinding(
                    severity="WARNING",
                    scope=thread["id"],
                    code="unseen-open-thread",
                    message=f"Thread '{thread['id']}' is still open but no current scene references it.",
                )
            )

    for _kind, _path, item in iter_records(root, kind="item"):
        owner = item.get("owner")
        item_state = find_item_state(item["id"], root=root)
        if not owner:
            if not item_state:
                continue
        if owner:
            owner_state = find_character_state(owner, root)
            if owner_state and item["id"] not in owner_state.get("inventory", []):
                findings.append(
                    AuditFinding(
                        severity="WARNING",
                        scope=item["id"],
                        code="owner-inventory-mismatch",
                        message=f"Item '{item['id']}' names owner '{owner}' but is absent from that character's inventory.",
                    )
                )

        if item_state and owner and item_state.get("current_holder") and item_state["current_holder"] != owner:
            findings.append(
                AuditFinding(
                    severity="WARNING",
                    scope=item["id"],
                    code="owner-holder-mismatch",
                    message=(
                        f"Item '{item['id']}' names owner '{owner}' but latest item_state "
                        f"lists holder '{item_state['current_holder']}'."
                    ),
                )
            )

        if item_state and item_state.get("current_holder"):
            holder = item_state["current_holder"]
            holder_state = find_character_state(holder, root)
            if holder_state and item["id"] not in holder_state.get("inventory", []):
                findings.append(
                    AuditFinding(
                        severity="WARNING",
                        scope=item["id"],
                        code="item-holder-inventory-mismatch",
                        message=(
                            f"Item '{item['id']}' is tracked on holder '{holder}' but that holder's inventory "
                            "does not include the item."
                        ),
                    )
                )
            if holder_state and item_state["current_location"] != holder_state["current_location"]:
                findings.append(
                    AuditFinding(
                        severity="WARNING",
                        scope=item["id"],
                        code="item-location-mismatch",
                        message=(
                            f"Item '{item['id']}' is tracked at '{item_state['current_location']}' while "
                            f"holder '{holder}' is at '{holder_state['current_location']}'."
                        ),
                    )
                )

    known_item_ids = {record["id"] for _kind, _path, record in iter_records(root, kind="item")}
    for _kind, _path, character_state in iter_records(root, kind="character_state"):
        for inventory_item in character_state.get("inventory", []):
            if inventory_item not in known_item_ids:
                continue
            item_state = find_item_state(
                inventory_item,
                root=root,
                scene_id=character_state.get("updated_at"),
            )
            if not item_state:
                findings.append(
                    AuditFinding(
                        severity="NOTE",
                        scope=character_state["id"],
                        code="inventory-item-missing-state",
                        message=(
                            f"Character state '{character_state['id']}' carries canonical item '{inventory_item}' "
                            "but no item_state snapshot is available at that scene."
                        ),
                    )
                )

    for _kind, _path, episode in iter_records(root, kind="episode"):
        for scene_id in episode.get("scenes", []):
            scene = get_record("scene_state", scene_id, root)
            if scene["episode"] != episode["id"]:
                findings.append(
                    AuditFinding(
                        severity="ERROR",
                        scope=episode["id"],
                        code="episode-scene-mismatch",
                        message=f"Episode '{episode['id']}' lists scene '{scene_id}', but that scene points at episode '{scene['episode']}'.",
                    )
                )
        scene_sort_keys = [get_record("scene_state", scene_id, root)["sort_key"] for scene_id in episode.get("scenes", [])]
        if scene_sort_keys != sorted(scene_sort_keys):
            findings.append(
                AuditFinding(
                    severity="ERROR",
                    scope=episode["id"],
                    code="episode-scene-order",
                    message=(
                        f"Episode '{episode['id']}' lists scenes out of sort_key order. "
                        "Keep episode scene order aligned with chronology."
                    ),
                )
            )

    snapshot_seen: dict[tuple[str, str, str], str] = {}
    for kind_name, subject_field, subject_label in (
        ("character_state", "character_id", "character"),
        ("item_state", "item_id", "item"),
    ):
        for _kind, _path, record in iter_records(root, kind=kind_name):
            key = (kind_name, record.get(subject_field, ""), record.get("updated_at", ""))
            if key in snapshot_seen:
                findings.append(
                    AuditFinding(
                        severity="ERROR",
                        scope=record.get(subject_field, ""),
                        code="duplicate-state-snapshot",
                        message=(
                            f"Multiple {subject_label} state snapshots exist for '{record.get(subject_field, '')}' "
                            f"at scene '{record.get('updated_at', '')}'."
                        ),
                    )
                )
            else:
                snapshot_seen[key] = record.get("id", "")

    world_snapshot_seen: dict[str, str] = {}
    for _kind, _path, record in iter_records(root, kind="world_state"):
        updated_at = record.get("updated_at", "")
        if updated_at in world_snapshot_seen:
            findings.append(
                AuditFinding(
                    severity="ERROR",
                    scope=record["id"],
                    code="duplicate-world-state-snapshot",
                    message=f"Multiple world_state snapshots point at scene '{updated_at}'.",
                )
            )
        else:
            world_snapshot_seen[updated_at] = record["id"]

    return dedupe_findings(findings)


def render_findings(title: str, findings: list[AuditFinding]) -> str:
    findings = dedupe_findings(findings)
    lines = [title, ""]
    if not findings:
        lines.append("No semantic findings.")
        return "\n".join(lines) + "\n"

    counts = {
        "ERROR": sum(1 for finding in findings if finding.severity == "ERROR"),
        "WARNING": sum(1 for finding in findings if finding.severity == "WARNING"),
        "NOTE": sum(1 for finding in findings if finding.severity == "NOTE"),
    }
    lines.append(
        f"Summary: {counts['ERROR']} errors, {counts['WARNING']} warnings, {counts['NOTE']} notes."
    )
    for severity in ("ERROR", "WARNING", "NOTE"):
        bucket = [finding for finding in findings if finding.severity == severity]
        if not bucket:
            continue
        lines.append("")
        lines.append(f"## {severity.title()}s")
        lines.extend(f"- [{finding.code}] {finding.message}" for finding in bucket)
    return "\n".join(lines) + "\n"


def render_audit(scene_id: str | None = None, draft_path: Path | None = None, root: Path | None = None) -> str:
    root = project_root(root)
    if scene_id:
        findings = audit_scene_semantics(scene_id, root)
        if draft_path:
            findings.extend(audit_scene_draft_text(scene_id, draft_path.read_text(encoding="utf-8"), root))
        label = f"# Semantic Audit: {scene_id}"
        if draft_path:
            label = f"{label} ({draft_path.name})"
        return render_findings(label, findings)
    return render_findings("# Semantic Audit: project", audit_project_semantics(root))


def validate_record_ids(record_ids: list[str], root: Path | None = None, expected_kind: str | None = None) -> None:
    root = project_root(root)
    records_by_id, kinds_by_id = build_indexes(root)
    for record_id in record_ids:
        if record_id not in records_by_id:
            raise ProjectError(f"Unknown record id: {record_id}")
        if expected_kind and expected_kind not in kinds_by_id.get(record_id, []):
            raise ProjectError(
                f"Record id {record_id!r} exists as {sorted(kinds_by_id.get(record_id, []))}, expected {expected_kind!r}"
            )


def load_checkpoint_rows(root: Path | None = None) -> list[tuple[Path, dict[str, Any]]]:
    rows: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(checkpoints_dir(root).glob("*.json"), reverse=True):
        rows.append((path, load_json(path)))
    return rows


def active_idea_records(root: Path | None = None) -> list[dict[str, Any]]:
    records = [record for _kind, _path, record in iter_records(root, kind="idea")]
    records = [record for record in records if record.get("status") in {"seed", "exploring", "parked"}]
    return sorted(records, key=lambda record: record.get("last_touched", ""), reverse=True)


def build_handoff_snapshot(root: Path | None = None) -> dict[str, Any]:
    root = project_root(root)
    config = load_project_config(root)
    checkpoint_rows = load_checkpoint_rows(root)
    latest_checkpoint = checkpoint_rows[0][1] if checkpoint_rows else None
    scene = None
    if latest_checkpoint and latest_checkpoint.get("scene_id"):
        scene = get_record("scene_state", latest_checkpoint["scene_id"], root)

    all_ideas = active_idea_records(root)
    idea_lookup = {record["id"]: record for record in all_ideas}
    highlighted_ids = latest_checkpoint.get("idea_ids", []) if latest_checkpoint else []
    highlighted_ideas = [idea_lookup[idea_id] for idea_id in highlighted_ids if idea_id in idea_lookup]
    extra_ideas = [record for record in all_ideas if record["id"] not in {idea["id"] for idea in highlighted_ideas}]
    ideas = highlighted_ideas + extra_ideas[: max(0, 5 - len(highlighted_ideas))]

    recent_decisions: list[str] = []
    for _path, checkpoint in checkpoint_rows[:3]:
        recent_decisions.extend(checkpoint.get("decisions", []))

    touched_records = latest_checkpoint.get("touched_records", []) if latest_checkpoint else []
    artifacts = latest_checkpoint.get("artifacts", []) if latest_checkpoint else []
    open_questions = latest_checkpoint.get("open_questions", []) if latest_checkpoint else []
    pending_actions = latest_checkpoint.get("pending_actions", []) if latest_checkpoint else []

    return {
        "generated_at": now_iso(),
        "project_name": config["project_name"],
        "premise": config["premise"],
        "latest_checkpoint": latest_checkpoint,
        "scene": scene,
        "recent_decisions": unique_strings(recent_decisions),
        "pending_actions": pending_actions,
        "open_questions": open_questions,
        "touched_records": touched_records,
        "artifacts": artifacts,
        "ideas": ideas,
        "recent_checkpoint_ids": [payload["id"] for _path, payload in checkpoint_rows[:5]],
    }


def build_quality_gate(root: Path | None = None) -> dict[str, int]:
    validation_errors = validate_project(root)
    findings = audit_project_semantics(root)
    return {
        "validation_errors": len(validation_errors),
        "semantic_errors": sum(1 for finding in findings if finding.severity == "ERROR"),
        "semantic_warnings": sum(1 for finding in findings if finding.severity == "WARNING"),
        "semantic_notes": sum(1 for finding in findings if finding.severity == "NOTE"),
    }


def enforce_checkpoint_gate(root: Path | None = None, allow_findings: bool = False) -> dict[str, int]:
    quality_gate = build_quality_gate(root)
    if allow_findings:
        return quality_gate

    validation_errors = validate_project(root)
    if validation_errors:
        preview = "\n".join(f"- {message}" for message in validation_errors[:5])
        raise ProjectError(f"Cannot checkpoint while validation errors remain:\n{preview}")

    error_findings = [
        finding.message
        for finding in audit_project_semantics(root)
        if finding.severity == "ERROR"
    ]
    if error_findings:
        preview = "\n".join(f"- {message}" for message in error_findings[:5])
        raise ProjectError(f"Cannot checkpoint while semantic errors remain:\n{preview}")

    return quality_gate


def render_handoff_snapshot(snapshot: dict[str, Any]) -> str:
    lines = ["# Current Handoff", ""]
    lines.append(f"- Generated: {snapshot['generated_at']}")
    lines.append(f"- Project: {snapshot['project_name']}")
    lines.append(f"- Premise: {snapshot['premise']}")

    latest_checkpoint = snapshot["latest_checkpoint"]
    if latest_checkpoint:
        lines.append(f"- Latest checkpoint: {latest_checkpoint['id']}")
        lines.append(f"- Status: {latest_checkpoint['status']}")
        lines.append(f"- Summary: {latest_checkpoint['summary']}")
        quality_gate = latest_checkpoint.get("quality_gate")
        if quality_gate:
            lines.append(
                "- Quality gate: "
                f"{quality_gate['validation_errors']} validation, "
                f"{quality_gate['semantic_errors']} semantic errors, "
                f"{quality_gate['semantic_warnings']} warnings, "
                f"{quality_gate['semantic_notes']} notes"
            )
    else:
        lines.append("- Latest checkpoint: none yet")

    scene = snapshot["scene"]
    if scene:
        lines.append("")
        lines.append("## Active Scene")
        lines.append(f"- {scene['id']}: {scene['name']}")
        lines.append(f"- Summary: {scene['summary']}")
        lines.append(f"- POV: {scene['pov_character']}")
        lines.append(f"- Location: {scene['location']}")
        lines.extend(f"- thread: {thread_id}" for thread_id in scene.get("active_threads", []))

    lines.append("")
    lines.extend(bullet_section("## Recent Decisions", snapshot["recent_decisions"]))
    lines.append("")
    lines.extend(bullet_section("## Pending Actions", snapshot["pending_actions"]))
    lines.append("")
    lines.extend(bullet_section("## Open Questions", snapshot["open_questions"]))
    lines.append("")
    lines.extend(bullet_section("## Touched Records", snapshot["touched_records"]))

    if snapshot["artifacts"]:
        lines.append("")
        lines.extend(bullet_section("## Draft Artifacts", snapshot["artifacts"]))

    lines.append("")
    lines.append("## Parked Ideas")
    if not snapshot["ideas"]:
        lines.append("- none")
    else:
        for idea in snapshot["ideas"]:
            lines.append(f"- {idea['id']} [{idea['status']}]: {idea['summary']}")
            lines.append(f"  spark: {idea['spark']}")
            for question in idea.get("questions", []):
                lines.append(f"  question: {question}")
            if idea.get("next_probe"):
                lines.append(f"  next probe: {idea['next_probe']}")

    lines.append("")
    lines.append("## Resume")
    lines.append("- python3 tools/story.py validate")
    lines.append("- python3 tools/story.py audit")
    if scene:
        lines.append(f"- python3 tools/story.py context {scene['id']}")
        lines.append(f"- python3 tools/story.py draft {scene['id']} --mode scaffold")
    lines.append("- python3 tools/story.py handoff")
    return "\n".join(lines) + "\n"


def refresh_handoff(root: Path | None = None) -> tuple[Path, Path]:
    root = project_root(root)
    snapshot = build_handoff_snapshot(root)
    markdown_path = handoff_markdown_path(root)
    json_path = handoff_json_path(root)
    write_text(markdown_path, render_handoff_snapshot(snapshot))
    write_json(json_path, snapshot)
    return markdown_path, json_path


def render_handoff(root: Path | None = None) -> str:
    return render_handoff_snapshot(build_handoff_snapshot(root))


def create_checkpoint(
    summary: str,
    scene_id: str | None = None,
    status: str = "active",
    decisions: list[str] | None = None,
    pending_actions: list[str] | None = None,
    open_questions: list[str] | None = None,
    touched_records: list[str] | None = None,
    idea_ids: list[str] | None = None,
    artifacts: list[str] | None = None,
    allow_findings: bool = False,
    root: Path | None = None,
) -> CheckpointPaths:
    root = project_root(root)
    decisions = decisions or []
    pending_actions = pending_actions or []
    open_questions = open_questions or []
    touched_records = touched_records or []
    idea_ids = idea_ids or []
    artifacts = artifacts or []

    if scene_id:
        get_record("scene_state", scene_id, root)
    validate_record_ids(touched_records, root)
    validate_record_ids(idea_ids, root, expected_kind="idea")
    quality_gate = enforce_checkpoint_gate(root, allow_findings=allow_findings)

    checkpoint_id = f"checkpoint-{now_stamp()}-{slugify(summary, fallback='checkpoint')[:40]}"
    checkpoint_path = checkpoints_dir(root) / f"{checkpoint_id}.json"
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "id": checkpoint_id,
        "created_at": now_iso(),
        "summary": summary,
        "scene_id": scene_id,
        "status": status,
        "decisions": unique_strings(decisions),
        "pending_actions": unique_strings(pending_actions),
        "open_questions": unique_strings(open_questions),
        "touched_records": unique_strings((touched_records or []) + ([scene_id] if scene_id else []) + idea_ids),
        "idea_ids": unique_strings(idea_ids),
        "artifacts": unique_strings(artifacts),
        "quality_gate": quality_gate,
    }
    write_json(checkpoint_path, payload)
    markdown_path, json_path = refresh_handoff(root)
    return CheckpointPaths(
        checkpoint=checkpoint_path,
        handoff_markdown=markdown_path,
        handoff_json=json_path,
    )


def capture_idea(
    idea_id: str,
    name: str,
    summary: str,
    spark: str,
    status: str = "parked",
    questions: list[str] | None = None,
    possible_uses: list[str] | None = None,
    linked_records: list[str] | None = None,
    tags: list[str] | None = None,
    next_probe: str = "",
    force: bool = False,
    root: Path | None = None,
) -> Path:
    root = project_root(root)
    questions = questions or []
    possible_uses = possible_uses or []
    linked_records = linked_records or []
    tags = tags or []
    validate_record_ids(linked_records, root)

    kind_map = load_kind_map(root)
    meta = kind_map["idea"]
    target_path = meta.directory / f"{idea_id}.json"
    if target_path.exists() and not force:
        raise ProjectError(f"Refusing to overwrite existing file: {target_path}")

    payload = {
        "id": idea_id,
        "kind": "idea",
        "name": name,
        "status": status,
        "summary": summary,
        "spark": spark,
        "questions": unique_strings(questions),
        "possible_uses": unique_strings(possible_uses),
        "linked_records": unique_strings(linked_records),
        "next_probe": next_probe,
        "tags": unique_strings(tags),
        "last_touched": now_iso(),
    }
    meta.directory.mkdir(parents=True, exist_ok=True)
    write_json(target_path, payload)
    refresh_handoff(root)
    return target_path


def make_stub(kind: str, record_id: str, name: str | None, force: bool, root: Path | None = None) -> Path:
    root = project_root(root)
    kind_map = load_kind_map(root)
    if kind not in kind_map:
        raise ProjectError(f"Unknown kind: {kind}")
    meta = kind_map[kind]
    target_path = meta.directory / f"{record_id}.json"
    if target_path.exists() and not force:
        raise ProjectError(f"Refusing to overwrite existing file: {target_path}")
    template = load_json(meta.template)

    def replace_placeholders(value: Any) -> Any:
        if isinstance(value, str):
            result = value.replace("__ID__", record_id)
            result = result.replace("__NAME__", name or record_id.replace("-", " ").title())
            return result
        if isinstance(value, list):
            return [replace_placeholders(item) for item in value]
        if isinstance(value, dict):
            return {key: replace_placeholders(item) for key, item in value.items()}
        return value

    stub = replace_placeholders(template)
    meta.directory.mkdir(parents=True, exist_ok=True)
    write_json(target_path, stub)
    return target_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Story Workbench CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("validate", help="Validate all project records")

    list_parser = subparsers.add_parser("list", help="List records of a kind")
    list_parser.add_argument("kind")

    show_parser = subparsers.add_parser("show", help="Show a specific record")
    show_parser.add_argument("kind")
    show_parser.add_argument("id")

    search_parser = subparsers.add_parser("search", help="Search across records")
    search_parser.add_argument("term")
    search_parser.add_argument("--kind")

    context_parser = subparsers.add_parser("context", help="Assemble a scene context bundle")
    context_parser.add_argument("scene_id")

    audit_parser = subparsers.add_parser("audit", help="Run semantic continuity audit")
    audit_parser.add_argument("scene_id", nargs="?")
    audit_parser.add_argument("--draft", type=Path)

    draft_parser = subparsers.add_parser("draft", help="Generate a scene drafting kit or prose seed")
    draft_parser.add_argument("scene_id")
    draft_parser.add_argument("--mode", choices=["scaffold", "beats", "prose"], default="scaffold")
    draft_parser.add_argument("--output", type=Path)

    handoff_parser = subparsers.add_parser("handoff", help="Render the latest handoff snapshot")
    handoff_parser.add_argument("--refresh", action="store_true")

    checkpoint_parser = subparsers.add_parser(
        "checkpoint",
        help="Write a checkpoint, refresh the handoff, and preserve pending work across sessions",
    )
    checkpoint_parser.add_argument("summary")
    checkpoint_parser.add_argument("--scene")
    checkpoint_parser.add_argument("--status", choices=["active", "blocked", "done"], default="active")
    checkpoint_parser.add_argument("--decision", action="append", default=[])
    checkpoint_parser.add_argument("--pending", action="append", default=[])
    checkpoint_parser.add_argument("--question", action="append", default=[])
    checkpoint_parser.add_argument("--touch", action="append", default=[])
    checkpoint_parser.add_argument("--idea", action="append", default=[])
    checkpoint_parser.add_argument("--artifact", action="append", default=[])
    checkpoint_parser.add_argument(
        "--allow-findings",
        action="store_true",
        help="Write a checkpoint even if validation or semantic errors are still present.",
    )

    idea_parser = subparsers.add_parser("idea", help="Capture an unstable or parked idea as a structured record")
    idea_parser.add_argument("id")
    idea_parser.add_argument("--name", required=True)
    idea_parser.add_argument("--summary", required=True)
    idea_parser.add_argument("--spark", required=True)
    idea_parser.add_argument(
        "--status",
        choices=["seed", "exploring", "parked", "adopted", "rejected"],
        default="parked",
    )
    idea_parser.add_argument("--question", action="append", default=[])
    idea_parser.add_argument("--use", action="append", default=[])
    idea_parser.add_argument("--link", action="append", default=[])
    idea_parser.add_argument("--tag", action="append", default=[])
    idea_parser.add_argument("--next-probe", default="")
    idea_parser.add_argument("--force", action="store_true")

    stub_parser = subparsers.add_parser("stub", help="Create a stub record from a template")
    stub_parser.add_argument("kind")
    stub_parser.add_argument("id")
    stub_parser.add_argument("--name")
    stub_parser.add_argument("--force", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "validate":
            errors = validate_project()
            if errors:
                print("\n".join(errors))
                return 1
            print(f"Validated {len(iter_records())} records with no errors.")
            return 0

        if args.command == "list":
            print(list_records(args.kind))
            return 0

        if args.command == "show":
            print(summarize_record(get_record(args.kind, args.id)))
            return 0

        if args.command == "search":
            print(search_records(args.term, kind=args.kind))
            return 0

        if args.command == "context":
            print(build_scene_context(args.scene_id), end="")
            return 0

        if args.command == "audit":
            print(render_audit(args.scene_id, args.draft), end="")
            return 0

        if args.command == "draft":
            payload = render_scene_draft(args.scene_id, mode=args.mode)
            if args.output:
                write_text(args.output, payload)
                print(args.output)
            else:
                print(payload, end="")
            return 0

        if args.command == "handoff":
            if args.refresh:
                refresh_handoff()
            print(render_handoff(), end="")
            return 0

        if args.command == "checkpoint":
            paths = create_checkpoint(
                summary=args.summary,
                scene_id=args.scene,
                status=args.status,
                decisions=args.decision,
                pending_actions=args.pending,
                open_questions=args.question,
                touched_records=args.touch,
                idea_ids=args.idea,
                artifacts=[str(path) for path in args.artifact],
                allow_findings=args.allow_findings,
            )
            print(paths.checkpoint)
            print(paths.handoff_markdown)
            return 0

        if args.command == "idea":
            path = capture_idea(
                idea_id=args.id,
                name=args.name,
                summary=args.summary,
                spark=args.spark,
                status=args.status,
                questions=args.question,
                possible_uses=args.use,
                linked_records=args.link,
                tags=args.tag,
                next_probe=args.next_probe,
                force=args.force,
            )
            print(path)
            return 0

        if args.command == "stub":
            path = make_stub(args.kind, args.id, args.name, args.force)
            print(path)
            return 0
    except (ProjectError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    parser.print_help()
    return 1
