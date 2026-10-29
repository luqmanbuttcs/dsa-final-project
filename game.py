"""Klondike rules and state transitions, deliberately independent of PyQt6."""
from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Any

from card import Card, Rank, Suit, make_deck
from data_structures import Queue, Stack


@dataclass(frozen=True, slots=True)
class MoveSource:
    """A card or face-up tableau suffix. pile is a column number or suit."""
    kind: str
    pile: int | str | None = None
    card_index: int | None = None


@dataclass(frozen=True, slots=True)
class MoveDestination:
    """A tableau column or a foundation suit."""
    kind: str
    pile: int | str


@dataclass(frozen=True, slots=True)
class MoveResult:
    success: bool
    message: str


@dataclass(frozen=True, slots=True)
class Hint:
    source: MoveSource | None
    destination: MoveDestination | None
    message: str


CardState = tuple[str, int, bool]


@dataclass(slots=True)
class GameSnapshot:
    stock: list[CardState]
    waste: list[CardState]
    tableau: list[list[CardState]]
    foundations: dict[str, list[CardState]]
    move_count: int


class GameEngine:
    """Stateful Klondike engine with validated moves and snapshot-based undo/redo."""

    def __init__(self, draw_mode: int = 1, seed: int | None = None) -> None:
        if draw_mode not in (1, 3):
            raise ValueError("draw_mode must be 1 or 3")
        self.draw_mode = draw_mode
        self._seed = seed
        self.stock: Queue[Card] = Queue()
        self.waste: Stack[Card] = Stack()
        self.tableau: list[Stack[Card]] = [Stack() for _ in range(7)]
        self.foundations: dict[Suit, Stack[Card]] = {suit: Stack() for suit in Suit}
        self.move_count = 0
        self._undo_stack: Stack[GameSnapshot] = Stack()
        self._redo_stack: Stack[GameSnapshot] = Stack()
        self.card_positions: dict[str, dict[str, Any]] = {}
        self.new_game(seed=seed)

    def new_game(self, seed: int | None = None) -> None:
        """Shuffle and deal a fresh 52-card game; history and move count reset."""
        self._seed = seed
        rng = random.Random(seed)
        deck = make_deck()
        rng.shuffle(deck)
        self.tableau = [Stack() for _ in range(7)]
        for column_index, pile in enumerate(self.tableau):
            for _ in range(column_index + 1):
                pile.push(deck.pop(0))
            top = pile.peek()
            assert top is not None
            top.face_up = True
        self.stock = Queue(deck)
        self.waste = Stack()
        self.foundations = {suit: Stack() for suit in Suit}
        self.move_count = 0
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._rebuild_position_index()

    def set_draw_mode(self, mode: int) -> None:
        if mode not in (1, 3):
            raise ValueError("draw mode must be 1 or 3")
        self.draw_mode = mode

    @property
    def can_undo(self) -> bool:
        return not self._undo_stack.is_empty()

    @property
    def can_redo(self) -> bool:
        return not self._redo_stack.is_empty()

    @property
    def has_won(self) -> bool:
        return sum(len(pile) for pile in self.foundations.values()) == 52

    @property
    def tableau_sizes(self) -> list[int]:
        return [len(pile) for pile in self.tableau]

    def draw_from_stock(self) -> MoveResult:
        """Draw one/three cards, or recycle the waste when stock is exhausted."""
        if not self.stock:
            if not self.waste:
                return MoveResult(False, "The stock and waste piles are both empty.")
            before = self._snapshot()
            # Waste is bottom-to-top; recycle in original draw order, face-down.
            recycled = self.waste.to_list()
            for card in recycled:
                card.face_up = False
            self.stock = Queue(recycled)
            self.waste.clear()
            self._finish_action(before)
            return MoveResult(True, "Waste recycled into the stockpile.")

        before = self._snapshot()
        drawn = 0
        while self.stock and drawn < self.draw_mode:
            card = self.stock.dequeue()
            card.face_up = True
            self.waste.push(card)
            drawn += 1
        self._finish_action(before)
        noun = "card" if drawn == 1 else "cards"
        return MoveResult(True, f"Drew {drawn} {noun} from the stockpile.")

    def move(self, source: MoveSource, destination: MoveDestination) -> MoveResult:
        """Move a selected card/sequence only after full rule validation."""
        valid, message, _moving = self._validate_move(source, destination)
        if not valid:
            return MoveResult(False, message)
        before = self._snapshot()

        if destination.kind == "tableau":
            destination_pile = self.tableau[int(destination.pile)]
            if source.kind == "tableau":
                source_pile = self.tableau[int(source.pile)]
                suffix = source_pile.split_off(int(source.card_index))
                destination_pile.extend_stack(suffix)
                self._flip_exposed_tableau_card(source_pile)
            elif source.kind == "waste":
                destination_pile.push(self.waste.pop())
            else:
                destination_pile.push(self.foundations[Suit(str(source.pile))].pop())
        else:
            suit = Suit(str(destination.pile))
            if source.kind == "tableau":
                source_pile = self.tableau[int(source.pile)]
                card = source_pile.pop()
                self.foundations[suit].push(card)
                self._flip_exposed_tableau_card(source_pile)
            elif source.kind == "waste":
                self.foundations[suit].push(self.waste.pop())
            else:
                return MoveResult(False, "A foundation card cannot move directly to another foundation.")

        self._finish_action(before)
        if self.has_won:
            return MoveResult(True, "Excellent! All 52 cards are in their foundations. You won!")
        return MoveResult(True, message)

    def undo(self) -> MoveResult:
        if not self.can_undo:
            return MoveResult(False, "There is no move to undo.")
        current = self._snapshot()
        previous = self._undo_stack.pop()
        self._redo_stack.push(current)
        self._restore(previous)
        return MoveResult(True, "Last action undone.")

    def redo(self) -> MoveResult:
        if not self.can_redo:
            return MoveResult(False, "There is no move to redo.")
        current = self._snapshot()
        following = self._redo_stack.pop()
        self._undo_stack.push(current)
        self._restore(following)
        return MoveResult(True, "Undid action restored.")

    def get_hint(self) -> Hint:
        """Return a legal, prioritized suggestion without changing the board."""
        candidates: list[tuple[int, MoveSource, MoveDestination, str]] = []

        if self.waste:
            src = MoveSource("waste")
            card = self.waste.peek()
            assert card is not None
            dest = MoveDestination("foundation", card.suit.value)
            if self._validate_move(src, dest)[0]:
                candidates.append((0, src, dest, f"Move {card} to its foundation."))

        for col, pile in enumerate(self.tableau):
            cards = pile.to_list()
            if not cards:
                continue
            top = cards[-1]
            src = MoveSource("tableau", col, len(cards) - 1)
            dest = MoveDestination("foundation", top.suit.value)
            if self._validate_move(src, dest)[0]:
                candidates.append((1, src, dest, f"Move {top} from column {col + 1} to its foundation."))

        for src_col, pile in enumerate(self.tableau):
            cards = pile.to_list()
            first_face_up = next((i for i, card in enumerate(cards) if card.face_up), len(cards))
            for card_index in range(first_face_up, len(cards)):
                moving = cards[card_index]
                src = MoveSource("tableau", src_col, card_index)
                for dest_col in range(7):
                    if dest_col == src_col:
                        continue
                    dest = MoveDestination("tableau", dest_col)
                    if self._validate_move(src, dest)[0]:
                        uncovers_hidden = (
                            card_index == len(cards) - 1 and len(cards) > 1 and not cards[-2].face_up
                        )
                        priority = 0 if uncovers_hidden else 3
                        candidates.append((
                            priority, src, dest,
                            f"Move {moving} from column {src_col + 1} to column {dest_col + 1}."
                        ))

        if self.waste:
            card = self.waste.peek()
            assert card is not None
            src = MoveSource("waste")
            for dest_col in range(7):
                dest = MoveDestination("tableau", dest_col)
                if self._validate_move(src, dest)[0]:
                    candidates.append((2, src, dest, f"Move {card} from waste to column {dest_col + 1}."))

        for suit, pile in self.foundations.items():
            card = pile.peek()
            if card is None:
                continue
            src = MoveSource("foundation", suit.value)
            for dest_col in range(7):
                dest = MoveDestination("tableau", dest_col)
                if self._validate_move(src, dest)[0]:
                    candidates.append((
                        4, src, dest,
                        f"Move {card} from {suit.title} foundation to column {dest_col + 1}."
                    ))

        if candidates:
            _, source, destination, message = min(candidates, key=lambda item: item[0])
            return Hint(source, destination, message)
        if self.stock or self.waste:
            action = "draw from the stockpile" if self.stock else "recycle the waste into the stockpile"
            return Hint(None, None, f"No immediate legal pile move found. Try to {action}.")
        return Hint(None, None, "No legal moves found. Try Undo or start a new game.")

    def _validate_move(
        self, source: MoveSource, destination: MoveDestination
    ) -> tuple[bool, str, list[Card]]:
        if destination.kind not in ("tableau", "foundation"):
            return False, "Unknown destination pile.", []
        moving: list[Card]
        if source.kind == "tableau":
            if not isinstance(source.pile, int) or not 0 <= source.pile < 7:
                return False, "Invalid tableau column.", []
            pile = self.tableau[source.pile]
            if source.card_index is None or source.card_index < 0 or source.card_index >= len(pile):
                return False, "Select a card in the tableau first.", []
            moving = pile.to_list()[source.card_index:]
            if not moving or any(not card.face_up for card in moving):
                return False, "Only face-up tableau cards can be moved.", []
            if any(
                int(moving[i].rank) != int(moving[i + 1].rank) + 1
                or moving[i].color == moving[i + 1].color
                for i in range(len(moving) - 1)
            ):
                return False, "The selected sequence must descend by rank and alternate colors.", []
        elif source.kind == "waste":
            card = self.waste.peek()
            if card is None:
                return False, "The waste pile is empty.", []
            moving = [card]
        elif source.kind == "foundation":
            try:
                suit = Suit(str(source.pile))
            except ValueError:
                return False, "Invalid foundation pile.", []
            card = self.foundations[suit].peek()
            if card is None:
                return False, "That foundation pile is empty.", []
            moving = [card]
        else:
            return False, "Unknown source pile.", []

        card = moving[0]
        if destination.kind == "foundation":
            try:
                target_suit = Suit(str(destination.pile))
            except ValueError:
                return False, "Invalid foundation pile.", []
            if source.kind == "foundation":
                return False, "Foundation cards cannot move directly between foundations.", []
            if len(moving) != 1:
                return False, "Only one card at a time can move to a foundation.", []
            if source.kind == "tableau":
                pile = self.tableau[int(source.pile)]
                if int(source.card_index) != len(pile) - 1:
                    return False, "Only the top tableau card can move to a foundation.", []
            if card.suit != target_suit:
                return False, f"Move this card to the {card.suit.title} foundation.", []
            target = self.foundations[target_suit].peek()
            expected_rank = 1 if target is None else int(target.rank) + 1
            if int(card.rank) != expected_rank:
                return False, "Foundations must be built from Ace to King in the same suit.", []
            return True, f"Moved {card} to the {target_suit.title} foundation.", moving

        if not isinstance(destination.pile, int) or not 0 <= destination.pile < 7:
            return False, "Invalid tableau column.", []
        if source.kind == "tableau" and int(source.pile) == destination.pile:
            return False, "Choose a different tableau column as the destination.", []
        target_pile = self.tableau[destination.pile]
        target = target_pile.peek()
        if target is None:
            if card.rank != Rank.KING:
                return False, "Only a King can be placed on an empty tableau column.", []
        elif int(target.rank) != int(card.rank) + 1 or target.color == card.color:
            return False, "Tableau moves require descending ranks and alternating colors.", []
        return True, f"Moved {card} to tableau column {destination.pile + 1}.", moving

    @staticmethod
    def _flip_exposed_tableau_card(pile: Stack[Card]) -> None:
        exposed = pile.peek()
        if exposed is not None and not exposed.face_up:
            exposed.face_up = True

    def _finish_action(self, before: GameSnapshot) -> None:
        self._undo_stack.push(before)
        self._redo_stack.clear()
        self.move_count += 1
        self._rebuild_position_index()

    def _snapshot(self) -> GameSnapshot:
        def encode(pile: list[Card] | tuple[Card, ...]) -> list[CardState]:
            return [(card.suit.value, int(card.rank), card.face_up) for card in pile]
        return GameSnapshot(
            stock=encode(self.stock.to_list()),
            waste=encode(self.waste.to_list()),
            tableau=[encode(pile.to_list()) for pile in self.tableau],
            foundations={suit.value: encode(pile.to_list()) for suit, pile in self.foundations.items()},
            move_count=self.move_count,
        )

    @staticmethod
    def _decode(states: list[CardState]) -> list[Card]:
        return [Card(Suit(suit), Rank(rank), face_up) for suit, rank, face_up in states]

    def _restore(self, snapshot: GameSnapshot) -> None:
        self.stock = Queue(self._decode(snapshot.stock))
        self.waste = Stack(self._decode(snapshot.waste))
        self.tableau = [Stack(self._decode(cards)) for cards in snapshot.tableau]
        self.foundations = {
            Suit(suit): Stack(self._decode(cards))
            for suit, cards in snapshot.foundations.items()
        }
        self.move_count = snapshot.move_count
        self._rebuild_position_index()

    def _rebuild_position_index(self) -> None:
        """Dictionary index: card ID -> current area, pile, index and face state."""
        index: dict[str, dict[str, Any]] = {}
        for i, card in enumerate(self.stock.to_list()):
            index[card.card_id] = {"zone": "stock", "pile": None, "index": i, "face_up": card.face_up}
        for i, card in enumerate(self.waste.to_list()):
            index[card.card_id] = {"zone": "waste", "pile": None, "index": i, "face_up": card.face_up}
        for column, pile in enumerate(self.tableau):
            for i, card in enumerate(pile.to_list()):
                index[card.card_id] = {
                    "zone": "tableau", "pile": column, "index": i, "face_up": card.face_up
                }
        for suit, pile in self.foundations.items():
            for i, card in enumerate(pile.to_list()):
                index[card.card_id] = {
                    "zone": "foundation", "pile": suit.value, "index": i, "face_up": card.face_up
                }
        self.card_positions = index

    def all_cards(self) -> list[Card]:
        cards = self.stock.to_list() + self.waste.to_list()
        for pile in self.tableau:
            cards.extend(pile.to_list())
        for pile in self.foundations.values():
            cards.extend(pile.to_list())
        return cards

    def deck_integrity_ok(self) -> bool:
        cards = self.all_cards()
        ids = {card.card_id for card in cards}
        return len(cards) == 52 and len(ids) == 52 and len(self.card_positions) == 52
