"""
Game engine for Sydney Life Simulator.

Handles loading scene data from JSON files (File I/O),
managing game state, and driving the scene-choice-ending loop.

Advanced concepts used:
- File I/O: load/save JSON scene data and game saves
- break/continue/return/raise: used throughout for control flow
"""

import json
import os

from src.models import (
    get_starting_stats,
    apply_effects,
    check_requirement,
    evaluate_endings,
)


# ---------------------------------------------------------------------------
# Scene data loading (File I/O)
# ---------------------------------------------------------------------------

def load_scenes(char_id, data_dir="data/scenes"):
    """Load all scene data for a character from a JSON file.

    The JSON file contains:
        {
            "character": "fern",
            "scenes": [ ... ],
            "endings": [ ... ]
        }

    Args:
        char_id: Character identifier (e.g., "fern").
        data_dir: Directory containing scene JSON files.

    Returns:
        Tuple of (scenes_list, endings_list).

    Raises:
        FileNotFoundError: If the scene file doesn't exist.
        ValueError: If the JSON structure is invalid.
    """
    file_path = os.path.join(data_dir, f"{char_id}.json")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Scene file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Validate basic structure
    if "scenes" not in data:
        raise ValueError(f"Scene file {file_path} missing 'scenes' key")
    if "endings" not in data:
        raise ValueError(f"Scene file {file_path} missing 'endings' key")

    return data["scenes"], data["endings"]


def load_character_bgm(char_id, data_dir="data/scenes"):
    """Return the gameplay BGM filename for a character, or None.

    Reads the optional top-level ``bgm`` field from the character's
    scene file. Returns None if the file or field is missing, so that
    background music is always an optional enhancement.

    Args:
        char_id: Character identifier (e.g., "kevin").
        data_dir: Directory containing scene JSON files.

    Returns:
        BGM filename string, or None.
    """
    file_path = os.path.join(data_dir, f"{char_id}.json")
    if not os.path.exists(file_path):
        return None
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("bgm")


# ---------------------------------------------------------------------------
# Game State
# ---------------------------------------------------------------------------

class GameState:
    """Tracks the current state of a playthrough.

    Attributes:
        char_id: Which character is being played.
        stats: Current stats dict (money, visa, skill, mood).
        flags: Set of string flags for conditional logic.
        current_scene_index: Index into the scenes list.
        history: List of (scene_id, choice_id) tuples for the playthrough.
        scenes: List of scene dicts loaded from JSON.
        endings: List of ending dicts loaded from JSON.
    """

    def __init__(self, char_id, scenes, endings):
        """Initialize a new game for the given character.

        Args:
            char_id: Character identifier.
            scenes: List of scene dicts.
            endings: List of ending dicts.
        """
        self.char_id = char_id
        self.stats = get_starting_stats(char_id)
        self.flags = set()
        self.current_scene_index = 0
        self.history = []
        self.scenes = scenes
        self.endings = endings

    def get_current_scene(self):
        """Return the current scene dict, or None if past the last scene.

        Returns:
            Scene dict or None.
        """
        if self.current_scene_index >= len(self.scenes):
            return None
        return self.scenes[self.current_scene_index]

    def get_available_choices(self):
        """Return list of (index, choice_dict, is_available) for current scene.

        A choice is unavailable if its stat requirements are not met.
        Unavailable choices are still returned (for display as greyed-out),
        but is_available is False.

        Returns:
            List of tuples: (choice_index, choice_dict, bool).
        """
        scene = self.get_current_scene()
        if scene is None:
            return []

        result = []
        for i, choice in enumerate(scene.get("choices", [])):
            requirement = choice.get("requirement", {})
            available = check_requirement(self.stats, requirement)
            result.append((i, choice, available))
        return result

    def make_choice(self, choice_index):
        """Apply a choice and advance to the next scene.

        Args:
            choice_index: Index of the chosen option.

        Returns:
            The choice dict that was applied.

        Raises:
            IndexError: If choice_index is out of range.
            RuntimeError: If the choice's requirements are not met.
        """
        scene = self.get_current_scene()
        choices = scene.get("choices", [])

        if choice_index < 0 or choice_index >= len(choices):
            raise IndexError(f"Choice index {choice_index} out of range "
                             f"(scene has {len(choices)} choices)")

        choice = choices[choice_index]

        # Verify requirements
        requirement = choice.get("requirement", {})
        if not check_requirement(self.stats, requirement):
            raise RuntimeError(
                f"Requirements not met for choice: {choice.get('text', '?')}")

        # Apply stat effects
        effects = choice.get("effects", {})
        apply_effects(self.stats, effects)

        # Apply flags
        for flag in choice.get("add_flags", []):
            self.flags.add(flag)

        # Record history
        scene_id = scene.get("id", f"scene_{self.current_scene_index}")
        choice_id = choice.get("id", f"choice_{choice_index}")
        self.history.append((scene_id, choice_id))

        # Advance to next scene
        self.current_scene_index += 1

        return choice

    def is_game_over(self):
        """Check if the game has reached the ending phase.

        Returns:
            True if all scenes have been played.
        """
        return self.current_scene_index >= len(self.scenes)

    def get_ending(self):
        """Determine the ending based on final stats and flags.

        Returns:
            Ending dict.

        Raises:
            RuntimeError: If called before game is over, or no ending matches.
        """
        if not self.is_game_over():
            raise RuntimeError("Game is not over yet!")
        return evaluate_endings(self.stats, self.endings, self.flags)

    def get_stats_display(self):
        """Return a formatted string showing current stats.

        Returns:
            Multi-line string with stat bars.
        """
        labels = {
            "money": ("金钱", "$"),
            "visa":  ("签证", "#"),
            "skill": ("技能", "*"),
            "mood":  ("心境", "~"),
        }
        lines = []
        for key in ["money", "visa", "skill", "mood"]:
            cn_name, symbol = labels[key]
            value = self.stats[key]
            bar = symbol * value + "." * (10 - value)
            lines.append(f"  {cn_name} [{bar}] {value}/10")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Save / Load (File I/O)
# ---------------------------------------------------------------------------

SAVE_DIR = "data"
SAVE_FILE = os.path.join(SAVE_DIR, "save.json")


def save_game(state):
    """Save the current game state to a JSON file.

    Args:
        state: GameState instance.
    """
    save_data = {
        "char_id": state.char_id,
        "stats": state.stats,
        "flags": list(state.flags),
        "current_scene_index": state.current_scene_index,
        "history": state.history,
    }
    os.makedirs(SAVE_DIR, exist_ok=True)
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)


def load_game():
    """Load a saved game state from file.

    Returns:
        GameState instance with restored state.

    Raises:
        FileNotFoundError: If no save file exists.
    """
    if not os.path.exists(SAVE_FILE):
        raise FileNotFoundError("No save file found.")

    with open(SAVE_FILE, "r", encoding="utf-8") as f:
        save_data = json.load(f)

    char_id = save_data["char_id"]
    scenes, endings = load_scenes(char_id)

    state = GameState(char_id, scenes, endings)
    state.stats = save_data["stats"]
    state.flags = set(save_data["flags"])
    state.current_scene_index = save_data["current_scene_index"]
    state.history = save_data["history"]

    return state


def has_save():
    """Check if a save file exists.

    Returns:
        True if a save file exists.
    """
    return os.path.exists(SAVE_FILE)


def delete_save():
    """Delete the save file if it exists."""
    if os.path.exists(SAVE_FILE):
        os.remove(SAVE_FILE)
