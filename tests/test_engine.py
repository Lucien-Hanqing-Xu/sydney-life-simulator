"""
Unit tests for Sydney Life Simulator game engine.

Tests the core logic without touching the GUI.

Advanced concept: Testing (unittest)

Run with:
    cd final_project
    python3 -m unittest tests.test_engine -v
"""

import unittest
import os
import json
import tempfile

# Adjust path so imports work when run from project root
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models import (
    make_stats,
    apply_effects,
    check_requirement,
    evaluate_endings,
    get_character_ids,
    get_starting_stats,
    get_character_display_name,
    get_character_descriptions,
    CHARACTER_TABLE,
)
from src.engine import GameState, load_scenes


class TestMakeStats(unittest.TestCase):
    """Test the make_stats helper function."""

    def test_default_stats(self):
        """Default stats should all be 5."""
        stats = make_stats()
        self.assertEqual(stats["money"], 5)
        self.assertEqual(stats["visa"], 5)
        self.assertEqual(stats["skill"], 5)
        self.assertEqual(stats["mood"], 5)

    def test_custom_stats(self):
        """Custom stat values should be set correctly."""
        stats = make_stats(money=2, visa=8, skill=3, mood=6)
        self.assertEqual(stats["money"], 2)
        self.assertEqual(stats["visa"], 8)
        self.assertEqual(stats["skill"], 3)
        self.assertEqual(stats["mood"], 6)


class TestApplyEffects(unittest.TestCase):
    """Test stat effect application."""

    def test_positive_effect(self):
        """Positive effects should increase stats."""
        stats = make_stats(money=3, mood=5)
        apply_effects(stats, {"money": 2, "mood": 1})
        self.assertEqual(stats["money"], 5)
        self.assertEqual(stats["mood"], 6)

    def test_negative_effect(self):
        """Negative effects should decrease stats."""
        stats = make_stats(money=5, mood=3)
        apply_effects(stats, {"money": -2, "mood": -1})
        self.assertEqual(stats["money"], 3)
        self.assertEqual(stats["mood"], 2)

    def test_clamp_upper(self):
        """Stats should not exceed 10."""
        stats = make_stats(mood=9)
        apply_effects(stats, {"mood": 5})
        self.assertEqual(stats["mood"], 10)

    def test_clamp_lower(self):
        """Stats should not go below 0."""
        stats = make_stats(money=1)
        apply_effects(stats, {"money": -5})
        self.assertEqual(stats["money"], 0)

    def test_invalid_key_raises(self):
        """Invalid stat keys should raise ValueError."""
        stats = make_stats()
        with self.assertRaises(ValueError):
            apply_effects(stats, {"charisma": 3})

    def test_empty_effects(self):
        """Empty effects dict should not change stats."""
        stats = make_stats(money=5)
        apply_effects(stats, {})
        self.assertEqual(stats["money"], 5)


class TestCheckRequirement(unittest.TestCase):
    """Test choice requirement checking."""

    def test_no_requirement(self):
        """No requirement (None or empty) should always pass."""
        stats = make_stats(money=0)
        self.assertTrue(check_requirement(stats, None))
        self.assertTrue(check_requirement(stats, {}))

    def test_met_requirement(self):
        """Should return True when stats meet requirements."""
        stats = make_stats(skill=6, money=4)
        self.assertTrue(check_requirement(stats, {"skill": 5, "money": 3}))

    def test_exact_requirement(self):
        """Should return True when stats exactly equal requirements."""
        stats = make_stats(skill=5)
        self.assertTrue(check_requirement(stats, {"skill": 5}))

    def test_unmet_requirement(self):
        """Should return False when stats are below requirements."""
        stats = make_stats(skill=3)
        self.assertFalse(check_requirement(stats, {"skill": 5}))

    def test_partial_requirement(self):
        """Should return False if any one requirement is not met."""
        stats = make_stats(skill=6, money=2)
        self.assertFalse(check_requirement(stats, {"skill": 5, "money": 3}))


class TestEvaluateEndings(unittest.TestCase):
    """Test ending determination based on stats and flags."""

    def setUp(self):
        """Set up sample endings."""
        self.endings = [
            {
                "id": "good",
                "title": "Good ending",
                "condition": {"skill": 6, "mood": 5},
                "text": "You made it!",
            },
            {
                "id": "flag_ending",
                "title": "Flag ending",
                "condition": {},
                "flag_condition": {"went_home": True},
                "text": "You went home.",
            },
            {
                "id": "default",
                "title": "Default ending",
                "condition": {},
                "text": "Default.",
            },
        ]

    def test_good_ending(self):
        """High stats should trigger the good ending."""
        stats = make_stats(skill=7, mood=6)
        ending = evaluate_endings(stats, self.endings)
        self.assertEqual(ending["id"], "good")

    def test_flag_ending(self):
        """Correct flag should trigger the flag-based ending."""
        stats = make_stats(skill=2, mood=2)
        ending = evaluate_endings(stats, self.endings, flags={"went_home"})
        self.assertEqual(ending["id"], "flag_ending")

    def test_default_ending(self):
        """Low stats with no flags should fall through to default."""
        stats = make_stats(skill=2, mood=2)
        ending = evaluate_endings(stats, self.endings)
        self.assertEqual(ending["id"], "default")

    def test_no_match_raises(self):
        """Should raise RuntimeError if no ending matches."""
        endings_no_fallback = [
            {
                "id": "impossible",
                "title": "Impossible",
                "condition": {"skill": 99},
                "text": "Never.",
            }
        ]
        stats = make_stats()
        with self.assertRaises(RuntimeError):
            evaluate_endings(stats, endings_no_fallback)


