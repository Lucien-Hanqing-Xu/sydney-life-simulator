========================================
  Sydney Life Simulator
  悉尼人生模拟器
========================================

  Same city. Different lives.

========================================
  IMPORTANT — PLEASE READ FIRST (FOR THE TUTOR)
========================================
This is a DESKTOP GUI game (PyQt6) with images and background music.
It therefore CANNOT run inside Ed's online environment — please run it
locally on your own laptop. It needs two third-party libraries:

      pip install PyQt6 Pillow      (or:  pip install -r requirements.txt)

Then run:   python3 main.py         (RUN THIS FILE — main.py is the entry point)

- Pure Python otherwise; no internet/network needed.
- All images & audio are OPTIONAL — if any asset is missing the game still
  runs (text placeholder for images, silence for audio).
- The game logic also has unit tests that DO run anywhere:
      python3 -m unittest tests.test_engine -v
- A short demo video / GitHub link is provided on the Padlet post in case
  installing PyQt6 is inconvenient.

========================================

HOW TO RUN
----------
1. Make sure you have Python 3.8 or later installed.
2. Install dependencies:
       pip install PyQt6 Pillow
3. Navigate to this folder:
       cd final_project
4. Run the game:
       python3 main.py

   On Windows, use:
       python main.py

REQUIREMENTS
------------
- Python 3.8+
- PyQt6 (GUI framework)        ->  pip install PyQt6
- Pillow (image processing)    ->  pip install Pillow

NOTE (Anaconda users): if PyQt6 was installed inside an Anaconda
environment you may have seen a "Could not find the Qt platform plugin
'cocoa'" error with other apps. main.py fixes this automatically by
pointing Qt at PyQt6's own bundled plugins, so the game just runs.

ABOUT THE GAME
--------------
You choose one of four characters — each with a different visa type,
cultural background, and starting conditions — and experience life in
Sydney through their eyes. Your choices affect four stats (money, visa
stability, skill, mood) which determine your ending.

The game supports both Chinese and English. Click the language
toggle button (EN / 中文) on any screen to switch.

Characters:
  - Fern (小敏)    : WHV holder, small-town East Asian woman
  - Chelsea (思琪)  : Student visa, wealthy Shanghai girl
  - Ruth / Linh (灵): Spouse visa, Vietnamese restaurant owner
  - Kevin (阿杰)   : NZ citizen, 3rd-gen Cantonese diaspora

RUNNING TESTS
-------------
From the project folder:
    python3 -m unittest tests.test_engine -v

ADVANCED CONCEPTS USED
----------------------
1. File I/O: Scene data loaded from JSON files (data/scenes/);
   game save/load system (data/save.json).
2. Multi-Dimensional Lists: Character stats table in models.py
   (rows = characters, columns = stat values).
3. Testing: Unit tests in tests/test_engine.py using unittest.

PROJECT STRUCTURE
-----------------
final_project/
  main.py              - Entry point (run this!)
  README.txt           - This file
  src/
    models.py          - Data models and character table
    engine.py          - Game engine (state management, file I/O)
    gui.py             - PyQt6 GUI with bilingual support
  data/
    scenes/            - JSON scene files for each character
    save.json          - Auto-generated save file (created at runtime)
  assets/
    images/            - Title art, character portraits, scene & ending images
    audio/             - Optional background music (game runs silently if empty)
  tests/
    test_engine.py     - Unit tests
  design/
    story_framework.md - Story design document (not needed to run)

NOTE: All images and audio are optional. If an asset file is missing, the
game falls back gracefully (a text placeholder for images, silence for
audio), so it always runs.

Author: Hanqing (Lucien) Xu
Course: COMP9001 - Introduction to Programming
