import sys
import json
import random
import sqlite3
from datetime import datetime
import numpy as np
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGridLayout, QLabel, QFrame,
    QGroupBox, QVBoxLayout, QPushButton, QDockWidget, QHBoxLayout,
    QSlider, QRadioButton, QProgressBar, QStatusBar, QMessageBox, QFileDialog,
    QInputDialog, QDialog, QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QIcon


DB_FILENAME = "scores.db"


def init_db():
    conn = sqlite3.connect(DB_FILENAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name TEXT,
            time_seconds INTEGER,
            mistakes INTEGER,
            hints_used INTEGER,
            filled_cells INTEGER,
            empty_cells INTEGER,
            date TEXT
        )
    """)
    conn.commit()
    conn.close()


class SudokuGame:
    def __init__(self):
        self.BASE = 3
        self.SIDE = 9
        self.solution_board = None
        self.game_board = None
        self.immutable_cells = set()
        self.mistakes = 0
        self.max_mistakes = 5
        self.hints_used = 0
        self.empty_cells = 40

    def generate_sudoku(self):
        def pattern(r, c):
            return (self.BASE * (r % self.BASE) + r // self.BASE + c) % self.SIDE

        def shuffle(s):
            return random.sample(s, len(s))

        r_base = range(self.BASE)
        rows = [g * self.BASE + r for g in shuffle(r_base) for r in shuffle(r_base)]
        cols = [g * self.BASE + c for g in shuffle(r_base) for c in shuffle(r_base)]
        nums = shuffle(list(range(1, self.SIDE + 1)))
        board = np.array([[nums[pattern(r, c)] for c in cols] for r in rows])
        return board

    def create_game_board(self, empty_cells=40):
        self.solution_board = self.generate_sudoku()
        self.game_board = self.solution_board.copy().astype(object)
        all_cells = [(i, j) for i in range(9) for j in range(9)]
        cells_to_empty = random.sample(all_cells, min(empty_cells, 81))
        self.immutable_cells = set(all_cells) - set(cells_to_empty)
        for r, c in cells_to_empty:
            self.game_board[r][c] = ""
        self.empty_cells = empty_cells
        self.mistakes = 0
        self.hints_used = 0
        return self.game_board

    def is_valid_move(self, row, col, num):
        if self.solution_board is None:
            return False
        if (row, col) in self.immutable_cells:
            return False
        return int(self.solution_board[row][col]) == int(num)

    def get_hint(self):
        for i in range(9):
            for j in range(9):
                if self.game_board[i][j] == "":
                    return (i, j, int(self.solution_board[i][j]))
        return None

    def check_solution(self):
        for i in range(9):
            for j in range(9):
                if (i, j) not in self.immutable_cells:
                    if str(self.game.game_board[i][j]) != str(self.solution_board[i][j]):
                        return False
        return True

    def get_filled_count(self):
        count = 0
        for i in range(9):
            for j in range(9):
                if self.game_board[i][j] != "":
                    count += 1
        return count

class SudokuCell(QLabel):
    clicked = Signal(int, int)

    def __init__(self, row, col, value=""):
        super().__init__(str(value) if value != "" else "")
        self.row = row
        self.col = col
        self.value = value
        self.is_immutable = False
        self.is_error = False
        self.is_selected = False
        self.is_hint = False

        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.update_style()

    def update_style(self):
        base_style = ""
        base_style += "font-family: 'Arial';"
        base_style += f"font-size: {28 if self.is_immutable else 24}px;"
        base_style += "border-style: solid;"

        if self.is_immutable:
            base_style += "background-color: #e0f7fa; color: #00796b; font-weight: bold;"
        elif self.is_error:
            base_style += "background-color: #ffcdd2; color: #b71c1c;"
        elif self.is_selected:
            base_style += "background-color: #b2ebf2; border: 3px solid #00bcd4;"
        elif self.is_hint:
            base_style += "background-color: #fff9c4; border: 2px dashed #fbc02d;"
        else:
            base_style += "background-color: #ffffff; color: #000000;"

        top = 4 if self.row % 3 == 0 else 1
        left = 4 if self.col % 3 == 0 else 1
        bottom = 4 if self.row == 8 else 1
        right = 4 if self.col == 8 else 1
        base_style += f"border-top: {top}px solid #333;"
        base_style += f"border-left: {left}px solid #333;"
        base_style += f"border-bottom: {bottom}px solid #333;"
        base_style += f"border-right: {right}px solid #333;"

        self.setStyleSheet(base_style)

    def mousePressEvent(self, event):
        self.clicked.emit(self.row, self.col)

    def set_value(self, value, is_immutable=False):
        self.value = value
        self.is_immutable = bool(is_immutable)
        self.setText(str(value) if value != "" else "")
        self.is_error = False
        self.is_hint = False
        self.update_style()

    def set_selected(self, selected):
        self.is_selected = bool(selected)
        self.update_style()

    def set_error(self, error):
        self.is_error = bool(error)
        self.update_style()

    def set_hint(self, hint):
        self.is_hint = bool(hint)
        self.update_style()

class ScoresDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Scores")
        self.resize(800, 400)
        layout = QVBoxLayout(self)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ID", "Player", "Time", "Mistakes", "Hints", "Filled", "Date"
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        self.load_data()

    def load_data(self):
        conn = sqlite3.connect(DB_FILENAME)
        c = conn.cursor()
        c.execute("SELECT id, player_name, time_seconds, mistakes, hints_used, filled_cells, date FROM scores ORDER BY time_seconds ASC, date ASC")
        rows = c.fetchall()
        conn.close()

        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            id_, name, tsec, mistakes, hints, filled, date_text = row
            h = tsec // 3600
            m = (tsec % 3600) // 60
            s = tsec % 60
            time_str = f"{h:02d}:{m:02d}:{s:02d}"
            vals = [str(id_), name, time_str, str(mistakes), str(hints), f"{filled}/81", date_text]
            for cidx, v in enumerate(vals):
                item = QTableWidgetItem(v)
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                self.table.setItem(r, cidx, item)

class SudokuMaster(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sudoku Master Pro")
        self.setGeometry(100, 100, 1400, 950)

        self.game = SudokuGame()
        self.selected_cell = None
        self.timer = QTimer(self)
        self.seconds = 0
        self.is_timer_running = False

        central = QWidget()
        self.setCentralWidget(central)
        self.main_layout = QGridLayout(central)
        self.main_layout.setColumnStretch(0, 1)
        self.main_layout.setColumnStretch(1, 0)

        title = QLabel("Sudoku Master Pro")
        title.setObjectName("lblTitle")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Segoe UI", 28, QFont.Bold))
        self.main_layout.addWidget(title, 0, 0, 1, 2)

        self.board_frame = QFrame()
        self.board_frame.setObjectName("gameBoardFrame")
        self.board_frame.setMinimumSize(700, 700)
        self.board_layout = QGridLayout(self.board_frame)
        self.board_layout.setSpacing(0)
        self.board_layout.setContentsMargins(0, 0, 0, 0)

        self.cells = []
        for r in range(9):
            row_cells = []
            for c in range(9):
                cell = SudokuCell(r, c)
                cell.clicked.connect(self.cell_clicked)
                self.board_layout.addWidget(cell, r, c)
                row_cells.append(cell)
            self.cells.append(row_cells)
        self.main_layout.addWidget(self.board_frame, 1, 0)

        self.create_control_panel(self.main_layout)

        self.create_dock_widget()

        self.setStatusBar(QStatusBar())
        self.lbl_status = QLabel("Welcome to Sudoku Master Pro. Select a cell and choose a number.")
        self.progressBar = QProgressBar()
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(81)
        self.progressBar.setFormat("%p% (%v/81 cells)")
        status_layout = QHBoxLayout()
        status_layout.addWidget(self.lbl_status)
        status_layout.addWidget(self.progressBar)
        status_frame = QWidget()
        status_frame.setLayout(status_layout)
        self.main_layout.addWidget(status_frame, 3, 0, 1, 2)

        self.timer.timeout.connect(self.update_timer)

        self.setStyleSheet(self.global_stylesheet())

        self.new_game()

    def keyPressEvent(self, event):
        if not self.selected_cell:
            return
        text = event.text()
        if text and text in "123456789":
            self.number_clicked(int(text))
            return
        key = event.key()
        if key in (Qt.Key_Backspace, Qt.Key_Delete):
            self.number_clicked("")
            return
        if key == Qt.Key_Escape:
            pr, pc = self.selected_cell
            self.cells[pr][pc].set_selected(False)
            self.selected_cell = None

    def create_control_panel(self, main_layout):
        control_group = QGroupBox("Game Controls")
        control_layout = QVBoxLayout()

        self.btn_new = QPushButton("New Game")
        self.btn_new.setObjectName("btnNewGame")
        self._try_set_icon(self.btn_new, "document-new")
        self.btn_new.clicked.connect(self.new_game)
        control_layout.addWidget(self.btn_new)

        self.btn_load = QPushButton("Load Game")
        self._try_set_icon(self.btn_load, "document-open")
        self.btn_save = QPushButton("Save Game")
        self._try_set_icon(self.btn_save, "document-save")
        self.btn_load.clicked.connect(self.load_game)
        self.btn_save.clicked.connect(self.save_game)
        control_layout.addWidget(self.btn_load)
        control_layout.addWidget(self.btn_save)

        self.btn_scores = QPushButton("Show Scores")
        self._try_set_icon(self.btn_scores, "view-list")
        self.btn_scores.clicked.connect(self.show_scores)
        control_layout.addWidget(self.btn_scores)

        difficulty = QGroupBox("Difficulty Level")
        diff_layout = QVBoxLayout()
        self.rbEasy = QRadioButton("Easy (35-40 cells given)")
        self.rbMedium = QRadioButton("Medium (30-35 cells given)")
        self.rbHard = QRadioButton("Hard (25-30 cells given)")
        self.rbExpert = QRadioButton("Expert (20-25 cells given)")
        self.rbMedium.setChecked(True)
        diff_layout.addWidget(self.rbEasy)
        diff_layout.addWidget(self.rbMedium)
        diff_layout.addWidget(self.rbHard)
        diff_layout.addWidget(self.rbExpert)
        difficulty.setLayout(diff_layout)
        control_layout.addWidget(difficulty)

        empty_group = QGroupBox("Empty Cells")
        empty_layout = QVBoxLayout()
        self.lblEmptyCellsValue = QLabel("40 cells empty")
        self.lblEmptyCellsValue.setAlignment(Qt.AlignCenter)
        self.sliderEmptyCells = QSlider(Qt.Horizontal)
        self.sliderEmptyCells.setMinimum(20)
        self.sliderEmptyCells.setMaximum(60)
        self.sliderEmptyCells.setValue(40)
        self.sliderEmptyCells.setTickInterval(5)
        self.sliderEmptyCells.valueChanged.connect(self.on_slider_changed)
        empty_layout.addWidget(self.lblEmptyCellsValue)
        empty_layout.addWidget(self.sliderEmptyCells)
        empty_group.setLayout(empty_layout)
        control_layout.addWidget(empty_group)

        number_group = QGroupBox("Number Selection")
        number_layout = QGridLayout()
        self.number_buttons = []
        for i in range(1, 10):
            btn = QPushButton(str(i))
            btn.setFixedSize(60, 60)
            btn.clicked.connect(lambda _, n=i: self.number_clicked(n))
            r = (i - 1) // 3
            c = (i - 1) % 3
            number_layout.addWidget(btn, r, c)
            self.number_buttons.append(btn)
        btn_erase = QPushButton("Erase")
        self._try_set_icon(btn_erase, "edit-clear")
        btn_erase.setFixedSize(60, 60)
        btn_erase.clicked.connect(lambda: self.number_clicked(""))
        number_layout.addWidget(btn_erase, 3, 1)
        number_group.setLayout(number_layout)
        control_layout.addWidget(number_group)

        control_group.setLayout(control_layout)
        main_layout.addWidget(control_group, 1, 1)

    def create_dock_widget(self):
        dock = QDockWidget("Tools & Statistics", self)
        dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        dock.setMinimumWidth(350)

        dock_widget = QWidget()
        dock_layout = QVBoxLayout()

        timer_group = QGroupBox("Game Timer")
        tlay = QVBoxLayout()
        self.lbl_timer = QLabel("00:00:00")
        self.lbl_timer.setObjectName("lblTimer")
        self.lbl_timer.setAlignment(Qt.AlignCenter)
        self.btn_timer = QPushButton("Start")
        self._try_set_icon(self.btn_timer, "media-playback-start")
        self.btn_timer.clicked.connect(self.toggle_timer)
        tlay.addWidget(self.lbl_timer)
        tlay.addWidget(self.btn_timer)
        timer_group.setLayout(tlay)
        dock_layout.addWidget(timer_group)

        stats_group = QGroupBox("Game Statistics")
        slay = QVBoxLayout()
        self.lbl_stats_mistakes = QLabel("Mistakes: 0/5")
        self.lbl_stats_filled = QLabel("Filled: 0/81")
        self.lbl_stats_hints = QLabel("Hints Used: 0")
        slay.addWidget(self.lbl_stats_mistakes)
        slay.addWidget(self.lbl_stats_filled)
        slay.addWidget(self.lbl_stats_hints)
        stats_group.setLayout(slay)
        dock_layout.addWidget(stats_group)

        tools_group = QGroupBox("Game Tools")
        t2 = QVBoxLayout()
        self.btn_check = QPushButton("Check Solution")
        self._try_set_icon(self.btn_check, "dialog-apply")
        self.btn_check.clicked.connect(self.check_solution)
        self.btn_hint = QPushButton("Show Hint")
        self._try_set_icon(self.btn_hint, "help-faq")
        self.btn_hint.clicked.connect(self.show_hint)
        t2.addWidget(self.btn_check)
        t2.addWidget(self.btn_hint)
        tools_group.setLayout(t2)
        dock_layout.addWidget(tools_group)

        dock_widget.setLayout(dock_layout)
        dock.setWidget(dock_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)

    def _try_set_icon(self, widget, icon_name):
        try:
            icon = QIcon.fromTheme(icon_name)
            if not icon.isNull():
                widget.setIcon(icon)
        except Exception:
            pass

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_board_frame_size()

    def update_board_frame_size(self):
        size = min(self.board_frame.width(), self.board_frame.height())
        for row in self.cells:
            for cell in row:
                cell.setFixedSize(size // 9, size // 9)

    def on_slider_changed(self, value):
        self.lblEmptyCellsValue.setText(f"{value} cells empty")

    def new_game(self):
        empty_cells = self.sliderEmptyCells.value()
        if self.rbEasy.isChecked():
            empty_cells = min(60, max(20, empty_cells - 5))
        elif self.rbHard.isChecked():
            empty_cells = min(60, max(20, empty_cells + 5))
        elif self.rbExpert.isChecked():
            empty_cells = min(60, max(20, empty_cells + 10))
        self.game.create_game_board(empty_cells)
        self.update_board()
        self.selected_cell = None
        self.game.mistakes = 0
        self.game.hints_used = 0

        self.seconds = 0
        self.lbl_timer.setText("00:00:00")
        self.is_timer_running = False
        self.btn_timer.setText("Start")
        self._try_set_icon(self.btn_timer, "media-playback-start")
        self.timer.stop()

        self.update_statistics()
        self.statusBar().showMessage("New game started. Select a cell and enter a number.")

    def update_board(self):
        for r in range(9):
            for c in range(9):
                cell = self.cells[r][c]
                value = self.game.game_board[r][c]
                is_immutable = (r, c) in self.game.immutable_cells
                cell.set_value(value if value != "" else "", is_immutable)
                cell.set_selected(False)
                cell.set_error(False)
                cell.set_hint(False)

    def cell_clicked(self, row, col):
        if self.selected_cell:
            pr, pc = self.selected_cell
            self.cells[pr][pc].set_selected(False)
        if (row, col) not in self.game.immutable_cells:
            self.selected_cell = (row, col)
            self.cells[row][col].set_selected(True)
            self.statusBar().showMessage(f"Selected cell: ({row + 1}, {col + 1})")
        else:
            self.selected_cell = None
            self.statusBar().showMessage("This cell is fixed and cannot be changed.")

    def number_clicked(self, number):
        if not self.selected_cell:
            self.statusBar().showMessage("Please select a cell first.")
            return
        row, col = self.selected_cell
        self.cells[row][col].set_error(False)
        self.cells[row][col].set_hint(False)
        if number == "":
            self.game.game_board[row][col] = ""
            self.cells[row][col].set_value("")
            self.statusBar().showMessage(f"Cell ({row + 1}, {col + 1}) cleared.")
        else:
            if self.game.is_valid_move(row, col, number):
                self.game.game_board[row][col] = int(number)
                self.cells[row][col].set_value(int(number))
                self.statusBar().showMessage(f"Correct. Number {number} placed at ({row + 1}, {col + 1}).")
            else:
                self.game.mistakes += 1
                self.game.game_board[row][col] = int(number)
                self.cells[row][col].set_value(int(number))
                self.cells[row][col].set_error(True)
                self.statusBar().showMessage(f"Incorrect. Mistakes: {self.game.mistakes}/{self.game.max_mistakes}")
                if self.game.mistakes >= self.game.max_mistakes:
                    QMessageBox.warning(self, "Game Over",
                                        f"You've made {self.game.mistakes} mistakes.\nGame Over.")
        self.update_statistics()
        if self._is_fully_solved():
            self.timer.stop()
            self.is_timer_running = False
            self.btn_timer.setText("Start")
            self._try_set_icon(self.btn_timer, "media-playback-start")
            QMessageBox.information(self, "Congratulations", f"Puzzle solved!\nTime: {self.lbl_timer.text()}\nMistakes: {self.game.mistakes}")
            self.save_score_prompt()

    def _is_fully_solved(self):
        if self.game.solution_board is None:
            return False
        for i in range(9):
            for j in range(9):
                if str(self.game.game_board[i][j]) != str(self.game.solution_board[i][j]):
                    return False
        return True

    def show_hint(self):
        if self.selected_cell:
            row, col = self.selected_cell
            if self.game.game_board[row][col] == "":
                correct_value = int(self.game.solution_board[row][col])
                self.game.game_board[row][col] = correct_value
                self.cells[row][col].set_value(correct_value)
                self.cells[row][col].set_hint(True)
                self.game.hints_used += 1
                self.update_statistics()
                self.statusBar().showMessage(f"Hint: {correct_value} placed at ({row + 1}, {col + 1}).")
                return
        hint = self.game.get_hint()
        if hint:
            row, col, value = hint
            self.game.game_board[row][col] = int(value)
            self.cells[row][col].set_value(int(value))
            self.cells[row][col].set_hint(True)
            self.game.hints_used += 1
            if self.selected_cell:
                pr, pc = self.selected_cell
                self.cells[pr][pc].set_selected(False)
            self.selected_cell = (row, col)
            self.cells[row][col].set_selected(True)
            self.update_statistics()
            self.statusBar().showMessage(f"Hint: {value} placed at ({row + 1}, {col + 1}).")
        else:
            self.statusBar().showMessage("No empty cells left.")

    def check_solution(self):
        if self._is_fully_solved():
            QMessageBox.information(self, "Solution Check", "Perfect. All numbers are correct.")
            return True
        else:
            incorrect_cells = []
            for i in range(9):
                for j in range(9):
                    if (i, j) not in self.game.immutable_cells:
                        if str(self.game.game_board[i][j]) != str(self.game.solution_board[i][j]):
                            incorrect_cells.append((i, j))
            if incorrect_cells:
                msg = f"Found {len(incorrect_cells)} incorrect cells:\n"
                for idx, (r, c) in enumerate(incorrect_cells[:10]):
                    msg += f"Cell ({r + 1}, {c + 1})\n"
                if len(incorrect_cells) > 10:
                    msg += f"... and {len(incorrect_cells) - 10} more"
                QMessageBox.warning(self, "Solution Check", msg)
            return False

    def toggle_timer(self):
        if self.is_timer_running:
            self.timer.stop()
            self.btn_timer.setText("Start")
            self._try_set_icon(self.btn_timer, "media-playback-start")
            self.is_timer_running = False
        else:
            self.timer.start(1000)
            self.btn_timer.setText("Pause")
            self._try_set_icon(self.btn_timer, "media-playback-pause")
            self.is_timer_running = True

    def update_timer(self):
        self.seconds += 1
        hours = self.seconds // 3600
        minutes = (self.seconds % 3600) // 60
        seconds = self.seconds % 60
        self.lbl_timer.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")

    def update_statistics(self):
        filled = self.game.get_filled_count()
        self.lbl_stats_mistakes.setText(f"Mistakes: {self.game.mistakes}/{self.game.max_mistakes}")
        self.lbl_stats_filled.setText(f"Filled: {filled}/81")
        self.lbl_stats_hints.setText(f"Hints Used: {self.game.hints_used}")
        self.progressBar.setValue(filled)

    def save_game(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Game", "", "Sudoku Files (*.sdj)")
        if not path:
            return
        if not path.lower().endswith(".sdj"):
            path += ".sdj"

        data = {
            "solution_board": [[int(self.game.solution_board[r][c]) for c in range(9)] for r in range(9)] if self.game.solution_board is not None else None,
            "game_board": [[(self.game.game_board[r][c] if self.game.game_board[r][c] != "" else "") for c in range(9)] for r in range(9)],
            "immutable_cells": list([list(x) for x in sorted(self.game.immutable_cells)]),
            "mistakes": int(self.game.mistakes),
            "hints_used": int(self.game.hints_used),
            "empty_cells": int(self.game.empty_cells),
            "seconds": int(self.seconds),
            "is_timer_running": bool(self.is_timer_running),
            "cells_meta": [
                [
                    {
                        "is_error": bool(self.cells[r][c].is_error),
                        "is_hint": bool(self.cells[r][c].is_hint)
                    }
                    for c in range(9)
                ]
                for r in range(9)
            ]
        }

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "Saved", "Game saved successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save game: {e}")

    def load_game(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Game", "", "Sudoku Files (*.sdj)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load game: {e}")
            return

        if data.get("solution_board") is not None:
            sol = data["solution_board"]
            self.game.solution_board = np.array([[int(sol[r][c]) for c in range(9)] for r in range(9)])
        else:
            self.game.solution_board = None

        gb = data.get("game_board")
        if gb is None:
            QMessageBox.critical(self, "Error", "Invalid save file: missing game_board")
            return
        self.game.game_board = np.array([[gb[r][c] if gb[r][c] != "" else "" for c in range(9)] for r in range(9)], dtype=object)

        im = data.get("immutable_cells", [])
        self.game.immutable_cells = set((int(x[0]), int(x[1])) for x in im)

        self.game.mistakes = int(data.get("mistakes", 0))
        self.game.hints_used = int(data.get("hints_used", 0))
        self.game.empty_cells = int(data.get("empty_cells", 40))
        self.seconds = int(data.get("seconds", 0))
        self.is_timer_running = bool(data.get("is_timer_running", False))
        if self.is_timer_running:
            self.timer.start(1000)
            self.btn_timer.setText("Pause")
            self._try_set_icon(self.btn_timer, "media-playback-pause")
        else:
            self.timer.stop()
            self.btn_timer.setText("Start")
            self._try_set_icon(self.btn_timer, "media-playback-start")

        cells_meta = data.get("cells_meta", None)

        for r in range(9):
            for c in range(9):
                value = self.game.game_board[r][c]
                is_immutable = (r, c) in self.game.immutable_cells
                self.cells[r][c].set_value(value if value != "" else "", is_immutable)
                if cells_meta:
                    meta = cells_meta[r][c]
                    self.cells[r][c].set_error(meta.get("is_error", False))
                    self.cells[r][c].set_hint(meta.get("is_hint", False))
                else:
                    self.cells[r][c].set_error(False)
                    self.cells[r][c].set_hint(False)
                self.cells[r][c].set_selected(False)

        self.selected_cell = None
        self.update_statistics()
        self.statusBar().showMessage("Game loaded successfully.")

    def save_score_prompt(self):
        name, ok = QInputDialog.getText(self, "Save Score", "Enter your name:")
        if not ok:
            return
        name = name.strip() or "Anonymous"
        self._save_score(name)

    def _save_score(self, player_name):
        filled = self.game.get_filled_count()
        conn = sqlite3.connect(DB_FILENAME)
        c = conn.cursor()
        c.execute("""
            INSERT INTO scores (player_name, time_seconds, mistakes, hints_used, filled_cells, empty_cells, date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            player_name,
            int(self.seconds),
            int(self.game.mistakes),
            int(self.game.hints_used),
            int(filled),
            int(self.game.empty_cells),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        conn.close()
        QMessageBox.information(self, "Saved", "Score saved to database.")

    def show_scores(self):
        dlg = ScoresDialog(self)
        dlg.exec()

    def global_stylesheet(self):
        return """
        QMainWindow { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #0f0c29, stop:0.5 #302b63, stop:1 #24243e); }
        QLabel#lblTitle { color: #00dbde; font-size: 36px; font-weight:bold; }
        QFrame#gameBoardFrame { background: white; border: 4px solid #00dbde; border-radius: 15px; }
        QPushButton { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #00dbde, stop:1 #fc00ff); border:none; border-radius:12px; color:white; padding:8px; min-height:40px; }
        QGroupBox { border: 3px solid #00dbde; border-radius: 12px; color: #00dbde; background: rgba(25,25,45,0.7); padding-top:10px; }
        QLabel { color: #ffffff; }
        QLabel#lblTimer { color: #ffd700; font-size: 32px; font-weight:bold; }
        QProgressBar { border:3px solid #00dbde; border-radius:8px; text-align:center; color:white; font-weight:bold; height:25px; }
        QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #fc00ff, stop:0.5 #00dbde, stop:1 #8a2be2); border-radius:5px; }
        """

def main():
    init_db()
    app = QApplication(sys.argv)
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    window = SudokuMaster()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
