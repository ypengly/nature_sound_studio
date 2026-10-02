"""A single Qt stylesheet string: dark background, rounded cards, soft accents."""

DARK_STYLE = """
QWidget { background-color: #14161c; color: #e7e9ee; font-size: 13px; }
QMainWindow { background-color: #14161c; }
QLabel#Header { font-size: 22px; font-weight: 700; color: #ffffff; }
QLabel#SubHeader { color: #9ba1ad; font-size: 13px; }
QLabel#SectionTitle { font-size: 15px; font-weight: 600; color: #ffffff; padding-top: 4px; }

QFrame#Card {
    background-color: #1d2029;
    border-radius: 14px;
    border: 1px solid #2a2e3a;
}
QFrame#Card:hover { border: 1px solid #5b7cfa; }

QPushButton {
    background-color: #262a36; color: #e7e9ee; border-radius: 8px;
    padding: 6px 14px; border: 1px solid #343947;
}
QPushButton:hover { background-color: #313644; }
QPushButton:pressed { background-color: #20232c; }
QPushButton#Primary {
    background-color: #5b7cfa; color: #0d0f14; font-weight: 600; border: none;
}
QPushButton#Primary:hover { background-color: #7291ff; }
QPushButton#Primary:disabled { background-color: #333a4d; color: #7b8296; }
QPushButton#Danger { background-color: #3a2028; border: 1px solid #5c2b36; color: #ff9aab; }
QPushButton#Danger:hover { background-color: #4a2530; }
QPushButton#Icon { border: none; background: transparent; font-size: 16px; padding: 2px; }
QPushButton#Toggle:checked { background-color: #5b7cfa; color: #0d0f14; border: none; }

QSlider::groove:horizontal { height: 5px; background: #2a2e3a; border-radius: 2px; }
QSlider::sub-page:horizontal { background: #5b7cfa; border-radius: 2px; }
QSlider::handle:horizontal {
    width: 15px; margin: -6px 0; border-radius: 7px; background: #e7e9ee;
}

QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {
    background-color: #262a36; border: 1px solid #343947; border-radius: 7px;
    padding: 5px 8px; color: #e7e9ee;
}
QComboBox QAbstractItemView { background-color: #262a36; selection-background-color: #5b7cfa; }

QScrollArea { border: none; }
QProgressBar {
    background-color: #262a36; border-radius: 7px; text-align: center;
    color: #e7e9ee; height: 16px; border: 1px solid #343947;
}
QProgressBar::chunk { background-color: #5b7cfa; border-radius: 7px; }

QTabWidget::pane { border: 1px solid #2a2e3a; border-radius: 10px; top: -1px; }
QTabBar::tab {
    background: #1d2029; padding: 8px 18px; margin-right: 4px;
    border-top-left-radius: 8px; border-top-right-radius: 8px; color: #9ba1ad;
}
QTabBar::tab:selected { background: #262a36; color: #ffffff; }

QListWidget { background-color: transparent; border: none; }
QToolTip { background-color: #262a36; color: #e7e9ee; border: 1px solid #343947; }
"""
