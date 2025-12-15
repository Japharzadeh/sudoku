This Python program implements a fully-featured Sudoku game application using PySide6 (Qt for Python) and SQLite for score management. The application provides an interactive GUI for playing, saving, and loading Sudoku puzzles with multiple features.

Key Features:

Sudoku Game Logic (SudokuGame Class):

Generates valid 9×9 Sudoku puzzles with randomized solutions.

Supports adjustable difficulty levels by controlling the number of empty cells.

Tracks immutable cells, mistakes, and hints used.

Provides functions for validating moves, giving hints, and checking the solution.

Graphical Interface (SudokuMaster Class):

Displays a 9×9 Sudoku board with visually distinct cells.

Highlights selected, error, and hint cells using dynamic styles.

Supports number input via buttons or keyboard, including erase functionality.

Provides a control panel for starting new games, saving/loading games, and adjusting difficulty.

Includes a dockable tools panel for timer, statistics, hints, and solution checking.

Timer and Statistics:

Tracks elapsed time with start/pause functionality.

Displays real-time statistics: mistakes, filled cells, and hints used.

Shows a progress bar representing the number of filled cells.

Persistence:

Saves and loads games using JSON files, preserving the current board, immutable cells, mistakes, hints, and timer state.

Records completed game scores in an SQLite database (scores.db) with player name, time, mistakes, hints used, filled/empty cells, and date.

Displays saved scores in a dedicated dialog with sorting and formatting.

User Interaction:

Interactive cell selection with visual feedback.

Provides hints either for the selected cell or for any empty cell.

Alerts players when the maximum number of mistakes is reached.

Supports checking the solution and notifying the player about errors.

Styling:

Customizable and modern UI design with gradient backgrounds, rounded borders, and dynamic cell styling.

Responsive layout adjusts cell sizes on window resize.

Installation and Running:

Ensure Python 3.10+ is installed.

Install required packages using pip:

pip install -r requirements.txt


Run the application:

python sudoku_master.py


(Replace sudoku_master.py with the filename of the main script if different.)

The application starts with main(), initializing the database, creating the GUI, and launching the Qt event loop.
