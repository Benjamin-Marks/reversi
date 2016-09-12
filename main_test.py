"""Tests for google3.experimental.users.benjaminmarks.reversi ."""

import unittest

from board import Board
from board import Square


class BoardTest(unittest.TestCase):
  new_4_board = [
      [2, 2, 2, 2],
      [2, 0, 1, 2],
      [2, 1, 0, 2],
      [2, 2, 2, 2]
  ]
  new_8_board = [
      [2, 2, 2, 2, 2, 2, 2, 2],
      [2, 2, 2, 2, 2, 2, 2, 2],
      [2, 2, 2, 2, 2, 2, 2, 2],
      [2, 2, 2, 0, 1, 2, 2, 2],
      [2, 2, 2, 1, 0, 2, 2, 2],
      [2, 2, 2, 2, 2, 2, 2, 2],
      [2, 2, 2, 2, 2, 2, 2, 2],
      [2, 2, 2, 2, 2, 2, 2, 2]
  ]

  def test_board_creation(self):
    board = Board.makeboard(4)
    if not board:
      self.fail('Board not made')

  def test_board_initial_setup_size4(self):
    board = Board.makeboard(4)
    self.assertEqual(board.board, self.new_4_board)
    self.assertEqual(board.get_size(), 4)

  def test_board_initial_setup_size8(self):
    board = Board.makeboard(8)
    self.assertEqual(board.board, self.new_8_board)

  def test_board_can_count_pieces(self):
    board = Board.makeboard(6)
    self.assertEqual(board.num_pieces(Square.white), 2)
    self.assertEqual(board.num_pieces(Square.black), 2)

  def test_board_valid_move(self):
    expected_board = [
        [2, 2, 2, 2],
        [2, 0, 0, 0],
        [2, 1, 0, 2],
        [2, 2, 2, 2]
    ]
    board = Board.makeboard(4)
    board.add_piece(1, 3, Square.white)
    self.assertEqual(board.board, expected_board)

  def test_board_count_moves(self):
    board = Board.makeboard(6)
    board.add_piece(1, 3, Square.white)
    self.assertEqual(board.get_num_moves(), 1)

  def test_board_illegal_move_out_of_range(self):
    board = Board.makeboard(4)
    board.add_piece(0, 6, Square.white)
    self.assertEqual(board.board, self.new_4_board)

  def test_board_illegal_move_no_points(self):
    board = Board.makeboard(8)
    board.add_piece(1, 1, Square.white)
    self.assertEqual(board.board, self.new_8_board)

  def test_board_illegal_move_wrong_team(self):
    board = Board.makeboard(4)
    board.add_piece(1, 0, Square.black)
    self.assertEqual(board.board, self.new_4_board)

  def test_board_game_over_white_win(self):
    board = Board.makeboard(4)
    moves = [[3, 1], [3, 2],
             [3, 3], [3, 0],
             [0, 2], [2, 3],
             [1, 3], [0, 3],
             [0, 1], [0, 0],
             [2, 0], [1, 0]]
    self.do_moves(moves, board)
    self.assertEqual(board.who_won(), Square.white)

  def test_board_game_over_black_win(self):
    board = Board.makeboard(4)
    moves = [[2, 0], [3, 2],
             [2, 3], [3, 0],
             [3, 1], [1, 0],
             [0, 2], [3, 3],
             [0, 1], [0, 0],
             [1, 3], [0, 3]]
    self.do_moves(moves, board)
    self.assertEqual(board.who_won(), Square.black)

  def test_board_game_over_tie(self):
    board = Board.makeboard(4)
    moves = [[1, 3], [2, 3],
             [3, 3], [0, 3],
             [0, 2], [0, 1],
             [0, 0], [3, 2],
             [2, 0], [3, 0],
             [3, 1], [1, 0]]
    self.do_moves(moves, board)
    self.assertEqual(board.who_won(), Square.blank)

  def test_board_game_over_black_eliminated(self):
    board = Board.makeboard(4)
    moves = [[1, 3], [2, 3],
             [3, 1], [2, 0],
             [3, 3], [0, 1],
             [3, 0]]
    self.do_moves(moves, board)
    board.add_piece(0, 0, Square.white)
    board.add_piece(0, 2, Square.black)
    board.add_piece(0, 3, Square.white)
    board.add_piece(1, 0, Square.white)
    self.assertEqual(board.who_won(), Square.white)
    self.assertEqual(board.num_pieces(Square.black), 0)
    self.assertEqual(board.get_squares_left(), 1)

  def test_board_player_no_move(self):
    moves = [[1, 3], [2, 3],
             [3, 3], [0, 3],
             [0, 1]]
    board = Board.makeboard(4)
    self.do_moves(moves, board)
    self.assertEqual(board.can_move(Square.black), False)
    self.assertEqual(board.get_turn(), Square.white)

  def test_board_game_over_no_moves(self):
    moves = [[1, 3], [2, 3],
             [3, 3], [0, 3],
             [0, 1]]
    board = Board.makeboard(4)
    self.do_moves(moves, board)
    board.add_piece(3, 0, Square.white)
    self.assertEqual(board.who_won(), Square.white)

  def test_remake_board(self):
    board = Board.makeboard(8)
    board2 = Board.makeboard(8)
    remadeboard = Board.from_json(board.to_json(), Square.white)
    self.assertEqual(remadeboard.board, board2.board)

  # Helper function, executes given moves on board
  # Note: assumes other player always has a valid move
  def do_moves(self, moves, board):
    cur_team = Square.white
    for move in moves:
      board.add_piece(move[0], move[1], cur_team)
      if cur_team == Square.white:
        cur_team = Square.black
      else:
        cur_team = Square.white


if __name__ == '__main__':
  unittest.main()
