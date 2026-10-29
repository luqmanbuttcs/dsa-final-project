"""PyQt6 desktop interface for Klondike Solitaire.

The board is drawn with QPainter, while GameEngine remains the only owner of
game rules and pile mutations. All mouse and button input flows through it.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QRectF, QSize
from PyQt6.QtGui import (
    QColor, QBrush, QFont, QLinearGradient, QPainter, QPainterPath, QPen,
)
from PyQt6.QtWidgets import (
    QButtonGroup, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton,
    QRadioButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from card import Card, Suit
from game import GameEngine, MoveDestination, MoveSource


TABLE = QColor("#0b4435")
TABLE_LIGHT = QColor("#125542")
_SLOT = QColor(220, 240, 228, 42)
_RED = QColor("#c72e43")
_DARK = QColor("#172b26")
_GOLD = QColor("#ffd166")


class SolitaireBoard(QWidget):
    """Responsive custom-painted board with click-to-select/move interactions."""

    def __init__(self, game: GameEngine, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.game = game
        self.selection: MoveSource | None = None
        self.status_callback = None
        self.move_callback = None
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.setMinimumWidth(980)
        self.setMinimumHeight(self.required_height())
        self.setMouseTracking(True)

    def required_height(self) -> int:
        max_cards = max([len(pile) for pile in self.game.tableau] + [1])
        card_w = 112
        card_h = int(card_w * 1.42)
        tableau_y = 24 + card_h + 36
        return tableau_y + card_h + max(0, max_cards - 1) * 26 + 34

    def sizeHint(self) -> QSize:
        return QSize(1120, self.required_height())

    def refresh_board(self) -> None:
        self.setMinimumHeight(self.required_height())
        self.updateGeometry()
        self.update()

    def set_selection(self, selection: MoveSource | None) -> None:
        self.selection = selection
        self.update()

    def _metrics(self) -> dict[str, int | list[int]]:
        width = max(self.width(), 980)
        margin = 24
        card_w = min(112, max(68, (width - margin * 2 - 6 * 14) // 7))
        gap = min(32, max(12, (width - margin * 2 - card_w * 7) // 6))
        content_w = card_w * 7 + gap * 6
        x0 = max(10, (width - content_w) // 2)
        xs = [x0 + i * (card_w + gap) for i in range(7)]
        card_h = int(card_w * 1.42)
        top_y = 24
        tableau_y = top_y + card_h + 36
        max_cards = max([len(pile) for pile in self.game.tableau] + [1])
        available = max(16, (self.height() - tableau_y - card_h - 26) // max(1, max_cards - 1))
        step = min(26, available)
        return {
            "card_w": card_w, "card_h": card_h, "gap": gap, "xs": xs,
            "top_y": top_y, "tableau_y": tableau_y, "step": step,
        }

    def paintEvent(self, _event) -> None:  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        background = QLinearGradient(0, 0, 0, self.height())
        background.setColorAt(0, TABLE_LIGHT)
        background.setColorAt(1, TABLE)
        painter.fillRect(self.rect(), QBrush(background))
        painter.setPen(QPen(QColor(255, 255, 255, 14), 1))
        for y in range(0, self.height(), 46):
            painter.drawLine(0, y, self.width(), y)

        m = self._metrics()
        card_w, card_h = int(m["card_w"]), int(m["card_h"])
        xs, top_y = m["xs"], int(m["top_y"])
        tableau_y, step = int(m["tableau_y"]), int(m["step"])

        # Stock and waste slots.
        stock_rect = QRectF(xs[0], top_y, card_w, card_h)
        if self.game.stock:
            self._draw_back(painter, stock_rect, False)
            painter.setPen(QColor(255, 255, 255, 210))
            painter.setFont(QFont("Arial", max(8, card_w // 12), QFont.Weight.DemiBold))
            painter.drawText(QRectF(stock_rect.left(), stock_rect.bottom() + 4, card_w, 18),
                             Qt.AlignmentFlag.AlignCenter, str(len(self.game.stock)))
        else:
            self._draw_empty_slot(painter, stock_rect, label="↻" if self.game.waste else "Empty")

        waste_cards = self.game.waste.to_list()
        waste_rect = QRectF(xs[1], top_y, card_w, card_h)
        if not waste_cards:
            self._draw_empty_slot(painter, waste_rect, label="Waste")
        else:
            visible = waste_cards[-3:]
            fan = max(13, card_w // 6)
            for offset, card in enumerate(visible):
                selected = self.selection == MoveSource("waste") and offset == len(visible) - 1
                rect = QRectF(xs[1] + offset * fan, top_y, card_w, card_h)
                self._draw_card(painter, rect, card, selected)

        # Four foundations: Hearts, Diamonds, Clubs, Spades on columns 4-7.
        for slot, suit in enumerate((Suit.HEARTS, Suit.DIAMONDS, Suit.CLUBS, Suit.SPADES), start=3):
            rect = QRectF(xs[slot], top_y, card_w, card_h)
            top = self.game.foundations[suit].peek()
            selected = self.selection == MoveSource("foundation", suit.value)
            if top is None:
                self._draw_empty_slot(painter, rect, suit=suit)
            else:
                self._draw_card(painter, rect, top, selected)

        # Seven tableau columns. Piles are always painted bottom-to-top.
        for col, pile in enumerate(self.game.tableau):
            cards = pile.to_list()
            x = xs[col]
            if not cards:
                self._draw_empty_slot(painter, QRectF(x, tableau_y, card_w, card_h), label="K")
                continue
            for index, card in enumerate(cards):
                y = tableau_y + index * step
                selected = (
                    self.selection is not None
                    and self.selection.kind == "tableau"
                    and self.selection.pile == col
                    and self.selection.card_index is not None
                    and index >= self.selection.card_index
                )
                self._draw_card(painter, QRectF(x, y, card_w, card_h), card, selected)
        painter.end()

    def _draw_empty_slot(
        self, painter: QPainter, rect: QRectF, label: str = "", suit: Suit | None = None
    ) -> None:
        painter.save()
        painter.setBrush(QBrush(QColor(2, 27, 20, 18)))
        painter.setPen(QPen(_SLOT, 1.7, Qt.PenStyle.DashLine))
        painter.drawRoundedRect(rect, 9, 9)
        if suit is not None:
            painter.setPen(QColor(255, 255, 255, 115))
            painter.setFont(QFont("DejaVu Sans", max(18, int(rect.width() * 0.36))))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, suit.symbol)
        elif label:
            painter.setPen(QColor(238, 249, 241, 170))
            painter.setFont(QFont("Arial", max(9, int(rect.width() * 0.12)), QFont.Weight.DemiBold))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)
        painter.restore()

    def _draw_back(self, painter: QPainter, rect: QRectF, selected: bool) -> None:
        painter.save()
        path = QPainterPath()
        path.addRoundedRect(rect, 8, 8)
        painter.fillPath(path, QBrush(QColor("#f7f7f2"))))
        inner = rect.adjusted(4, 4, -4, -4)
        inner_path = QPainterPath()
        inner_path.addRoundedRect(inner, 5, 5)
        gradient = QLinearGradient(inner.topLeft(), inner.bottomRight())
        gradient.setColorAt(0, QColor("#245ca4"))
        gradient.setColorAt(1, QColor("#102d62"))
        painter.fillPath(inner_path, QBrush(gradient))
        painter.save()
        painter.setClipPath(inner_path)
        painter.setPen(QPen(QColor(225, 238, 255, 90), 1))
        spacing = max(7, int(rect.width() / 10))
        x = int(inner.left() - rect.height())
        while x < inner.right() + rect.height():
            painter.drawLine(x, int(inner.top()), x + int(rect.height()), int(inner.bottom()))
            painter.drawLine(x, int(inner.bottom()), x + int(rect.height()), int(inner.top()))
            x += spacing
        painter.restore()
        painter.setPen(QPen(_GOLD if selected else QColor("#f2f2eb"), 3 if selected else 1.2))
        painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 8, 8)
        if selected:
            painter.setPen(QPen(_GOLD, 3))
            painter.drawRoundedRect(rect.adjusted(-2, -2, 2, 2), 9, 9)
        painter.restore()

    def _draw_card(self, painter: QPainter, rect: QRectF, card: Card, selected: bool) -> None:
        if not card.face_up:
            self._draw_back(painter, rect, selected)
            return
        painter.save()
        path = QPainterPath()
        path.addRoundedRect(rect, 8, 8)
        face = QLinearGradient(rect.topLeft(), rect.bottomRight())
        face.setColorAt(0, QColor("#ffffff"))
        face.setColorAt(1, QColor("#eceee8"))
        painter.fillPath(path, QBrush(face))
        painter.setPen(QPen(_GOLD if selected else QColor("#c8d0c8"), 3 if selected else 1.1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect.adjusted(0.7, 0.7, -0.7, -0.7), 8, 8)
        color = _RED if card.color == "red" else _DARK
        corner_font = QFont("DejaVu Sans", max(10, int(rect.width() * 0.17)), QFont.Weight.Bold)
        painter.setPen(color)
        painter.setFont(corner_font)
        painter.drawText(QRectF(rect.left() + 6, rect.top() + 4, rect.width() * 0.43, rect.height() * 0.20),
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, card.rank.label)
        suit_font = QFont("DejaVu Sans", max(10, int(rect.width() * 0.15)), QFont.Weight.DemiBold)
        painter.setFont(suit_font)
        painter.drawText(QRectF(rect.left() + 6, rect.top() + rect.height() * 0.16,
                                rect.width() * 0.42, rect.height() * 0.18),
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, card.suit.symbol)
        painter.setFont(QFont("DejaVu Sans", max(24, int(rect.width() * 0.43)), QFont.Weight.Bold))
        painter.drawText(rect.adjusted(4, 10, -4, -8), Qt.AlignmentFlag.AlignCenter, card.suit.symbol)
        painter.setFont(QFont("DejaVu Sans", max(10, int(rect.width() * 0.15)), QFont.Weight.DemiBold))
        painter.drawText(QRectF(rect.left() + rect.width() * 0.54, rect.bottom() - rect.height() * 0.22,
                                rect.width() * 0.37, rect.height() * 0.16),
                         Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom, card.rank.label + card.suit.symbol)
        painter.restore()

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos = event.position()
        m = self._metrics()
        card_w, card_h = int(m["card_w"]), int(m["card_h"])
        xs, top_y = m["xs"], int(m["top_y"])
        tableau_y = int(m["tableau_y"])
        x, y = int(pos.x()), int(pos.y())

        # Top-row targets have priority over tableau columns below them.
        if top_y <= y <= top_y + card_h:
            if xs[0] <= x <= xs[0] + card_w:
                self.selection = None
                result = self.game.draw_from_stock()
                self._notify(result.message, result.success)
                return
            waste_fan_right = xs[1] + card_w + max(13, card_w // 6) * 2
            if xs[1] <= x <= waste_fan_right:
                if self.game.waste:
                    self.selection = MoveSource("waste")
                    self._notify("Waste card selected. Choose a tableau column or its foundation.", True)
                else:
                    self._notify("The waste pile is empty.", False)
                return
            for slot, suit in enumerate((Suit.HEARTS, Suit.DIAMONDS, Suit.CLUBS, Suit.SPADES), start=3):
                if xs[slot] <= x <= xs[slot] + card_w:
                    self._click_foundation(suit)
                    return

        if y >= tableau_y:
            for col, col_x in enumerate(xs):
                if col_x <= x <= col_x + card_w:
                    self._click_tableau(col, y, m)
                    return
        if self.selection is not None:
            self.selection = None
            self._notify("Selection cancelled.", True)

    def _click_foundation(self, suit: Suit) -> None:
        source = MoveSource("foundation", suit.value)
        if self.selection is None:
            if not self.game.foundations[suit]:
                self._notify(f"{suit.title} foundation is empty.", False)
                return
            self.selection = source
            self._notify(f"Top card of {suit.title} foundation selected. Choose a tableau column.", True)
            return
        if self.selection == source:
            self.selection = None
            self._notify("Selection cancelled.", True)
            return
        self._try_move(MoveDestination("foundation", suit.value))

    def _click_tableau(self, col: int, y: int, metrics: dict[str, int | list[int]]) -> None:
        pile = self.game.tableau[col]
        cards = pile.to_list()
        start_y, step = int(metrics["tableau_y"]), int(metrics["step"])
        card_index = max(0, min(len(cards) - 1, (y - start_y) // step)) if cards else None

        if self.selection is None:
            if card_index is None:
                self._notify("Empty column: select a King to move it here.", False)
                return
            card = cards[card_index]
            if not card.face_up:
                self._notify("That card is face down. Move the exposed card above it first.", False)
                return
            self.selection = MoveSource("tableau", col, card_index)
            self._notify(f"Selected {card}. Click a legal destination; the face-up sequence below it moves together.", True)
            return

        if self.selection.kind == "tableau" and self.selection.pile == col:
            if card_index is None:
                self.selection = None
            elif card_index == self.selection.card_index:
                self.selection = None
                self._notify("Selection cancelled.", True)
                return
            elif cards[card_index].face_up:
                card = cards[card_index]
                self.selection = MoveSource("tableau", col, card_index)
                self._notify(f"Selection changed to {card}.", True)
                return
            else:
                self._notify("Select a face-up card or click another column.", False)
                return
            self.update()
            return

        self._try_move(MoveDestination("tableau", col))

    def _try_move(self, destination: MoveDestination) -> None:
        if self.selection is None:
            return
        result = self.game.move(self.selection, destination)
        if result.success:
            self.selection = None
            self._notify(result.message, True)
            if self.game.has_won:
                QMessageBox.information(self, "You won!", "All 52 cards are in their foundations. Congratulations!")
        else:
            self._notify(result.message, False)
        self.refresh_board()
        if self.move_callback:
            self.move_callback()

    def _notify(self, message: str, success: bool) -> None:
        if self.status_callback:
            self.status_callback(message, success)
        self.refresh_board()
        if self.move_callback:
            self.move_callback()


class SolitaireWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.game = GameEngine()
        self.setWindowTitle("Klondike Solitaire - DSA Project")
        self.setMinimumSize(1080, 760)
        self.resize(1280, 850)
        self.setStyleSheet("""
            QMainWindow, QWidget#root { background: #092f27; color: #f5f7f4; }
            QLabel { color: #f5f7f4; }
            QPushButton {
                background: #e4f0e8; color: #123b30; border: 1px solid #b8d3c1;
                border-radius: 8px; padding: 9px 15px; font-weight: 650;
            }
            QPushButton:hover { background: #ffffff; }
            QPushButton:pressed { background: #c4dfcd; }
            QPushButton:disabled { color: #7d9287; background: #c7d3cc; border-color: #aabbb0; }
            QRadioButton { color: #e6efe9; spacing: 6px; padding: 5px 7px; }
            QRadioButton::indicator { width: 15px; height: 15px; }
            QRadioButton::indicator:checked { background: #ffd166; border: 2px solid #ffd166; border-radius: 8px; }
            QRadioButton::indicator:unchecked { background: #143e33; border: 1px solid #8bb19d; border-radius: 8px; }
            QScrollArea { background: transparent; border: none; }
            QStatusBar { background: #072820; color: #e5eee8; border-top: 1px solid #275649; }
        """)

        root = QWidget()
        root.setObjectName("root")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 14, 18, 8)
        layout.setSpacing(10)

        heading = QHBoxLayout()
        title_col = QVBoxLayout()
        title = QLabel("KLONDIKE SOLITAIRE")
        title.setStyleSheet("font-size: 22px; font-weight: 800; letter-spacing: 1.3px; color: #ffffff;")
        subtitle = QLabel("DSA project • Build each foundation from Ace to King")
        subtitle.setStyleSheet("font-size: 12px; color: #b8d5c6;")
        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        heading.addLayout(title_col)
        heading.addStretch(1)
        self.moves_label = QLabel("MOVES  0")
        self.moves_label.setStyleSheet("font-size: 14px; font-weight: 800; background: #164b3b; padding: 10px 15px; border-radius: 8px;")
        heading.addWidget(self.moves_label)
        layout.addLayout(heading)

        controls = QHBoxLayout()
        controls.setSpacing(8)
        self.new_button = QPushButton("New Game")
        self.undo_button = QPushButton("Undo")
        self.redo_button = QPushButton("Redo")
        self.hint_button = QPushButton("Hint")
        self.new_button.clicked.connect(self._new_game)
        self.undo_button.clicked.connect(self._undo)
        self.redo_button.clicked.connect(self._redo)
        self.hint_button.clicked.connect(self._hint)
        for button in (self.new_button, self.undo_button, self.redo_button, self.hint_button):
            controls.addWidget(button)
        separator = QLabel("DRAW MODE")
        separator.setStyleSheet("color: #a8cbb9; font-size: 11px; font-weight: 800; padding-left: 12px;")
        controls.addWidget(separator)
        self.draw1 = QRadioButton("Draw 1")
        self.draw3 = QRadioButton("Draw 3")
        self.draw1.setChecked(True)
        self.draw_group = QButtonGroup(self)
        self.draw_group.addButton(self.draw1)
        self.draw_group.addButton(self.draw3)
        self.draw1.toggled.connect(lambda checked: self._set_draw_mode(1) if checked else None)
        self.draw3.toggled.connect(lambda checked: self._set_draw_mode(3) if checked else None)
        controls.addWidget(self.draw1)
        controls.addWidget(self.draw3)
        controls.addStretch(1)
        help_text = QLabel("Click a card, then click its destination • Esc cancels selection")
        help_text.setStyleSheet("color: #b8d5c6; font-size: 11px;")
        controls.addWidget(help_text)
        layout.addLayout(controls)

        self.board = SolitaireBoard(self.game)
        self.board.status_callback = self._status_message
        self.board.move_callback = self._refresh_controls
        scroll = QScrollArea()
        scroll.setWidget(self.board)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        layout.addWidget(scroll, 1)
        self.setCentralWidget(root)
        self.statusBar().showMessage("Ready. Draw cards from the stock; build tableau columns in descending alternating colors.")
        self._refresh_controls()

    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.key() == Qt.Key.Key_Escape:
            self.board.set_selection(None)
            self.statusBar().showMessage("Selection cancelled.")
            return
        super().keyPressEvent(event)

    def _status_message(self, message: str, success: bool) -> None:
        color = "#ccebd7" if success else "#ffd1d1"
        self.statusBar().setStyleSheet(f"QStatusBar {{ color: {color}; }}")
        self.statusBar().showMessage(message, 7000)

    def _refresh_controls(self) -> None:
        self.moves_label.setText(f"MOVES  {self.game.move_count}")
        self.undo_button.setEnabled(self.game.can_undo)
        self.redo_button.setEnabled(self.game.can_redo)
        self.board.refresh_board()

    def _set_draw_mode(self, mode: int) -> None:
        self.game.set_draw_mode(mode)
        self.statusBar().showMessage(f"Stock draw mode set to Draw {mode}.", 3500)

    def _new_game(self) -> None:
        self.game.new_game()
        self.board.set_selection(None)
        self.board.refresh_board()
        self._refresh_controls()
        self.statusBar().showMessage("New shuffled game dealt. Good luck!")

    def _undo(self) -> None:
        self.board.set_selection(None)
        result = self.game.undo()
        self.statusBar().showMessage(result.message, 4500)
        self._refresh_controls()

    def _redo(self) -> None:
        self.board.set_selection(None)
        result = self.game.redo()
        self.statusBar().showMessage(result.message, 4500)
        self._refresh_controls()

    def _hint(self) -> None:
        hint = self.game.get_hint()
        self.board.set_selection(hint.source)
        self.statusBar().showMessage(hint.message, 8000)
        self._refresh_controls()
        if hint.destination is not None:
            target = (f"column {int(hint.destination.pile) + 1}" if hint.destination.kind == "tableau"
                      else f"the {Suit(str(hint.destination.pile)).title} foundation")
            self.statusBar().showMessage(f"Hint: {hint.message} Click {target} to make the move.", 9000)
