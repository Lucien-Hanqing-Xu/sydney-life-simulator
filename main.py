#!/usr/bin/env python3
"""
Sydney Life Simulator
=====================
A branching narrative game where you experience life in Sydney
through the eyes of four characters with different backgrounds,
visa types, and starting conditions.

Same city. Different lives.

HOW TO RUN:
    python3 main.py

REQUIREMENTS:
    - Python 3.8+
    - PyQt6:   pip install PyQt6
    - Pillow:  pip install Pillow   (optional, for extra image formats)

ADVANCED CONCEPTS USED:
    - File I/O: Scene data loaded from JSON files; save/load game progress
    - Multi-Dimensional Lists: Character stats table; ending condition matrix
    - Testing: See tests/test_engine.py
              (run with: python3 -m unittest tests.test_engine -v)

Author: Hanqing (Lucien) Xu
Course: COMP9001 — Introduction to Programming
"""

import os
import sys

# Ensure we can import from the project root regardless of where
# the script is run from.
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def _qt_plugin_root():
    """Return the path to PyQt6's bundled Qt plugins, or None."""
    import PyQt6
    root = os.path.join(os.path.dirname(PyQt6.__file__), "Qt6", "plugins")
    return root if os.path.isdir(root) else None


# ---------------------------------------------------------------------------
# Anaconda compatibility fix.
#
# When PyQt6 is installed inside an Anaconda environment, Anaconda's own
# qt.conf points Qt to its bundled Qt 5.15 plugins, which are incompatible
# with PyQt6 (Qt 6). The result is a crash on startup:
#     "Could not find the Qt platform plugin 'cocoa'"
#
# We fix this by forcing Qt to use PyQt6's OWN bundled plugins. The path is
# computed dynamically, so this is harmless on machines without Anaconda.
# These environment variables MUST be set before PyQt6 is imported.
# ---------------------------------------------------------------------------
_PLUGIN_ROOT = _qt_plugin_root()
if _PLUGIN_ROOT:
    os.environ["QT_PLUGIN_PATH"] = _PLUGIN_ROOT
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.path.join(
        _PLUGIN_ROOT, "platforms"
    )

from PyQt6.QtWidgets import QApplication
from src.gui import SydneyLifeSimApp


def main():
    """Entry point for the game."""
    app = QApplication(sys.argv)

    # Force Qt to look ONLY in PyQt6's plugin directory, removing any
    # conflicting Anaconda Qt5 paths that may still be registered.
    if _PLUGIN_ROOT:
        app.setLibraryPaths([_PLUGIN_ROOT])

    window = SydneyLifeSimApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
