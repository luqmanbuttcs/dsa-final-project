# Klondike Solitaire - DSA Project

A playable, self-contained desktop implementation of classic Klondike Solitaire using **Python and PyQt6**. The interface is custom-painted with `QPainter`; no downloaded card images, browser UI, or other GUI framework is used. The game engine and data structures can be tested without launching Qt.

## Requirements

- Python 3.10 or newer
- Windows, macOS, or Linux with a desktop environment for the GUI
- PyQt6 (installed from `requirements.txt`)

## Install and run

Open a terminal in this folder. On Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

On macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

If PowerShell blocks virtual-environment activation, you can call the venv Python directly: `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` and `.\.venv\Scripts\python.exe main.py`.

## How to play

- **Stock:** Click it to draw one or three cards, as selected. When stock is empty, click its empty slot to recycle the waste.
- **Waste:** Click the playable top card, then click a valid tableau column or the matching foundation.
- **Tableau:** Click a face-up card to select it. Clicking any face-up card in a tableau also selects the face-up sequence beneath it. Click a destination column to move that card/sequence.
- **Foundations:** Build each suit from Ace through King. Click a foundation's top card, then a legal tableau destination to move it back when necessary.
- **Rules:** Tableau cards descend by rank and alternate red/black. Only Kings can fill empty tableau columns. Foundations build upward by suit.
- **Controls:** New Game, Undo, Redo, Draw 1, Draw 3, Hint. Press **Esc** to cancel a selection. Move count and invalid-move messages appear in the status bar.
- **Victory:** All 52 cards must be in their correct foundations.

## Project structure

```text
card.py                  Card, Suit, Rank, deck creation
data_structures.py       Node, DoublyLinkedList, Stack, Queue
game.py                  Klondike rules, piles, validation, snapshots, undo/redo, hints
ui.py                    QMainWindow, custom QPainter board, mouse interactions
main.py                  PyQt6 application entry point
tests/
  test_data_structures.py
test_game.py
requirements.txt
README.md
```

## Data structures used

| Structure | Where and why it is used |
|---|---|
| **Array/List** | Builds the standard 52-card deck before shuffle/deal; temporary list views make it straightforward to validate selected tableau sequences. |
| **Custom Queue (FIFO)** | Holds the stockpile in draw order. Drawing removes from the front; recycling the waste restores the original order. |
| **Custom Stack (LIFO)** | Represents waste and foundation piles and the undo/redo histories. Tableau piles are also stacks. |
| **Custom Doubly Linked List** | Backs each custom Stack, so the stack remains the pile API while tableau sequences can be split and spliced without maintaining duplicate card storage. |
| **Custom Node** | Links the doubly linked list and the stock queue. |
| **Dictionary / HashMap** | `GameEngine.card_positions` indexes card IDs to their current zone, pile, index, and face state; the index is rebuilt after successful state changes. |

## Game logic and complexity notes

- Shuffling a deck of 52 cards is `O(n)` expected time; initial dealing is `O(52)` for this fixed-size game.
- Queue enqueue/dequeue and stack push/pop are `O(1)`.
- A linked-list suffix split locates the split node in `O(min(k, n-k))` and detaches the suffix by pointer updates. Splicing a suffix onto another stack is `O(1)`.
- Move validation inspects the selected sequence and the destination top card, so it is `O(k)` for a sequence of `k` cards. The dictionary index refresh is `O(52)`, constant for a standard deck.
- Undo/redo stores snapshots of the piles (at most 52 cards) and restores them in `O(52)` time. This is deliberately simple and robust for a university project; invalid moves do not create history entries or change the board.

## Run tests (no GUI required)

The tests use Python's built-in `unittest` and do not import PyQt6:

```bash
python -m unittest discover -s tests -v
```

The suite covers custom data structures, initial dealing and card uniqueness, stock draw modes/recycling, legal and invalid moves, card flipping, foundations, hints, and undo/redo.

## Academic demonstration guide

1. Show `card.py` for `Card`, `Suit`, `Rank`, and the 52-card deck.
2. Show `data_structures.py` for the LIFO `Stack`, FIFO `Queue`, node links, and `DoublyLinkedList.split_off` / `extend` used to move tableau sequences.
3. Show `game.py::_validate_move` for the Klondike rules and `game.py::move` for the validated state transition. All GUI actions call this engine rather than editing piles directly.
4. Show `_snapshot`, `_restore`, `undo`, and `redo` to explain move-history stacks.
5. Show `ui.py::SolitaireBoard.paintEvent` for custom card drawing and `mousePressEvent` for Qt click handling. `main.py` starts the event loop.
6. Run the tests, then demonstrate stock recycling, an invalid move, revealing a hidden tableau card, undo/redo, and winning-condition checking.

The optional hint system suggests a currently legal move when one is available. Timer and scoring are not implemented; they are optional extras in the course brief.
