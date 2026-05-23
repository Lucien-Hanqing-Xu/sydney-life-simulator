"""
GUI for Sydney Life Simulator using PyQt6.

Displays scene images, narrative text, stat bars,
and choice buttons. Supports bilingual (中文/English) switching.

Layout:
    +-----------------------------------+
    |          [Scene Image]            |
    +-----------------------------------+
    |  Stats bar (money/visa/skill/mood)|
    +-----------------------------------+
    |  Chapter Title            [EN/中] |
    |                                   |
    |       Narrative text (scroll)     |
    |                                   |
    +-----------------------------------+
    |  [Choice A]                       |
    |  [Choice B]                       |
    |  [Choice C]                       |
    +-----------------------------------+
"""

import os

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QScrollArea, QFrame, QGraphicsDropShadowEffect,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QPixmap, QFont, QColor, QPainter

# QtMultimedia is optional — the game runs silently if it is unavailable.
try:
    from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
    HAS_AUDIO = True
except ImportError:
    HAS_AUDIO = False

from src.models import (
    get_character_display_name,
    get_character_descriptions,
    get_starting_stats,
)
from src.engine import (
    GameState,
    load_scenes,
    load_character_bgm,
    save_game,
    load_game,
    has_save,
    delete_save,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WINDOW_WIDTH = 900
WINDOW_HEIGHT = 720
IMAGE_HEIGHT = 400
AUDIO_DIR = "assets/audio"
BGM_VOLUME = 0.4
# Title/menu music: first existing file wins (drop a dedicated title.mp3
# in assets/audio to override; otherwise the hopeful theme is used).
TITLE_BGM_CANDIDATES = ["title.mp3", "mood_hopeful.mp3"]

# Typography: drop title.ttf / body.ttf / mono.ttf into assets/fonts/ to
# upgrade the whole UI. If absent, these system fallbacks are used.
FONTS_DIR = "assets/fonts"
TITLE_FONT = "Georgia"      # headings / title  (override: assets/fonts/title.ttf)
BODY_FONT = "Helvetica"     # body / buttons    (override: assets/fonts/body.ttf)
MONO_FONT = "Courier"       # stat numbers      (override: assets/fonts/mono.ttf)

BG_COLOR = "#1a1a2e"
CARD_BG = "#16213e"
CARD_HOVER = "#1c2a4a"
DARK_BG = "#0f0f1a"
STATS_BG = "#0f0f23"
TEXT_COLOR = "#e0e0e0"
ACCENT_COLOR = "#e94560"
DIM_COLOR = "#888888"
DISABLED_COLOR = "#555555"
DISABLED_BG = "#0a0a15"

STAT_COLORS = {
    "money": "#f0c040",
    "visa":  "#40a0f0",
    "skill": "#f08040",
    "mood":  "#80e080",
}

# ---------------------------------------------------------------------------
# Bilingual UI strings
# ---------------------------------------------------------------------------

UI = {
    "title_main":   {"zh": "悉尼人生模拟器", "en": "Sydney Life Simulator"},
    "tagline":      {"zh": "同一座城市，不同的人生。",
                     "en": "Same city. Different lives."},
    "new_game":     {"zh": "新游戏",   "en": "New Game"},
    "continue":     {"zh": "继续游戏", "en": "Continue"},
    "quit":         {"zh": "退出", "en": "Quit"},
    "select_char":  {"zh": "选择你的人生", "en": "Choose Your Life"},
    "back":         {"zh": "< 返回", "en": "< Back"},
    "restart":      {"zh": "重新开始", "en": "Restart"},
    "to_title":     {"zh": "返回标题", "en": "Title Screen"},
    "ending_label": {"zh": "结局", "en": "ENDING"},
    "requires":     {"zh": "需要", "en": "Requires"},
    "money":        {"zh": "金钱", "en": "Money"},
    "visa":         {"zh": "签证", "en": "Visa"},
    "skill":        {"zh": "技能", "en": "Skill"},
    "mood":         {"zh": "心境", "en": "Mood"},
    "lang_toggle":  {"zh": "EN", "en": "中文"},
    "ch_of":        {"zh": "第 {0} / {1} 章", "en": "Chapter {0} / {1}"},
    "music_on":     {"zh": "♪ 音乐", "en": "♪ Music"},
    "music_off":    {"zh": "♪̶ 静音", "en": "♪̶ Muted"},
    "trajectory":   {"zh": "查看选择轨迹", "en": "View Your Path"},
    "your_path":    {"zh": "你的选择轨迹", "en": "Your Path"},
    "back_ending":  {"zh": "< 返回结局", "en": "< Back to Ending"},
    "verdict":      {"zh": "评语", "en": "Verdict"},
    "not_chosen":   {"zh": "未选择", "en": "not taken"},
    "fs_hint":      {"zh": "F11 全屏 · F 无边框 · Esc 退出全屏",
                     "en": "F11 Fullscreen · F Borderless · Esc Exit"},
}

# English character descriptions for the select screen
EN_CHAR_DESC = {
    "fern": (
        "Fern",
        "WHV · Working-class East Asian woman",
        "25, small-town origin, arrived in Sydney with one suitcase\n"
        "and $2,000. Mum calls weekly asking when she'll send money.\n"
        "Her only weapons: a dodgy e-bike and a refusal to give up.",
    ),
    "chelsea": (
        "Chelsea",
        "Student visa · Shanghai heiress",
        "22, wealthy Shanghai family, harbour-view apartment.\n"
        "Media + Commerce dual degree, 20k Xiaohongshu followers.\n"
        "She had everything — until a smear campaign tore it apart.",
    ),
    "ruth": (
        "Linh",
        "Student-dependent visa · Vietnamese woman",
        "38, from Ho Chi Minh City, followed her PhD-student husband.\n"
        "Opened a pho restaurant on Marrickville Road.\n"
        "Her visa is chained to him; her dream is her own.",
    ),
    "kevin": (
        "Kevin",
        "NZ citizen · 3rd-gen Cantonese diaspora",
        "23, born in New Zealand, third generation since Nanyang.\n"
        "Go8 uni student. Daily: yum cha, basketball, gaming.\n"
        "His grandparents risked everything for freedom — he lies flat.",
    ),
}


# ---------------------------------------------------------------------------
# Image helper
# ---------------------------------------------------------------------------

def load_custom_fonts():
    """Register TTF/OTF fonts found in assets/fonts/ and route the title /
    body / mono families to them by filename (title.ttf, body.ttf, mono.ttf).
    No-op if the folder or files are absent — system fonts are used instead.
    """
    from PyQt6.QtGui import QFontDatabase
    # Resolve the fonts dir to an ABSOLUTE path. Qt 6 silently fails to load
    # fonts from a relative path (addApplicationFont returns -1), so we must
    # pass an absolute path. Try CWD-relative first, then module-anchored.
    candidates = [
        os.path.abspath(FONTS_DIR),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), FONTS_DIR),
    ]
    fonts_dir = next((d for d in candidates if os.path.isdir(d)), None)
    if not fonts_dir:
        return
    targets = {"title": "TITLE_FONT", "body": "BODY_FONT", "mono": "MONO_FONT"}
    for fn in sorted(os.listdir(fonts_dir)):
        if not fn.lower().endswith((".ttf", ".otf")):
            continue
        stem = os.path.splitext(fn)[0].lower()
        if stem not in targets:
            continue
        path = os.path.join(fonts_dir, fn)
        fid = QFontDatabase.addApplicationFont(path)
        if fid == -1:
            # Fallback: load raw bytes (more robust on some Qt builds).
            try:
                with open(path, "rb") as fh:
                    fid = QFontDatabase.addApplicationFontFromData(fh.read())
            except OSError:
                continue
        families = QFontDatabase.applicationFontFamilies(fid)
        if families:
            globals()[targets[stem]] = families[0]


