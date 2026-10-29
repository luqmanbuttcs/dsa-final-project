"""Card models for the Klondike Solitaire project. No GUI dependencies."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum


class Suit(str, Enum):
    HEARTS = "hearts"
    DIAMONDS = "diamonds"
    CLUBS = "clubs"
    SPADES = "spades"

    @property
    def symbol(self) -> str:
        return {
            Suit.HEARTS: "♥",
            Suit.DIAMONDS: "♦",
            Suit.CLUBS: "♣",
            Suit.SPADES: "♠",
        }[self]

    @property
    def color(self) -> str:
        return "red" if self in (Suit.HEARTS, Suit.DIAMONDS) else "black"

    @property
    def title(self) -> str:
        return self.value.title()


class Rank(IntEnum):
    ACE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13

    @property
    def label(self) -> str:
        return {
            Rank.ACE: "A", Rank.JACK: "J", Rank.QUEEN: "Q", Rank.KING: "K"
        }.get(self, str(int(self)))


@dataclass(slots=True)
class Card:
    suit: Suit
    rank: Rank
    face_up: bool = False

    @property
    def color(self) -> str:
        return self.suit.color

    @property
    def card_id(self) -> str:
        """Stable ID used by the game's dictionary position index."""
        return f"{self.suit.value}:{int(self.rank)}"

    @property
    def label(self) -> str:
        return f"{self.rank.label}{self.suit.symbol}"

    def __str__(self) -> str:
        return f"{self.rank.label} of {self.suit.title}"


def make_deck() -> list[Card]:
    """Return a fresh, ordered, standard 52-card deck."""
    return [Card(suit, Rank(rank)) for suit in Suit for rank in range(1, 14)]