class TestCharacterTable(unittest.TestCase):
    """Test the multi-dimensional character table."""

    def test_table_has_four_characters(self):
        """Should have exactly 4 characters."""
        self.assertEqual(len(CHARACTER_TABLE), 4)

    def test_character_ids(self):
        """Should return correct character IDs."""
        ids = get_character_ids()
        self.assertEqual(ids, ["fern", "chelsea", "ruth", "kevin"])

    def test_starting_stats_fern(self):
        """Fern's starting stats should match the design."""
        stats = get_starting_stats("fern")
        self.assertEqual(stats["money"], 2)
        self.assertEqual(stats["visa"], 2)
        self.assertEqual(stats["skill"], 2)
        self.assertEqual(stats["mood"], 6)

    def test_starting_stats_kevin(self):
        """Kevin should have high visa (NZ citizen)."""
        stats = get_starting_stats("kevin")
        self.assertEqual(stats["visa"], 9)

    def test_invalid_character_raises(self):
        """Unknown character should raise ValueError."""
        with self.assertRaises(ValueError):
            get_starting_stats("nobody")

    def test_display_names(self):
        """Display names should be the canonical (Chinese) character names."""
        self.assertEqual(get_character_display_name("fern"), "小敏")
        self.assertEqual(get_character_display_name("chelsea"), "思琪")
        self.assertEqual(get_character_display_name("ruth"), "Linh")
        self.assertEqual(get_character_display_name("kevin"), "阿杰")

    def test_descriptions_completeness(self):
        """Each character should have a description entry."""
        descs = get_character_descriptions()
        self.assertEqual(len(descs), 4)
        for entry in descs:
            self.assertEqual(len(entry), 4)  # id, name, subtitle, desc


class TestLoadScenes(unittest.TestCase):
    """Test scene loading from JSON files."""

    def test_load_fern(self):
        """Should successfully load Fern's scene data."""
        scenes, endings = load_scenes("fern")
        self.assertEqual(len(scenes), 12)
        self.assertGreater(len(endings), 0)
        # Check first scene has required keys
        scene = scenes[0]
        self.assertIn("id", scene)
        self.assertIn("title", scene)
        self.assertIn("narrative", scene)
        self.assertIn("choices", scene)

    def test_load_all_characters(self):
        """All four character files should load without errors."""
        for char_id in get_character_ids():
            scenes, endings = load_scenes(char_id)
            self.assertGreater(len(scenes), 0, f"{char_id} has no scenes")
            self.assertGreater(len(endings), 0, f"{char_id} has no endings")

    def test_missing_file_raises(self):
        """Loading a non-existent character should raise FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            load_scenes("nonexistent_character")


class TestGameState(unittest.TestCase):
    """Test the GameState class and game flow."""

    def setUp(self):
        """Load Fern's scenes for testing."""
        self.scenes, self.endings = load_scenes("fern")
        self.state = GameState("fern", self.scenes, self.endings)

    def test_initial_state(self):
        """Initial state should be at scene 0 with starting stats."""
        self.assertEqual(self.state.current_scene_index, 0)
        self.assertEqual(self.state.stats["money"], 2)
        self.assertFalse(self.state.is_game_over())

    def test_get_current_scene(self):
        """Should return the first scene."""
        scene = self.state.get_current_scene()
        self.assertEqual(scene["id"], "ch1a_landing")

    def test_make_choice_advances(self):
        """Making a choice should advance to the next scene."""
        self.state.make_choice(0)
        self.assertEqual(self.state.current_scene_index, 1)
        scene = self.state.get_current_scene()
        self.assertEqual(scene["id"], "ch1b_register")

    def test_choice_applies_effects(self):
        """Choice effects should modify stats."""
        # Choice 0 in ch1 (boundary): mood +1
        initial_mood = self.state.stats["mood"]
        self.state.make_choice(0)
        self.assertEqual(self.state.stats["mood"], initial_mood + 1)

    def test_choice_adds_flags(self):
        """Choices with flags should add them to the state."""
        # Choice 1 in ch1 (promise): adds "promised_money"
        self.state.make_choice(1)
        self.assertIn("promised_money", self.state.flags)

    def test_invalid_choice_raises(self):
        """Out-of-range choice should raise IndexError."""
        with self.assertRaises(IndexError):
            self.state.make_choice(99)

    def test_full_playthrough(self):
        """Playing through all scenes should reach game over."""
        # Make first available choice in each scene
        while not self.state.is_game_over():
            choices = self.state.get_available_choices()
            # Pick first available choice
            for idx, choice, available in choices:
                if available:
                    self.state.make_choice(idx)
                    break

        self.assertTrue(self.state.is_game_over())
        ending = self.state.get_ending()
        self.assertIn("title", ending)
        self.assertIn("text", ending)

    def test_history_recorded(self):
        """Choice history should be recorded."""
        self.state.make_choice(0)
        self.assertEqual(len(self.state.history), 1)
        self.assertEqual(self.state.history[0][0], "ch1a_landing")


class TestGameStateAllCharacters(unittest.TestCase):
    """Test that all four characters can complete a full playthrough."""

    def test_full_playthrough_all(self):
        """Every character should be able to play through and reach an ending."""
        for char_id in get_character_ids():
            scenes, endings = load_scenes(char_id)
            state = GameState(char_id, scenes, endings)

            while not state.is_game_over():
                choices = state.get_available_choices()
                for idx, choice, available in choices:
                    if available:
                        state.make_choice(idx)
                        break

            ending = state.get_ending()
            self.assertIsNotNone(
                ending,
                f"Character '{char_id}' failed to reach an ending"
            )


if __name__ == "__main__":
    unittest.main()
