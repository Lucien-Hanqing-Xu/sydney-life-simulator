"""
Data models for Sydney Life Simulator.

Defines the core data structures: Character, Scene, Choice, Ending, GameState.
All game data is represented as simple dictionaries loaded from JSON;
these helper functions validate and access that data.

Advanced concepts used:
- Multi-Dimensional Lists: character stats table, ending conditions
- File I/O: models are loaded from JSON (see engine.py)
"""


def make_stats(money=5, visa=5, skill=5, mood=5):
    """Create a stats dictionary with default values.

    Args:
        money: Economic security (0-10)
        visa: Visa stability (0-10)
        skill: Career capital (0-10)
        mood: Mental health / happiness (0-10)

    Returns:
        dict with four stat keys.
    """
    return {
        "money": money,
        "visa": visa,
        "skill": skill,
        "mood": mood,
    }


def apply_effects(stats, effects):
    """Apply stat effects from a choice to current stats.

    Each effect is a key-value pair like {"money": -2, "mood": 1}.
    Stats are clamped to [0, 10].

    Args:
        stats: Current stats dict (modified in-place).
        effects: Dict of stat changes.

    Returns:
        The modified stats dict.

    Raises:
        ValueError: If an effect key is not a valid stat name.
    """
    valid_keys = {"money", "visa", "skill", "mood"}
    for key, delta in effects.items():
        if key not in valid_keys:
            raise ValueError(f"Invalid stat key: '{key}'. Must be one of {valid_keys}")
        stats[key] = max(0, min(10, stats[key] + delta))
    return stats


def check_requirement(stats, requirement):
    """Check whether current stats meet a choice's requirement.

    A requirement is a dict like {"skill": 5, "money": 3},
    meaning skill >= 5 AND money >= 3.

    Args:
        stats: Current stats dict.
        requirement: Dict of minimum stat values, or None/empty.

    Returns:
        True if all requirements are met (or if no requirements).
    """
    if not requirement:
        return True
    for key, minimum in requirement.items():
        if stats.get(key, 0) < minimum:
            return False
    return True


def evaluate_endings(stats, endings, flags=None):
    """Determine which ending the player gets based on final stats.

    Endings are checked in order; the first one whose conditions are
    met is returned. The last ending should have no conditions (fallback).

    Each ending dict has:
        - "id": unique ending identifier
        - "title": display title
        - "condition": dict of stat requirements (optional)
        - "flag_condition": dict of required flags (optional)
        - "text": ending narrative text

    Args:
        stats: Final stats dict.
        endings: List of ending dicts, checked in order.
        flags: Set of string flags accumulated during the game.

    Returns:
        The first matching ending dict.

    Raises:
        RuntimeError: If no ending matches (design error).
    """
    if flags is None:
        flags = set()

    for ending in endings:
        # Check stat conditions
        condition = ending.get("condition", {})
        if not check_requirement(stats, condition):
            continue

        # Check flag conditions (e.g., "chose_grey_zone")
        flag_condition = ending.get("flag_condition", {})
        flag_ok = True
        for flag_name, required_value in flag_condition.items():
            has_flag = flag_name in flags
            if has_flag != required_value:
                flag_ok = False
                break
        if not flag_ok:
            continue

        return ending

    raise RuntimeError("No ending matched! Check your ending conditions — "
                       "the last ending should have no conditions (fallback).")


# ---------------------------------------------------------------------------
# Character definitions: starting stats as a 2D table
# This IS the Multi-Dimensional Lists advanced concept.
# ---------------------------------------------------------------------------

# Each row: [name_en, name_cn, money, visa, skill, mood]
CHARACTER_TABLE = [
    ["fern",    "小敏",  2, 2, 2, 6],
    ["chelsea", "思琪",  8, 5, 3, 6],
    ["ruth",    "Linh",  4, 5, 5, 5],
    ["kevin",   "阿杰",  5, 9, 2, 4],
]

# Column indices for the table above
COL_ID = 0
COL_DISPLAY = 1
COL_MONEY = 2
COL_VISA = 3
COL_SKILL = 4
COL_MOOD = 5


def get_character_ids():
    """Return list of character IDs (e.g., ['fern', 'chelsea', ...])."""
    return [row[COL_ID] for row in CHARACTER_TABLE]


def get_character_display_name(char_id):
    """Return the display name for a character ID."""
    for row in CHARACTER_TABLE:
        if row[COL_ID] == char_id:
            return row[COL_DISPLAY]
    raise ValueError(f"Unknown character: '{char_id}'")


def get_starting_stats(char_id):
    """Return starting stats dict for a character ID."""
    for row in CHARACTER_TABLE:
        if row[COL_ID] == char_id:
            return make_stats(
                money=row[COL_MONEY],
                visa=row[COL_VISA],
                skill=row[COL_SKILL],
                mood=row[COL_MOOD],
            )
    raise ValueError(f"Unknown character: '{char_id}'")


def get_character_descriptions():
    """Return a list of (id, display_name, description) for character select.

    Uses a 2D list: rows = characters, columns = attributes.
    """
    descriptions = [
        ["fern", "小敏", "WHV签证 · 底层东亚女性",
         "25岁，小镇出身，一个箱子和2000刀来到悉尼。\n"
         "妈妈每周打电话催她寄钱。\n"
         "她的武器只有一辆续航缩水的电瓶车和不肯认输的心。"],
        ["chelsea", "思琪", "学生签证 · 上海白富美",
         "22岁，上海富家女，Darling Harbour海景公寓。\n"
         "传媒+商科双学位，小红书两万粉。\n"
         "她拥有一切，直到一场黄谣把一切撕碎。"],
        ["ruth", "Linh", "陪读家属签 · 越南中年女性",
         "38岁，胡志明市人，跟读博的丈夫来澳。\n"
         "在Marrickville开了一家越南粉店。\n"
         "签证绑在丈夫身上，但梦想只属于她自己。"],
        ["kevin", "阿杰", "NZ公民 · 粤/闽南洋后裔",
         "23岁，新西兰出生，下南洋第三代。\n"
         "八大在读，日常喝茶打球打游戏。\n"
         "祖辈拼命换来的自由，他用来躺平。"],
    ]
    return descriptions
