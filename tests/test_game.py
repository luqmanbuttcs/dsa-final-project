import unittest

from card import Card, Rank, Suit, make_deck
from data_structures import Queue, Stack
from game import GameEngine, MoveDestination, MoveSource


class GameSetupTests(unittest.TestCase):
    def test_new_game_deals_all_52_unique_cards(self):
        game = GameEngine(seed=123)
        self.assertTrue(game.deck_integrity_ok())
        self.assertEqual(game.tableau_sizes, [1, 2, 3, 4, 5, 6, 7])
        self.assertEqual(len(game.stock), 24)
        self.assertEqual(len(game.waste), 0)
        for pile in game.tableau:
            cards = pile.to_list()
            self.assertEqual(sum(card.face_up for card in cards), 1)
            self.assertTrue(cards[-1].face_up)
            self.assertTrue(all(not card.face_up for card in cards[:-1]))

    def test_position_dictionary_covers_every_card(self):
        game = GameEngine(seed=2)
        self.assertEqual(len(game.card_positions), 52)
        location = game.card_positions[game.tableau[0].peek().card_id]
        self.assertEqual(location["zone"], "tableau")
        self.assertEqual(location["pile"], 0)

    def test_victory_requires_all_cards_in_foundations(self):
        game = GameEngine(seed=4)
        self.assertFalse(game.has_won)
        deck = make_deck()
        game.stock = Queue()
        game.waste = Stack()
        game.tableau = [Stack() for _ in range(7)]
        game.foundations = {suit: Stack() for suit in Suit}
        for suit in Suit:
            suited_cards = [card for card in deck if card.suit == suit]
            for card in suited_cards:
                card.face_up = True
            game.foundations[suit] = Stack(suited_cards)
        game._rebuild_position_index()
        self.assertTrue(game.has_won)
        self.assertTrue(game.deck_integrity_ok())


class StockTests(unittest.TestCase):
    def test_draw_one_then_undo_and_redo(self):
        game = GameEngine(draw_mode=1, seed=15)
        first_id = game.stock.peek().card_id
        result = game.draw_from_stock()
        self.assertTrue(result.success)
        self.assertEqual(len(game.stock), 23)
        self.assertEqual(len(game.waste), 1)
        self.assertEqual(game.waste.peek().card_id, first_id)
        self.assertTrue(game.undo().success)
        self.assertEqual(len(game.stock), 24)
        self.assertEqual(len(game.waste), 0)
        self.assertTrue(game.redo().success)
        self.assertEqual(game.waste.peek().card_id, first_id)

    def test_draw_three_draws_up_to_three(self):
        game = GameEngine(draw_mode=3, seed=7)
        game.draw_from_stock()
        self.assertEqual(len(game.stock), 21)
        self.assertEqual(len(game.waste), 3)
        self.assertTrue(all(card.face_up for card in game.waste))

    def test_stock_recycles_waste_in_original_order(self):
        game = GameEngine(seed=1)
        first = Card(Suit.HEARTS, Rank.FIVE, True)
        second = Card(Suit.SPADES, Rank.SIX, True)
        game.stock = Queue()
        game.waste = Stack([first, second])
        game._rebuild_position_index()
        result = game.draw_from_stock()
        self.assertTrue(result.success)
        self.assertEqual([card.card_id for card in game.stock], [first.card_id, second.card_id])
        self.assertTrue(all(not card.face_up for card in game.stock))
        self.assertEqual(len(game.waste), 0)
        game.set_draw_mode(1)
        game.draw_from_stock()
        self.assertEqual(game.waste.peek().card_id, first.card_id)

    def test_empty_stock_and_waste_is_a_safe_noop(self):
        game = GameEngine(seed=1)
        game.stock = Queue()
        game.waste = Stack()
        before = game._snapshot()
        result = game.draw_from_stock()
        self.assertFalse(result.success)
        self.assertEqual(game._snapshot(), before)