def load_image(image_name, images_dir="assets/images"):
    """Load an image as QPixmap. Returns None if not found."""
    if not image_name:
        return None
    path = os.path.join(images_dir, image_name)
    if not os.path.exists(path):
        return None
    pixmap = QPixmap(path)
    if pixmap.isNull():
        return None
    return pixmap


class CoverImage(QWidget):
    """Paints a pixmap scaled to COVER its area (center-crop), re-scaling
    automatically whenever the widget resizes — so images fill the screen
    at any window size / fullscreen. Falls back to centered placeholder text.
    """

    def __init__(self, pixmap=None, placeholder="", bg=DARK_BG,
                 ph_color="#333355", ph_size=22, fit=False, valign=0.5):
        super().__init__()
        self._pix = pixmap
        self._ph = placeholder
        self._bg = bg
        self._ph_color = ph_color
        self._ph_size = ph_size
        # fit=True  -> show the WHOLE image (contain), dark matte around it
        # fit=False -> fill the area (cover), cropping the overflow
        self._fit = fit
        # vertical crop anchor for cover mode (0=keep top, 0.5=center)
        self._valign = valign
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Expanding)

    def setPixmap(self, pixmap):
        self._pix = pixmap
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(self._bg))
        if self._pix is not None and not self._pix.isNull():
            if self._fit:
                # Contain: whole image visible, centered, dark matte around.
                scaled = self._pix.scaled(
                    self.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                x = (self.width() - scaled.width()) // 2
                y = (self.height() - scaled.height()) // 2
                painter.drawPixmap(x, y, scaled)
            else:
                # Cover: fill the area, center-crop the overflow.
                scaled = self._pix.scaled(
                    self.size(),
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
                x = (scaled.width() - self.width()) // 2
                y = int((scaled.height() - self.height()) * self._valign)
                painter.drawPixmap(-x, -y, scaled)
        elif self._ph:
            painter.setPen(QColor(self._ph_color))
            painter.setFont(QFont(BODY_FONT, self._ph_size, QFont.Weight.Bold))
            painter.drawText(
                self.rect(), Qt.AlignmentFlag.AlignCenter, self._ph
            )
        painter.end()


# ---------------------------------------------------------------------------
# Main Application
# ---------------------------------------------------------------------------

class SydneyLifeSimApp(QMainWindow):
    """Main application window managing all screens."""

    def __init__(self):
        super().__init__()
        load_custom_fonts()        # use assets/fonts/* if provided
        self.lang = "en"           # default to English; toggle to Chinese
        self.game_state = None
        self._char_bgm = None      # gameplay BGM for the current character
        self._scene_image = None   # current scene/ending CoverImage (resizable)
        self._title_logo_label = None    # title logo QLabel (resizable)
        self._title_logo_pixmap = None   # original title logo pixmap

        self.setWindowTitle("Sydney Life Simulator — 悉尼人生模拟器")
        # Resizable so the window can be maximised / fullscreen / borderless.
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setMinimumSize(WINDOW_WIDTH, WINDOW_HEIGHT)

        # --- Audio (optional) ---
        self.muted = False
        self._current_bgm = None   # filename currently loaded in the player
        self._bgm_positions = {}   # filename -> last playback position (ms)
        self._pending_seek = 0     # seek to apply once media has loaded
        self.player = None
        self.audio = None
        if HAS_AUDIO:
            self.player = QMediaPlayer()
            self.audio = QAudioOutput()
            self.player.setAudioOutput(self.audio)
            self.audio.setVolume(BGM_VOLUME)
            self.player.setLoops(QMediaPlayer.Loops.Infinite)
            self.player.mediaStatusChanged.connect(self._on_media_status)

        # Pages are responsive and fill the whole window (and the whole
        # screen in fullscreen), so images can scale up and show more.
        self._page = None
        self.show_title_screen()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def t(self, key, *args):
        """Return the UI string for *key* in the current language."""
        text = UI.get(key, {}).get(self.lang, key)
        if args:
            text = text.format(*args)
        return text

    def scene_text(self, obj, field):
        """Return bilingual scene/choice/ending text.

        Looks for ``field_en`` when language is English;
        falls back to the Chinese ``field`` if the English one is missing.
        """
        if self.lang == "en":
            en = obj.get(f"{field}_en")
            if en:
                return en
        return obj.get(field, "")

    def _set_page(self, widget):
        """Replace the current page; it fills the whole window."""
        self._page = widget
        self.setCentralWidget(widget)  # QMainWindow deletes the previous one

    # ------------------------------------------------------------------
    # Background music (optional — silent if files or QtMultimedia missing)
    # ------------------------------------------------------------------

    def play_bgm(self, filename):
        """Play/loop a track, resuming from where that track last left off.

        If the requested track is already playing it just keeps going (so
        moving between scenes never restarts the music). When switching
        tracks, the outgoing track's position is remembered, and the new
        track resumes from its own last position — the music feels
        continuous instead of restarting from zero each time.
        """
        if not HAS_AUDIO or self.player is None or not filename:
            return
        if filename == self._current_bgm:
            return  # already playing this track — let it continue
        path = os.path.join(AUDIO_DIR, filename)
        if not os.path.exists(path):
            self.stop_bgm()
            return
        # Remember the outgoing track's position so we can resume it later.
        if self._current_bgm is not None:
            self._bgm_positions[self._current_bgm] = self.player.position()
        self._current_bgm = filename
        # Seek is applied once the media reports it has loaded.
        self._pending_seek = self._bgm_positions.get(filename, 0)
        self.player.setSource(QUrl.fromLocalFile(os.path.abspath(path)))
        if not self.muted:
            self.player.play()

    def _on_media_status(self, status):
        """Seek to the remembered position once a new track has loaded."""
        if not HAS_AUDIO or self.player is None:
            return
        loaded = (QMediaPlayer.MediaStatus.LoadedMedia,
                  QMediaPlayer.MediaStatus.BufferedMedia)
        if status in loaded and self._pending_seek:
            self.player.setPosition(self._pending_seek)
            self._pending_seek = 0

    def _title_bgm(self):
        """Return the first existing title-music candidate, or None."""
        for name in TITLE_BGM_CANDIDATES:
            if os.path.exists(os.path.join(AUDIO_DIR, name)):
                return name
        return None

    def stop_bgm(self):
        """Stop any playing BGM (only used as a hard fallback)."""
        self._current_bgm = None
        if HAS_AUDIO and self.player is not None:
            self.player.stop()

    # ------------------------------------------------------------------
    # Window mode: fullscreen / borderless
    # ------------------------------------------------------------------

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_F11:
            self._toggle_fullscreen()
        elif key == Qt.Key.Key_Escape and self.isFullScreen():
            self.showNormal()
        elif key == Qt.Key.Key_F:
            self._toggle_frameless()
        else:
            super().keyPressEvent(event)

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _toggle_frameless(self):
        frameless = bool(self.windowFlags() & Qt.WindowType.FramelessWindowHint)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, not frameless)
        self.show()

    def toggle_mute(self):
        """Toggle music on/off and refresh the current screen's button."""
        self.muted = not self.muted
        if HAS_AUDIO and self.player is not None:
            if self.muted:
                self.player.pause()
            else:
                self.player.play()
        # Re-render the current screen so the button label updates.
        self._refresh_current()

    def _refresh_current(self):
        """Redraw whichever screen is currently active."""
        if self.game_state is None:
            self.show_title_screen()
        elif self.game_state.is_game_over():
            self.show_ending()
        else:
            self.show_scene()

    # ------------------------------------------------------------------
    # Reusable widget builders
    # ------------------------------------------------------------------

    def _lang_button(self, callback):
        """Small language-toggle button."""
        btn = QPushButton(self.t("lang_toggle"))
        btn.setFont(QFont(BODY_FONT, 10))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {DIM_COLOR};
                border: 1px solid {DIM_COLOR};
                border-radius: 4px; padding: 3px 10px;
            }}
            QPushButton:hover {{
                color: {TEXT_COLOR}; border-color: {TEXT_COLOR};
            }}
        """)
        btn.clicked.connect(callback)
        return btn

    def _mute_button(self):
        """Small music on/off toggle button."""
        label = self.t("music_off") if self.muted else self.t("music_on")
        btn = QPushButton(label)
        btn.setFont(QFont(BODY_FONT, 10))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        color = DIM_COLOR if self.muted else STAT_COLORS["mood"]
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {color};
                border: 1px solid {color};
                border-radius: 4px; padding: 3px 10px;
            }}
            QPushButton:hover {{
                color: {TEXT_COLOR}; border-color: {TEXT_COLOR};
            }}
        """)
        btn.clicked.connect(self.toggle_mute)
        return btn

    def _accent_label(self, text, size=18):
        lbl = QLabel(text)
        lbl.setFont(QFont(BODY_FONT, size, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {ACCENT_COLOR}; background: transparent;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return lbl

    def _action_button(self, text, callback, *, width=None,
                       accent=False, disabled=False, center=False):
        """General purpose styled button."""
        btn = QPushButton(text)
        btn_font = QFont(BODY_FONT, 13, QFont.Weight.Medium)
        btn_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.0)
        btn.setFont(btn_font)
        if width:
            btn.setFixedWidth(width)
        if disabled:
            btn.setEnabled(False)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {DISABLED_BG}; color: {DISABLED_COLOR};
                    border: none; border-radius: 6px;
                    padding: 10px 18px; text-align: left;
                }}
            """)
        else:
            bg = ACCENT_COLOR if accent else CARD_BG
            align = "center" if center else "left"
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {bg}; color: {TEXT_COLOR};
                    border: none; border-radius: 6px;
                    padding: 10px 18px; text-align: {align};
                }}
                QPushButton:hover {{
                    background: {ACCENT_COLOR}; color: white;
                }}
            """)
            btn.clicked.connect(callback)
        return btn

    def _scroll_label(self, text):
        """Scrollable text area containing a QLabel."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background: {BG_COLOR}; border: none;
            }}
            QScrollBar:vertical {{
                background: {BG_COLOR}; width: 8px;
            }}
            QScrollBar::handle:vertical {{
                background: #333355; border-radius: 4px;
                min-height: 30px;
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{ height: 0; }}
        """)
        lbl = QLabel(text)
        lbl.setFont(QFont(BODY_FONT, 13))
        lbl.setStyleSheet(
            f"color: {TEXT_COLOR}; background: {BG_COLOR}; "
            f"padding: 6px 30px;"
        )
        lbl.setWordWrap(True)
        lbl.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        scroll.setWidget(lbl)
        return scroll

    def _stats_bar(self):
        """Horizontal stats bar widget."""
        bar = QFrame()
        bar.setStyleSheet(f"background: {STATS_BG};")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 8, 20, 8)

        names = {
            "money": self.t("money"), "visa": self.t("visa"),
            "skill": self.t("skill"), "mood": self.t("mood"),
        }

        for key in ["money", "visa", "skill", "mood"]:
            value = self.game_state.stats[key]
            color = STAT_COLORS[key]

            group = QHBoxLayout()
            group.setSpacing(4)

            name_lbl = QLabel(names[key])
            name_lbl.setFont(QFont(MONO_FONT, 11, QFont.Weight.Bold))
            name_lbl.setStyleSheet(
                f"color: {color}; background: transparent;"
            )
            group.addWidget(name_lbl)

            # Bar background
            bar_bg = QFrame()
            bar_bg.setFixedSize(80, 10)
            bar_bg.setStyleSheet(
                "background: #333333; border-radius: 3px;"
            )
            # Filled portion
            fill_w = max(1, int(80 * value / 10)) if value > 0 else 0
            if fill_w:
                bar_fill = QFrame(bar_bg)
                bar_fill.setGeometry(0, 0, fill_w, 10)
                bar_fill.setStyleSheet(
                    f"background: {color}; border-radius: 3px;"
                )
            group.addWidget(bar_bg)

            val_lbl = QLabel(str(value))
            val_lbl.setFont(QFont(MONO_FONT, 11, QFont.Weight.Bold))
            val_lbl.setStyleSheet(
                f"color: {color}; background: transparent;"
            )
            group.addWidget(val_lbl)

            layout.addLayout(group)

        return bar

    def _add_glow(self, widget, color, blur=20, dx=0, dy=2):
        """Attach a soft drop-shadow/glow to a widget (cinematic text)."""
        effect = QGraphicsDropShadowEffect(self)
        effect.setBlurRadius(blur)
        effect.setColor(QColor(color))
        effect.setOffset(dx, dy)
        widget.setGraphicsEffect(effect)

    # ==================================================================
    # Title Screen
    # ==================================================================

    def show_title_screen(self):
        self._scene_image = None
        self._title_logo_label = None
        self.play_bgm(self._title_bgm())
        page = QWidget()
        page.setStyleSheet(f"background: {BG_COLOR};")
        grid = QGridLayout(page)
        grid.setContentsMargins(0, 0, 0, 0)

        # Optional full-bleed background image + dark scrim for readability.
        # CoverImage fills the whole window/screen at any size.
        bg = load_image("title_bg.png")
        if bg:
            grid.addWidget(CoverImage(bg), 0, 0)
            scrim = QLabel()
            scrim.setStyleSheet("background: rgba(15, 15, 26, 0.55);")
            grid.addWidget(scrim, 0, 0)

        # Foreground content (transparent so the image shows through)
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(content)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Music + language toggles — top-right
        top = QHBoxLayout()
        top.addStretch()
        top.addWidget(self._mute_button())
        top.addWidget(self._lang_button(self._toggle_lang_title))
        lay.addLayout(top)

        lay.addSpacing(60)

        # -- Title: prefer a pre-rendered logo PNG (language-specific if
        #    provided), else styled text. --
        logo = load_image(f"title_logo_{self.lang}.png") or load_image("title_logo.png")
        if logo:
            logo_label = QLabel()
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            logo_label.setStyleSheet("background: transparent;")
            self._title_logo_label = logo_label
            self._title_logo_pixmap = logo
            self._fit_title_logo()
            lay.addWidget(logo_label, alignment=Qt.AlignmentFlag.AlignCenter)
        else:
            # Single title in the current language only (no cross-language line)
            title = QLabel(self.t("title_main"))
            title_font = QFont(TITLE_FONT, 44, QFont.Weight.Bold)
            title_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2)
            title.setFont(title_font)
            title.setStyleSheet(f"color: {ACCENT_COLOR}; background: transparent;")
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._add_glow(title, ACCENT_COLOR, blur=28)
            lay.addWidget(title)

        tag = QLabel(self.t("tagline"))
        tag_font = QFont(TITLE_FONT, 16)
        tag_font.setItalic(True)
        tag_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.5)
        tag.setFont(tag_font)
        tag.setStyleSheet("color: #d8d4c8; background: transparent;")
        tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._add_glow(tag, "#000000", blur=10)
        lay.addWidget(tag)

        lay.addSpacing(48)

        # Buttons
        new_btn = self._action_button(
            self.t("new_game"), self.show_character_select,
            width=260, center=True,
        )
        lay.addWidget(new_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        if has_save():
            cont_btn = self._action_button(
                self.t("continue"), self.continue_game,
                width=260, center=True,
            )
            lay.addWidget(cont_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        lay.addSpacing(12)

        quit_btn = QPushButton(self.t("quit"))
        quit_btn.setFont(QFont(BODY_FONT, 11))
        quit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        quit_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {DIM_COLOR};
                border: none; padding: 6px;
            }}
            QPushButton:hover {{ color: {TEXT_COLOR}; }}
        """)
        quit_btn.clicked.connect(self.close)
        lay.addWidget(quit_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        lay.addStretch()

        # Window-mode hint (fullscreen / borderless)
        hint = QLabel(self.t("fs_hint"))
        hint.setFont(QFont(BODY_FONT, 10))
        hint.setStyleSheet("color: #6a6a85; background: transparent;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(hint)
        lay.addSpacing(10)

        grid.addWidget(content, 0, 0)
        self._set_page(page)

    def _toggle_lang_title(self):
        self.lang = "en" if self.lang == "zh" else "zh"
        self.show_title_screen()

    # ==================================================================
    # Character Select Screen
    # ==================================================================

    def show_character_select(self):
        self._scene_image = None
        page = QWidget()
        page.setStyleSheet(f"background: {BG_COLOR};")
        lay = QVBoxLayout(page)

        # Top bar
        top = QHBoxLayout()
        back = QPushButton(self.t("back"))
        back.setFont(QFont(BODY_FONT, 11))
        back.setCursor(Qt.CursorShape.PointingHandCursor)
        back.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {DIM_COLOR}; border: none;
            }}
            QPushButton:hover {{ color: {TEXT_COLOR}; }}
        """)
        back.clicked.connect(self.show_title_screen)
        top.addWidget(back)
        top.addStretch()
        top.addWidget(self._mute_button())
        top.addWidget(self._lang_button(self._toggle_lang_select))
        lay.addLayout(top)

        # Art-styled title with glow
        title = QLabel(self.t("select_char"))
        tf = QFont(TITLE_FONT, 30, QFont.Weight.Bold)
        tf.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2)
        title.setFont(tf)
        title.setStyleSheet(f"color: {ACCENT_COLOR}; background: transparent;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._add_glow(title, ACCENT_COLOR, blur=24)
        lay.addWidget(title)
        lay.addSpacing(10)

        # 2x2 portrait grid that expands to fill the screen
        grid_w = QWidget()
        grid_w.setStyleSheet("background: transparent;")
        grid = QGridLayout(grid_w)
        grid.setContentsMargins(20, 0, 20, 0)
        grid.setSpacing(18)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setRowStretch(0, 1)
        grid.setRowStretch(1, 1)
        for i, char_data in enumerate(get_character_descriptions()):
            char_id, zh_name, zh_sub, zh_desc = char_data
            if self.lang == "en" and char_id in EN_CHAR_DESC:
                name, subtitle, desc = EN_CHAR_DESC[char_id]
            else:
                name, subtitle, desc = zh_name, zh_sub, zh_desc
            r, c = divmod(i, 2)
            grid.addWidget(
                self._portrait_card(char_id, name, subtitle, desc), r, c
            )
        lay.addWidget(grid_w, stretch=1)
        self._set_page(page)

    def _toggle_lang_select(self):
        self.lang = "en" if self.lang == "zh" else "zh"
        self.show_character_select()

    def _portrait_card(self, char_id, name, subtitle, desc):
        """Expanding character card: portrait (scales with the card) + text."""
        card = QFrame()
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Expanding)
        card.setStyleSheet(f"""
            QFrame {{
                background: {CARD_BG}; border-radius: 10px;
            }}
            QFrame:hover {{
                background: {CARD_HOVER};
            }}
        """)

        h = QHBoxLayout(card)
        h.setContentsMargins(14, 14, 14, 14)
        h.setSpacing(14)

        # Portrait — CoverImage that scales to fill its share of the card
        portrait = load_image(f"portrait_{char_id}.png")
        pic = CoverImage(portrait, placeholder=name.split()[0], ph_size=18)
        pic.setMinimumWidth(110)
        h.addWidget(pic, stretch=2)

        # Text (right)
        col = QVBoxLayout()
        col.setSpacing(5)
        n = QLabel(name)
        n.setFont(QFont(BODY_FONT, 16, QFont.Weight.Bold))
        n.setStyleSheet(f"color: {ACCENT_COLOR}; background: transparent;")
        col.addWidget(n)
        s = QLabel(subtitle)
        s.setFont(QFont(BODY_FONT, 11))
        s.setStyleSheet(f"color: {DIM_COLOR}; background: transparent;")
        s.setWordWrap(True)
        col.addWidget(s)
        d = QLabel(desc)
        d.setFont(QFont(BODY_FONT, 11))
        d.setStyleSheet(f"color: {TEXT_COLOR}; background: transparent;")
        d.setWordWrap(True)
        col.addWidget(d)
        col.addStretch()

        stats = get_starting_stats(char_id)
        stat_names = {
            "money": self.t("money"), "visa": self.t("visa"),
            "skill": self.t("skill"), "mood": self.t("mood"),
        }
        stats_str = "  ".join(
            f"{stat_names[k]} {stats[k]}" for k in ["money", "visa", "skill", "mood"]
        )
        st = QLabel(stats_str)
        st.setFont(QFont(MONO_FONT, 11, QFont.Weight.Bold))
        st.setStyleSheet(f"color: {DIM_COLOR}; background: transparent;")
        col.addWidget(st)

        h.addLayout(col, stretch=3)

        card.mousePressEvent = lambda ev, cid=char_id: self.start_game(cid)
        return card

    # ==================================================================
    # Game Screen
    # ==================================================================

    def start_game(self, char_id):
        try:
            scenes, endings = load_scenes(char_id)
        except FileNotFoundError:
            return
        delete_save()
        self.game_state = GameState(char_id, scenes, endings)
        self._char_bgm = load_character_bgm(char_id)
        self.show_scene()

    def continue_game(self):
        try:
            self.game_state = load_game()
            self._char_bgm = load_character_bgm(self.game_state.char_id)
            if self.game_state.is_game_over():
                self.show_ending()
            else:
                self.show_scene()
        except (FileNotFoundError, KeyError, ValueError):
            self.show_title_screen()

    def show_scene(self):
        scene = self.game_state.get_current_scene()
        if scene is None:
            self.show_ending()
            return

        # Gameplay BGM: a scene may override the character's default track
        # (e.g. a cold cue during the smear, a hopeful one during healing).
        self.play_bgm(scene.get("bgm") or self._char_bgm)

        page = QWidget()
        page.setStyleSheet(f"background: {BG_COLOR};")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # -- Image (fills width at 16:9, height capped) --
        lay.addWidget(self._image_area(scene))

        # -- Stats --
        lay.addWidget(self._stats_bar())

        # -- Title + lang toggle --
        title_row = QHBoxLayout()
        title_row.setContentsMargins(30, 12, 30, 0)
        title_text = self.scene_text(scene, "title")
        if title_text:
            tl = QLabel(title_text)
            tl.setFont(QFont(BODY_FONT, 18, QFont.Weight.Bold))
            tl.setStyleSheet(f"color: {ACCENT_COLOR}; background: transparent;")
            title_row.addWidget(tl)
        title_row.addStretch()
        title_row.addWidget(self._mute_button())
        title_row.addWidget(self._lang_button(self._toggle_lang_scene))
        lay.addLayout(title_row)

        # -- Narrative (fills the remaining space) --
        narrative = self.scene_text(scene, "narrative")
        lay.addWidget(self._scroll_label(narrative), stretch=1)

        # -- Choices --
        choices_w = QWidget()
        choices_w.setStyleSheet(f"background: {BG_COLOR};")
        cl = QVBoxLayout(choices_w)
        cl.setContentsMargins(30, 4, 30, 15)
        cl.setSpacing(6)

        for idx, choice, available in self.game_state.get_available_choices():
            text = self.scene_text(choice, "text") or f"Choice {idx + 1}"
            if not available:
                req = choice.get("requirement", {})
                parts = [f"{self.t(k)}>={v}" for k, v in req.items()]
                text = f"[{self.t('requires')} {' & '.join(parts)}] {text}"
            btn = self._action_button(
                text,
                (lambda *_a, i=idx: self._on_choice(i)),
                disabled=not available,
            )
            cl.addWidget(btn)

        lay.addWidget(choices_w)
        self._set_page(page)

    def _image_area(self, data):
        """A 16:9 cover-image that fills the full width (no side matte),
        height capped so the text below stays usable. Cropping is biased
        toward the top so characters' heads are kept."""
        pixmap = load_image(data.get("image", ""))
        if pixmap:
            img = CoverImage(pixmap, valign=0.25)  # fill width, keep heads
        else:
            if "narrative" in data:
                ch = self.game_state.current_scene_index + 1
                total = len(self.game_state.scenes)
                char_name = get_character_display_name(self.game_state.char_id)
                text = f"{self.t('ch_of', ch, total)}\n{char_name}"
            else:
                text = self.t("ending_label")
            img = CoverImage(None, placeholder=text)
        self._scene_image = img
        self._fit_scene_image_height()
        return img

    def _fit_scene_image_height(self):
        """Size the scene/ending image to ~16:9 of the full width, capped
        so ~320px stays free for the text and choices below."""
        img = self._scene_image
        if img is None:
            return
        try:
            ideal = int(self.width() * 9 / 16)        # full-width 16:9
            cap = max(240, self.height() - 320)        # leave room below
            img.setFixedHeight(max(240, min(ideal, cap)))
        except RuntimeError:
            self._scene_image = None

    def _fit_title_logo(self):
        """Scale the title logo responsively into a box ~46% wide / ~26% tall
        of the window, keeping aspect ratio, so it looks right at any size."""
        label = self._title_logo_label
        pix = self._title_logo_pixmap
        if label is None or pix is None:
            return
        try:
            box_w = max(520, min(int(self.width() * 0.62), 1000))
            box_h = max(120, int(self.height() * 0.30))
            label.setPixmap(pix.scaled(
                box_w, box_h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))
        except RuntimeError:
            self._title_logo_label = None

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_scene_image_height()
        self._fit_title_logo()

    def _on_choice(self, idx):
        self.game_state.make_choice(idx)
        save_game(self.game_state)
        if self.game_state.is_game_over():
            self.show_ending()
        else:
            self.show_scene()

    def _toggle_lang_scene(self):
        self.lang = "en" if self.lang == "zh" else "zh"
        if self.game_state.is_game_over():
            self.show_ending()
        else:
            self.show_scene()

    # ==================================================================
    # Ending Screen
    # ==================================================================

    def show_ending(self):
        try:
            ending = self.game_state.get_ending()
        except RuntimeError:
            self.show_title_screen()
            return

        # Switch to this ending's BGM (different mood per ending).
        self.play_bgm(ending.get("bgm"))

        page = QWidget()
        page.setStyleSheet(f"background: {BG_COLOR};")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Image (fills width at 16:9, height capped)
        lay.addWidget(self._image_area(ending))

        # Stats
        lay.addWidget(self._stats_bar())

        # Title + tier + toggles
        title_row = QHBoxLayout()
        title_row.setContentsMargins(40, 15, 40, 0)
        tl = QLabel(self.scene_text(ending, "title"))
        tl.setFont(QFont(BODY_FONT, 18, QFont.Weight.Bold))
        tl.setStyleSheet(f"color: {ACCENT_COLOR}; background: transparent;")
        title_row.addWidget(tl)

        tier = self.scene_text(ending, "tier")
        if tier:
            tier_lbl = QLabel(f"【{tier}】")
            tier_lbl.setFont(QFont(BODY_FONT, 14, QFont.Weight.Bold))
            tier_lbl.setStyleSheet(
                f"color: {STAT_COLORS['money']}; background: transparent;"
            )
            title_row.addWidget(tier_lbl)

        title_row.addStretch()
        title_row.addWidget(self._mute_button())
        title_row.addWidget(self._lang_button(self._toggle_lang_scene))
        lay.addLayout(title_row)

        # Verdict line (italic-ish, dimmed accent)
        verdict = self.scene_text(ending, "verdict")
        if verdict:
            vl = QLabel(f"“{verdict}”")
            vl.setFont(QFont(BODY_FONT, 13))
            vl.setStyleSheet(
                f"color: {DIM_COLOR}; background: transparent; padding: 0 40px;"
            )
            vl.setWordWrap(True)
            lay.addWidget(vl)

        # Text
        lay.addWidget(
            self._scroll_label(self.scene_text(ending, "text")),
            stretch=1,
        )

        # Bottom buttons
        btn_w = QWidget()
        btn_w.setStyleSheet(f"background: {BG_COLOR};")
        bl = QHBoxLayout(btn_w)
        bl.setContentsMargins(30, 8, 30, 18)
        bl.addStretch()
        bl.addWidget(self._action_button(
            self.t("trajectory"), self.show_trajectory, width=180, center=True,
        ))
        bl.addWidget(self._action_button(
            self.t("restart"), self._restart, width=150, center=True,
        ))
        bl.addWidget(self._action_button(
            self.t("to_title"), self.show_title_screen, width=150, center=True,
        ))
        bl.addStretch()
        lay.addWidget(btn_w)

        self._set_page(page)

    # ==================================================================
    # Choice Trajectory Screen
    # ==================================================================

    def _history_items(self):
        """Resolve history into (title, chosen_text, [alt_texts]) tuples."""
        scene_by_id = {s.get("id"): s for s in self.game_state.scenes}
        items = []
        for scene_id, choice_id in self.game_state.history:
            scene = scene_by_id.get(scene_id, {})
            title = self.scene_text(scene, "title") or scene_id
            chosen = choice_id
            alts = []
            for c in scene.get("choices", []):
                txt = self.scene_text(c, "text") or c.get("id", "")
                # keep only the short label before the em-dash separator
                txt = txt.split(" —— ")[0].split(" — ")[0].strip()
                if c.get("id") == choice_id:
                    chosen = txt
                else:
                    alts.append(txt)
            items.append((title, chosen, alts))
        return items

    def show_trajectory(self):
        """Display the chain of choices the player made this run."""
        page = QWidget()
        page.setStyleSheet(f"background: {BG_COLOR};")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Header
        header_row = QHBoxLayout()
        header_row.setContentsMargins(30, 20, 30, 5)
        h = QLabel(self.t("your_path"))
        h.setFont(QFont(BODY_FONT, 20, QFont.Weight.Bold))
        h.setStyleSheet(f"color: {ACCENT_COLOR}; background: transparent;")
        header_row.addWidget(h)
        header_row.addStretch()
        header_row.addWidget(self._lang_button(self._toggle_lang_traj))
        lay.addLayout(header_row)

        # Scrollable node chain
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background: {BG_COLOR}; border: none; }}
            QScrollBar:vertical {{ background: {BG_COLOR}; width: 8px; }}
            QScrollBar::handle:vertical {{
                background: #333355; border-radius: 4px; min-height: 30px;
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{ height: 0; }}
        """)
        inner = QWidget()
        inner.setStyleSheet(f"background: {BG_COLOR};")
        inner_lay = QVBoxLayout(inner)
        inner_lay.setContentsMargins(40, 10, 40, 10)
        inner_lay.setSpacing(0)

        items = self._history_items()
        for i, (title, chosen, alts) in enumerate(items, start=1):
            inner_lay.addWidget(
                self._traj_node(i, title, chosen, alts, is_last=(i == len(items)))
            )

        inner_lay.addStretch()
        scroll.setWidget(inner)
        lay.addWidget(scroll, stretch=1)

        # Back button
        btn_w = QWidget()
        btn_w.setStyleSheet(f"background: {BG_COLOR};")
        bl = QHBoxLayout(btn_w)
        bl.setContentsMargins(30, 8, 30, 18)
        bl.addStretch()
        bl.addWidget(self._action_button(
            self.t("back_ending"), self.show_ending, width=200, center=True,
        ))
        bl.addStretch()
        lay.addWidget(btn_w)

        self._set_page(page)

    def _traj_node(self, number, title, chosen, alts, is_last=False):
        """A decision-tree node: numbered dot + chosen branch + dimmed alts,
        connected to the next node by a vertical line on the left."""
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(12)
        rl.setAlignment(Qt.AlignmentFlag.AlignTop)

        # -- Left rail: number badge + connecting line --
        rail = QWidget()
        rail.setFixedWidth(30)
        rail.setStyleSheet("background: transparent;")
        rail_lay = QVBoxLayout(rail)
        rail_lay.setContentsMargins(0, 0, 0, 0)
        rail_lay.setSpacing(0)
        rail_lay.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        badge = QLabel(str(number))
        badge.setFixedSize(30, 30)
        badge.setFont(QFont(BODY_FONT, 12, QFont.Weight.Bold))
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(
            f"color: white; background: {ACCENT_COLOR}; border-radius: 15px;"
        )
        rail_lay.addWidget(badge, alignment=Qt.AlignmentFlag.AlignHCenter)

        if not is_last:
            line = QFrame()
            line.setFixedWidth(2)
            line.setStyleSheet(f"background: {ACCENT_COLOR};")
            rail_lay.addWidget(line, stretch=1,
                               alignment=Qt.AlignmentFlag.AlignHCenter)
        rl.addWidget(rail)

        # -- Right: chapter title, chosen branch (highlight), alts (dim) --
        box = QVBoxLayout()
        box.setSpacing(4)

        t = QLabel(title)
        t.setFont(QFont(BODY_FONT, 10))
        t.setStyleSheet(f"color: {DIM_COLOR}; background: transparent;")
        box.addWidget(t)

        # Chosen branch — highlighted pill
        chosen_lbl = QLabel("● " + chosen)
        chosen_lbl.setFont(QFont(BODY_FONT, 12, QFont.Weight.Bold))
        chosen_lbl.setStyleSheet(f"""
            color: white; background: {CARD_BG};
            border-left: 3px solid {ACCENT_COLOR};
            border-radius: 6px; padding: 7px 12px;
        """)
        chosen_lbl.setWordWrap(True)
        box.addWidget(chosen_lbl)

        # Alternatives — dimmed branches
        for a in alts:
            alt = QLabel("○ " + a)
            alt.setFont(QFont(BODY_FONT, 11))
            alt.setStyleSheet(
                f"color: {DISABLED_COLOR}; background: transparent; "
                f"padding: 1px 12px;"
            )
            alt.setWordWrap(True)
            box.addWidget(alt)

        # Spacer below to give the connecting line some length
        if not is_last:
            box.addSpacing(10)

        rl.addLayout(box, stretch=1)
        return row

    def _toggle_lang_traj(self):
        self.lang = "en" if self.lang == "zh" else "zh"
        self.show_trajectory()

    def _restart(self):
        cid = self.game_state.char_id
        delete_save()
        self.start_game(cid)

    # ==================================================================
    # Run (compatibility wrapper)
    # ==================================================================

    def run(self):
        """Show the window. QApplication.exec() is called in main.py."""
        self.show()
