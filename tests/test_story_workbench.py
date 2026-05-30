from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from story_workbench.cli import (
    ProjectError,
    audit_project_semantics,
    audit_scene_draft_text,
    audit_scene_semantics,
    build_scene_context,
    capture_idea,
    create_checkpoint,
    list_records,
    make_stub,
    render_handoff,
    render_scene_draft,
    search_records,
    validate_project,
)


class StoryWorkbenchTest(unittest.TestCase):
    def test_validate_sample_data(self) -> None:
        self.assertEqual(validate_project(ROOT), [])

    def test_scene_context_includes_scene_core(self) -> None:
        context = build_scene_context("scene-001", ROOT)
        self.assertIn("Dawn Inspection at Tidegate", context)
        self.assertIn("Mira Quill", context)
        self.assertIn("Jun Alder", context)
        self.assertIn("Who Benefits from the Stolen Succession Ledger?", context)
        self.assertIn("[canon]", context)

    def test_list_and_search_work(self) -> None:
        characters = list_records("character", ROOT)
        results = search_records("ledger", root=ROOT)
        self.assertIn("mira-quill", characters)
        self.assertIn("ledger-theft", results)
        self.assertIn("scene-001", results)

    def test_scene_draft_contains_scaffold_sections(self) -> None:
        draft = render_scene_draft("scene-001", mode="scaffold", root=ROOT)
        self.assertIn("## Continuity Watchpoints", draft)
        self.assertIn("## Beat Plan", draft)
        self.assertIn("## Prose Starter", draft)

    def test_seed_scene_has_no_semantic_findings(self) -> None:
        self.assertEqual(audit_scene_semantics("scene-001", ROOT), [])

    def test_draft_audit_flags_meaning_level_contradiction(self) -> None:
        findings = audit_scene_draft_text(
            "scene-001",
            "The flood tunnel grates stood open at dawn while the queue drifted forward.",
            ROOT,
        )
        self.assertTrue(any(finding.code == "draft-contradiction" for finding in findings))

    def test_project_audit_flags_location_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            shutil.copytree(ROOT / "config", temp_root / "config")
            shutil.copytree(ROOT / "data", temp_root / "data")

            target = temp_root / "data" / "state" / "characters" / "jun-alder-state.json"
            payload = json.loads(target.read_text(encoding="utf-8"))
            payload["current_location"] = "archive-wharf"
            target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

            findings = audit_project_semantics(temp_root)
            self.assertTrue(any(finding.code == "character-location-mismatch" for finding in findings))

    def test_idea_capture_and_checkpoint_refresh_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            shutil.copytree(ROOT / "config", temp_root / "config")
            shutil.copytree(ROOT / "schemas", temp_root / "schemas")
            shutil.copytree(ROOT / "data", temp_root / "data")

            idea_path = capture_idea(
                "flood-prophet-temp",
                name="Flood Prophet rumor",
                summary="A witness figure that might be person, office myth, or distributed legend.",
                spark="The city could speak back through rumor and bureaucracy.",
                questions=["Is the prophet a person or a title?"],
                linked_records=["memory-tithe-city", "mira-quill"],
                root=temp_root,
            )

            checkpoint_paths = create_checkpoint(
                summary="Locked the opening scene pressure",
                scene_id="scene-001",
                decisions=["Kept Jun as the direct obstacle at the gate."],
                pending_actions=["Draft the first prose pass for scene-001."],
                open_questions=["Does Jun search the satchel in public or in private?"],
                touched_records=["mira-quill", "jun-alder", "episode-001"],
                idea_ids=["flood-prophet-temp"],
                root=temp_root,
            )

            self.assertTrue(idea_path.exists())
            self.assertTrue(checkpoint_paths.checkpoint.exists())
            handoff = render_handoff(temp_root)
            self.assertIn("Locked the opening scene pressure", handoff)
            self.assertIn("flood-prophet-temp", handoff)
            self.assertIn("scene-001", handoff)
            self.assertIn("Quality gate:", handoff)

    def test_stub_creation_uses_template(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            shutil.copytree(ROOT / "config", temp_root / "config")
            shutil.copytree(ROOT / "templates", temp_root / "templates")
            (temp_root / "data" / "canon" / "characters").mkdir(parents=True)

            path = make_stub("character", "lio-vann", "Lio Vann", force=False, root=temp_root)

            self.assertTrue(path.exists())
            payload = path.read_text(encoding="utf-8")
            self.assertIn('"id": "lio-vann"', payload)
            self.assertIn('"name": "Lio Vann"', payload)

    def test_scene_context_uses_state_snapshot_for_scene_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            shutil.copytree(ROOT / "config", temp_root / "config")
            shutil.copytree(ROOT / "data", temp_root / "data")

            later_scene = json.loads((temp_root / "data" / "state" / "scenes" / "scene-001.json").read_text(encoding="utf-8"))
            later_scene["id"] = "scene-002"
            later_scene["name"] = "Aftermath at Tidegate"
            later_scene["sort_key"] = 20
            later_scene["summary"] = "A later pressure pass at the same gate."
            (temp_root / "data" / "state" / "scenes" / "scene-002.json").write_text(
                json.dumps(later_scene, indent=2) + "\n",
                encoding="utf-8",
            )

            later_state = json.loads(
                (temp_root / "data" / "state" / "characters" / "mira-quill-state.json").read_text(encoding="utf-8")
            )
            later_state["id"] = "mira-quill-state-later"
            later_state["current_goal"] = "Burn the ledger before anyone can read it."
            later_state["updated_at"] = "scene-002"
            (temp_root / "data" / "state" / "characters" / "mira-quill-state-later.json").write_text(
                json.dumps(later_state, indent=2) + "\n",
                encoding="utf-8",
            )

            context = build_scene_context("scene-001", temp_root)
            self.assertIn("Get the ledger through the gate without exposing the heir claim.", context)
            self.assertNotIn("Burn the ledger before anyone can read it.", context)

    def test_project_audit_flags_item_holder_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            shutil.copytree(ROOT / "config", temp_root / "config")
            shutil.copytree(ROOT / "data", temp_root / "data")

            target = temp_root / "data" / "state" / "items" / "moon-key-state.json"
            payload = json.loads(target.read_text(encoding="utf-8"))
            payload["current_holder"] = "jun-alder"
            target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

            findings = audit_project_semantics(temp_root)
            self.assertTrue(
                any(finding.code in {"owner-holder-mismatch", "item-holder-inventory-mismatch"} for finding in findings)
            )

    def test_checkpoint_gate_blocks_semantic_errors(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            shutil.copytree(ROOT / "config", temp_root / "config")
            shutil.copytree(ROOT / "schemas", temp_root / "schemas")
            shutil.copytree(ROOT / "data", temp_root / "data")

            target = temp_root / "data" / "state" / "scenes" / "scene-001.json"
            payload = json.loads(target.read_text(encoding="utf-8"))
            payload["present_characters"] = ["jun-alder"]
            target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

            with self.assertRaises(ProjectError):
                create_checkpoint(
                    summary="Should fail on semantic error",
                    scene_id="scene-001",
                    decisions=["Tried to checkpoint a broken scene."],
                    root=temp_root,
                )


if __name__ == "__main__":
    unittest.main()
