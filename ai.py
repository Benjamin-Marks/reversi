"""Handles AI logic.

The AI is divided into four types: Novice, Weak, Moderate, and Strong. Each AI
will process the current board state, and choose a move designed to give a
appropriate level of difficulty.
"""
from bisect import bisect
from copy import deepcopy
import logging
import random

from board import Square


def novice_move(board):
  """Novice AI - lightly weighted towards a low scoring move.

  Args:
    board: (Board) The game board.

  Returns:
    Array: Our chosen move.
  """
  valid_moves = _get_moves(board, Square.black)

  # Adjust Scores to prefer low point moves
  large = valid_moves[0][2]
  for i in range(len(valid_moves)):
    valid_moves[i][2] = large - valid_moves[i][2]

  # Sorted ascending - weigh low point moves more
  weights = [2, 3, 4]
  our_move = _weight_moves_thirds(valid_moves, weights)
  logging.info('Novice AI chose r%sc%s', our_move[0], our_move[1])
  return our_move


def weak_move(board):
  """Weak AI - makes a random valid move.

  Args:
    board: (Board) The game board.

  Returns:
    Array: Our chosen move.
  """
  valid_moves = _get_moves(board, Square.black)
  # Return a random valid move
  our_move = valid_moves[random.randrange(0, len(valid_moves))]
  logging.info('Weak AI chose r%sc%s', our_move[0], our_move[1])
  return our_move


def moderate_move(board):
  """Moderate AI - makes a valid move weighted towards high scores.

  Args:
    board: (Board) The game board.

  Returns:
    Array: Our chosen move.
  """
  # Sort valid moves by score
  valid_moves = _get_moves(board, Square.black)

  # First third of options get x5, second third get x2, won't pick last third
  weights = [5, 2, 0]
  our_move = _weight_moves_thirds(valid_moves, weights)

  logging.info('Moderate AI chose r%sc%s', our_move[0], our_move[1])
  return our_move


def strong_move(board):
  """Strong AI - brute force recurse to future to get highest score scenario.

  Args:
    board: (Board) The game board.

  Returns:
    Array: Our chosen move.
  """
  # How many moves in advance to think - THIS CANNOT BE 0
  moves_in_advance = 3
  our_move = strong_move_recurse(deepcopy(board), moves_in_advance, None)
  logging.getLogger().setLevel(logging.DEBUG)
  logging.info('Strong AI chose r%sc%s', our_move[0][0], our_move[0][1])
  return our_move[0]


def strong_move_recurse(board, num_moves_left, move):
  """Recursive method to calculate StrongAI's best possible move.

  Creates a list of every possible move, and white's highest scoring response
  to that move. Proceed down moves_in_advance turns, and returns the move
  with the largest increase in black pieces.

  Args:
    board: (Board) The game board in the recursed state.
    num_moves_left: The number of turns in advance to think.
    move: The most recent AI move that got us to this state.

  Returns:
    Tuple: The move, and the number of black pieces on the board.
  """
  # If we're done, return black's standing on the board and the move
  if num_moves_left == 0:
    return (move, board.num_pieces(Square.black))
  valid_moves = _get_moves(board, Square.black)
  logging.getLogger().setLevel(logging.WARNING)
  move_results = []

  for move in valid_moves:
    new_board = deepcopy(board)
    new_board.add_piece(move[0], move[1], Square.black)
    # If this was our final move, make sure there are no more
    if new_board.get_turn() == Square.blank:
      num_moves_left = 1
    while new_board.get_turn() == Square.white:
      # Get highest scoring white move
      white_moves = _get_moves(new_board, Square.white)
      logging.getLogger().setLevel(logging.WARNING)
      white_move = white_moves[0]
      new_board.add_piece(white_move[0], white_move[1], Square.white)
      if new_board.get_turn() == Square.blank:
        num_moves_left = 1
    move_result = strong_move_recurse(new_board, num_moves_left - 1, move)
    move_results.append([move, move_result[1]])
  # Get best move result
  sorted_moves = sorted(move_results, key=lambda x: x[1], reverse=True)
  best_move = sorted_moves[0]
  return (best_move[0], best_move[1])


def _weight_moves_thirds(valid_moves, weights):
  """Weights each third of valid moves according to weights, randomly picks one.

  Args:
    valid_moves: (Array) The full list of valid moves.
    weights: (Array) How to weigh each section of the moves.

  Returns:
    Array: The location of the chosen move.
  """
  # Assign weights to points
  total = 0
  cumulative_weights = []
  for i in range(len(valid_moves)):
    if i * 3 <= len(valid_moves):
      valid_moves[i][2] *= weights[0]
    elif i * 1.5 <= len(valid_moves):
      valid_moves[i][2] *= weights[1]
    else:
      valid_moves[i][2] *= weights[2]

    total += valid_moves[i][2]
    cumulative_weights.append(total)
  # Pick our move based on the weights
  our_move = bisect(cumulative_weights, random.random() * total)
  # Prevent overflow if random is all the way at the max
  if our_move == len(valid_moves):
    our_move -= 1
  return valid_moves[our_move]


def _get_moves(board, team):
  """Generates a list of possible legal moves, sorted by score.

  Args:
    board: (Board) The game board.
    team: (int) Our team.

  Returns:
    Array: A sorted list of valid moves.
  """
  valid_moves = []
  # Disable warning logs so board doesn't complain about invalid moves
  logging.getLogger().setLevel(logging.ERROR)
  for r in xrange(0, board.get_size()):
    for c in xrange(0, board.get_size()):
      score = board.flip_score(r, c, team)
      if score != 0:
        valid_moves.append([r, c, score])
  logging.getLogger().setLevel(logging.DEBUG)
  return sorted(valid_moves, key=lambda x: x[2], reverse=True)

