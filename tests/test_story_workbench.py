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
    adopt_idea,
    audit_idea_leaks,
    audit_project_semantics,
    audit_scene_draft_text,
    audit_scene_semantics,
    build_parser,
    build_scene_context,
    capture_idea,
    create_scene_delta,
    create_checkpoint,
    list_records,
    make_stub,
    reject_idea,
    render_doctor,
    render_handoff,
    render_threads_overview,
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
            self.assertNotIn("flood-prophet-temp", handoff)
            self.assertIn("Idea details are hidden by default", handoff)
            self.assertNotIn("flood-prophet-temp", checkpoint_paths.handoff_markdown.read_text(encoding="utf-8"))
            self.assertNotIn("flood-prophet-temp", checkpoint_paths.handoff_json.read_text(encoding="utf-8"))
            handoff_with_ideas = render_handoff(temp_root, include_ideas=True)
            self.assertIn("flood-prophet-temp", handoff_with_ideas)
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

    def test_handoff_with_ideas_includes_sample_idea(self) -> None:
        handoff = render_handoff(ROOT, include_ideas=True)
        self.assertIn("flood-prophet", handoff)
        self.assertIn("A witness figure", handoff)

    def test_adopt_and_reject_idea_update_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            shutil.copytree(ROOT / "config", temp_root / "config")
            shutil.copytree(ROOT / "data", temp_root / "data")

            adopt_idea(
                "flood-prophet",
                adopted_into=["ledger-theft"],
                decision="Adopted as an in-world rumor network, not one person.",
                root=temp_root,
            )
            idea_path = temp_root / "data" / "ideas" / "parking" / "flood-prophet.json"
            adopted = json.loads(idea_path.read_text(encoding="utf-8"))
            self.assertEqual(adopted["status"], "adopted")
            self.assertEqual(adopted["adopted_into"], ["ledger-theft"])
            self.assertIn("rumor network", adopted["adoption_decision"])
            self.assertIn("closed_at", adopted)
            self.assertIn("last_touched", adopted)

            reject_idea("flood-prophet", reason="Too similar to the Office rumor mechanism.", root=temp_root)
            rejected = json.loads(idea_path.read_text(encoding="utf-8"))
            self.assertEqual(rejected["status"], "rejected")
            self.assertIn("Office rumor", rejected["rejected_reason"])
            self.assertIn("closed_at", rejected)
            self.assertNotIn("adopted_into", rejected)

    def test_adopt_reject_errors_for_unknown_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            shutil.copytree(ROOT / "config", temp_root / "config")
            shutil.copytree(ROOT / "data", temp_root / "data")

            with self.assertRaises(ProjectError):
                adopt_idea("missing-idea", adopted_into=["ledger-theft"], decision="Nope.", root=temp_root)
            with self.assertRaises(ProjectError):
                adopt_idea("flood-prophet", adopted_into=["missing-record"], decision="Nope.", root=temp_root)
            with self.assertRaises(ProjectError):
                reject_idea("missing-idea", reason="Nope.", root=temp_root)

    def test_idea_leak_audit_catches_parked_and_rejected_markers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            shutil.copytree(ROOT / "config", temp_root / "config")
            shutil.copytree(ROOT / "data", temp_root / "data")

            scene_path = temp_root / "data" / "state" / "scenes" / "scene-001.json"
            scene = json.loads(scene_path.read_text(encoding="utf-8"))
            scene["facts_in_play"].append("Flood Prophet rumor is now discussed at the gate.")
            scene_path.write_text(json.dumps(scene, indent=2) + "\n", encoding="utf-8")

            findings = audit_idea_leaks(temp_root)
            self.assertTrue(any(finding.code == "idea-leak" and "Parked idea" in finding.message for finding in findings))

            idea_path = temp_root / "data" / "ideas" / "parking" / "flood-prophet.json"
            idea = json.loads(idea_path.read_text(encoding="utf-8"))
            idea["status"] = "adopted"
            idea["adopted_into"] = ["scene-001"]
            idea_path.write_text(json.dumps(idea, indent=2) + "\n", encoding="utf-8")
            self.assertFalse(any(finding.code == "idea-leak" for finding in audit_idea_leaks(temp_root)))

            idea["status"] = "adopted"
            idea.pop("adopted_into")
            idea_path.write_text(json.dumps(idea, indent=2) + "\n", encoding="utf-8")
            self.assertTrue(any(finding.code == "idea-adoption-missing-target" for finding in audit_idea_leaks(temp_root)))

            idea["status"] = "rejected"
            idea_path.write_text(json.dumps(idea, indent=2) + "\n", encoding="utf-8")
            self.assertTrue(any("Rejected idea" in finding.message for finding in audit_idea_leaks(temp_root)))

    def test_short_idea_markers_are_ignored_by_leak_audit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            shutil.copytree(ROOT / "config", temp_root / "config")
            shutil.copytree(ROOT / "data", temp_root / "data")

            idea_path = temp_root / "data" / "ideas" / "parking" / "flood-prophet.json"
            idea = json.loads(idea_path.read_text(encoding="utf-8"))
            idea["id"] = "key"
            idea["name"] = "Key"
            idea["tags"] = ["key"]
            idea_path.write_text(json.dumps(idea, indent=2) + "\n", encoding="utf-8")

            scene_path = temp_root / "data" / "state" / "scenes" / "scene-001.json"
            scene = json.loads(scene_path.read_text(encoding="utf-8"))
            scene["facts_in_play"].append("The key detail stays ordinary here.")
            scene_path.write_text(json.dumps(scene, indent=2) + "\n", encoding="utf-8")

            findings = audit_idea_leaks(temp_root)
            self.assertFalse(any(finding.code == "idea-leak" for finding in findings))

    def test_long_idea_markers_are_still_detected_by_leak_audit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            shutil.copytree(ROOT / "config", temp_root / "config")
            shutil.copytree(ROOT / "data", temp_root / "data")

            scene_path = temp_root / "data" / "state" / "scenes" / "scene-001.json"
            scene = json.loads(scene_path.read_text(encoding="utf-8"))
            scene["facts_in_play"].append("Flood Prophet rumor is now discussed at the gate.")
            scene_path.write_text(json.dumps(scene, indent=2) + "\n", encoding="utf-8")

            findings = audit_idea_leaks(temp_root)
            self.assertTrue(
                any(
                    finding.code == "idea-leak" and "Flood Prophet rumor" in finding.message
                    for finding in findings
                )
            )

    def test_ascii_idea_markers_use_token_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            shutil.copytree(ROOT / "config", temp_root / "config")
            shutil.copytree(ROOT / "data", temp_root / "data")

            idea_path = temp_root / "data" / "ideas" / "parking" / "flood-prophet.json"
            idea = json.loads(idea_path.read_text(encoding="utf-8"))
            idea["id"] = "red-door"
            idea["name"] = "Door"
            idea["tags"] = []
            idea_path.write_text(json.dumps(idea, indent=2) + "\n", encoding="utf-8")

            scene_path = temp_root / "data" / "state" / "scenes" / "scene-001.json"
            scene = json.loads(scene_path.read_text(encoding="utf-8"))
            scene["facts_in_play"].append("A shred-doorway rumor is too vague to matter.")
            scene_path.write_text(json.dumps(scene, indent=2) + "\n", encoding="utf-8")
            self.assertFalse(any(finding.code == "idea-leak" for finding in audit_idea_leaks(temp_root)))

            scene["facts_in_play"][-1] = "The red-door rumor is now explicit at the gate."
            scene_path.write_text(json.dumps(scene, indent=2) + "\n", encoding="utf-8")
            self.assertTrue(any(finding.code == "idea-leak" for finding in audit_idea_leaks(temp_root)))

    def test_context_manifest_is_present_and_excludes_ideas_by_policy(self) -> None:
        context = build_scene_context("scene-001", ROOT)
        self.assertIn("## Context Manifest", context)
        self.assertIn("- scene_state: scene-001", context)
        self.assertIn("- plot_thread: ledger-theft", context)
        self.assertIn("- data/ideas/**", context)
        self.assertNotIn("A witness figure that may be person", context)

    def test_scene_delta_creation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            shutil.copytree(ROOT / "config", temp_root / "config")
            shutil.copytree(ROOT / "data", temp_root / "data")

            path = create_scene_delta("scene-001", root=temp_root)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["scene_id"], "scene-001")
            self.assertEqual(payload["outcome"], "")
            self.assertEqual(payload["reference"]["scene_name"], "Dawn Inspection at Tidegate")
            with self.assertRaises(ProjectError):
                create_scene_delta("scene-001", root=temp_root)
            with self.assertRaises(ProjectError):
                create_scene_delta("missing-scene", root=temp_root)

    def test_reader_and_character_reveals_validate_and_render(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            shutil.copytree(ROOT / "config", temp_root / "config")
            shutil.copytree(ROOT / "schemas", temp_root / "schemas")
            shutil.copytree(ROOT / "data", temp_root / "data")

            scene_path = temp_root / "data" / "state" / "scenes" / "scene-001.json"
            scene = json.loads(scene_path.read_text(encoding="utf-8"))
            scene["reader_reveals"] = ["The ledger may prove a living heir."]
            scene["character_reveals"] = [{"character": "jun-alder", "learns": "Mira is carrying a record he was not cleared to see."}]
            scene_path.write_text(json.dumps(scene, indent=2) + "\n", encoding="utf-8")

            self.assertEqual(validate_project(temp_root), [])
            context = build_scene_context("scene-001", temp_root)
            self.assertIn("reader reveal: The ledger may prove a living heir.", context)
            self.assertIn("character reveal: jun-alder -> Mira is carrying", context)

            scene["character_reveals"] = [{"character": "missing-character", "learns": "A bad fact."}]
            scene_path.write_text(json.dumps(scene, indent=2) + "\n", encoding="utf-8")
            self.assertTrue(any("character_reveals[0].character" in error for error in validate_project(temp_root)))

    def test_threads_overview_lists_threads_and_warnings(self) -> None:
        overview = render_threads_overview(ROOT)
        self.assertIn("ledger-theft", overview)
        self.assertIn("referenced scenes: scene-001", overview)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            shutil.copytree(ROOT / "config", temp_root / "config")
            shutil.copytree(ROOT / "data", temp_root / "data")
            thread_path = temp_root / "data" / "plot" / "threads" / "orphan-thread.json"
            thread = json.loads((temp_root / "data" / "plot" / "threads" / "ledger-theft.json").read_text(encoding="utf-8"))
            thread["id"] = "orphan-thread"
            thread["name"] = "Orphan Thread"
            thread["status"] = "open"
            thread["resolution_criteria"] = []
            thread_path.write_text(json.dumps(thread, indent=2) + "\n", encoding="utf-8")

            overview = render_threads_overview(temp_root)
            self.assertIn("orphan-thread", overview)
            self.assertIn("open thread is not referenced", overview)
            self.assertIn("resolution_criteria is empty", overview)

    def test_audit_lang_ja_skips_english_lexical_contradiction_but_keeps_structure(self) -> None:
        ja_findings = audit_scene_draft_text(
            "scene-001",
            "The flood tunnel grates stood open at dawn while the queue drifted forward.",
            ROOT,
            lang="ja",
        )
        self.assertFalse(any(finding.code == "draft-contradiction" for finding in ja_findings))

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            shutil.copytree(ROOT / "config", temp_root / "config")
            shutil.copytree(ROOT / "data", temp_root / "data")

            scene_path = temp_root / "data" / "state" / "scenes" / "scene-001.json"
            scene = json.loads(scene_path.read_text(encoding="utf-8"))
            scene["present_characters"] = ["jun-alder"]
            scene_path.write_text(json.dumps(scene, indent=2) + "\n", encoding="utf-8")

            findings = audit_scene_semantics("scene-001", temp_root, lang="ja")
            self.assertTrue(any(finding.code == "pov-missing" for finding in findings))

    def test_doctor_detects_doc_links_and_validation_errors(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            for name in ("config", "data", "schemas", "templates", "docs"):
                shutil.copytree(ROOT / name, temp_root / name)
            shutil.copy(ROOT / "README.md", temp_root / "README.md")
            shutil.copy(ROOT / "README.ja.md", temp_root / "README.ja.md")

            readme = temp_root / "README.md"
            readme.write_text(readme.read_text(encoding="utf-8") + "\nBroken: /Users/foo/story-workbench/README.md\n", encoding="utf-8")
            report, status = render_doctor(temp_root)
            self.assertEqual(status, 0)
            self.assertIn("local-absolute-doc-link", report)

            scene_path = temp_root / "data" / "state" / "scenes" / "scene-001.json"
            scene = json.loads(scene_path.read_text(encoding="utf-8"))
            scene.pop("summary")
            scene_path.write_text(json.dumps(scene, indent=2) + "\n", encoding="utf-8")
            report, status = render_doctor(temp_root)
            self.assertEqual(status, 1)
            self.assertIn("validation errors", report)

    def test_doctor_strict_ideas_fails_on_idea_leak_findings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            for name in ("config", "data", "schemas", "templates", "docs"):
                shutil.copytree(ROOT / name, temp_root / name)
            shutil.copy(ROOT / "README.md", temp_root / "README.md")
            shutil.copy(ROOT / "README.ja.md", temp_root / "README.ja.md")

            scene_path = temp_root / "data" / "state" / "scenes" / "scene-001.json"
            scene = json.loads(scene_path.read_text(encoding="utf-8"))
            scene["facts_in_play"].append("Flood Prophet rumor is now discussed at the gate.")
            scene_path.write_text(json.dumps(scene, indent=2) + "\n", encoding="utf-8")

            report, status = render_doctor(temp_root)
            self.assertEqual(status, 0)
            self.assertIn("Strict idea mode: off", report)
            self.assertIn("idea leak findings", report)

            strict_report, strict_status = render_doctor(temp_root, strict_ideas=True)
            self.assertEqual(strict_status, 1)
            self.assertIn("Strict idea mode: on", strict_report)
            self.assertIn("strict idea mode treats idea leak findings as failing findings", strict_report)

            args = build_parser().parse_args(["doctor", "--strict-ideas"])
            self.assertTrue(args.strict_ideas)


if __name__ == "__main__":
    unittest.main()