class MoveTests(unittest.TestCase):
    @staticmethod
    def small_game() -> GameEngine:
        game = GameEngine(seed=9)
        game.stock = Queue()
        game.waste = Stack()
        game.tableau = [Stack() for _ in range(7)]
        game.foundations = {suit: Stack() for suit in Suit}
        game.tableau[0] = Stack([
            Card(Suit.CLUBS, Rank.TEN, False),
            Card(Suit.HEARTS, Rank.SEVEN, True),
        ])
        game.tableau[1] = Stack([Card(Suit.SPADES, Rank.EIGHT, True)])
        game._rebuild_position_index()
        return game

    def test_legal_alternating_color_move_flips_exposed_card(self):
        game = self.small_game()
        source = MoveSource("tableau", 0, 1)
        target = MoveDestination("tableau", 1)
        result = game.move(source, target)
        self.assertTrue(result.success, result.message)
        self.assertEqual(len(game.tableau[0]), 1)
        self.assertTrue(game.tableau[0].peek().face_up)
        self.assertEqual(len(game.tableau[1]), 2)
        self.assertEqual(game.tableau[1].peek().rank, Rank.SEVEN)
        self.assertEqual(game.move_count, 1)

    def test_invalid_move_does_not_mutate_state(self):
        game = self.small_game()
        before = game._snapshot()
        result = game.move(
            MoveSource("tableau", 0, 1), MoveDestination("tableau", 2)
        )
        self.assertFalse(result.success)
        self.assertEqual(game._snapshot(), before)
        self.assertFalse(game.can_undo)

    def test_king_can_move_to_empty_column(self):
        game = self.small_game()
        game.tableau[0] = Stack([Card(Suit.HEARTS, Rank.KING, True)])
        game._rebuild_position_index()
        result = game.move(MoveSource("tableau", 0, 0), MoveDestination("tableau", 6))
        self.assertTrue(result.success)
        self.assertEqual(game.tableau[6].peek().rank, Rank.KING)

    def test_ace_moves_to_matching_foundation(self):
        game = self.small_game()
        ace = Card(Suit.HEARTS, Rank.ACE, True)
        game.waste = Stack([ace])
        game._rebuild_position_index()
        result = game.move(MoveSource("waste"), MoveDestination("foundation", Suit.HEARTS.value))
        self.assertTrue(result.success)
        self.assertEqual(game.foundations[Suit.HEARTS].peek().card_id, ace.card_id)
        self.assertEqual(len(game.waste), 0)

    def test_face_up_sequence_moves_as_a_unit(self):
        game = self.small_game()
        sequence = [
            Card(Suit.SPADES, Rank.KING, True),
            Card(Suit.HEARTS, Rank.QUEEN, True),
            Card(Suit.SPADES, Rank.JACK, True),
        ]
        game.tableau[0] = Stack(sequence)
        game.tableau[6] = Stack()
        game._rebuild_position_index()
        result = game.move(MoveSource("tableau", 0, 0), MoveDestination("tableau", 6))
        self.assertTrue(result.success, result.message)
        self.assertEqual([card.card_id for card in game.tableau[6]], [card.card_id for card in sequence])
        self.assertEqual(len(game.tableau[0]), 0)

    def test_foundation_top_can_return_to_tableau_when_legal(self):
        game = self.small_game()
        foundation_cards = [Card(Suit.HEARTS, Rank(rank), True) for rank in range(1, 6)]
        game.foundations[Suit.HEARTS] = Stack(foundation_cards)
        game.tableau[0] = Stack([Card(Suit.CLUBS, Rank.SIX, True)])
        game._rebuild_position_index()
        result = game.move(
            MoveSource("foundation", Suit.HEARTS.value), MoveDestination("tableau", 0)
        )
        self.assertTrue(result.success, result.message)
        self.assertEqual(game.tableau[0].peek().rank, Rank.FIVE)
        self.assertEqual(game.foundations[Suit.HEARTS].peek().rank, Rank.FOUR)

    def test_foundation_requires_ace_to_king_and_matching_suit(self):
        game = self.small_game()
        seven = Card(Suit.HEARTS, Rank.SEVEN, True)
        game.waste = Stack([seven])
        before = game._snapshot()
        result = game.move(MoveSource("waste"), MoveDestination("foundation", Suit.HEARTS.value))
        self.assertFalse(result.success)
        self.assertEqual(game._snapshot(), before)

    def test_undo_redo_restores_cards_and_move_counter(self):
        game = self.small_game()
        game.move(MoveSource("tableau", 0, 1), MoveDestination("tableau", 1))
        after_move = game._snapshot()
        self.assertEqual(game.move_count, 1)
        self.assertTrue(game.undo().success)
        self.assertEqual(game.move_count, 0)
        self.assertTrue(game.tableau[0].peek().face_up)
        self.assertTrue(game.redo().success)
        self.assertEqual(game._snapshot(), after_move)

    def test_hint_is_legal_and_does_not_change_state(self):
        game = GameEngine(seed=20)
        before = game._snapshot()
        hint = game.get_hint()
        self.assertTrue(hint.message)
        self.assertEqual(game._snapshot(), before)
        if hint.source is not None and hint.destination is not None:
            self.assertTrue(game._validate_move(hint.source, hint.destination)[0])


if __name__ == "__main__":
    unittest.main()
