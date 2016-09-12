"""Represents the Board of a Reversi game."""
import json
import logging


class Square(object):
  """Enum to differentiate between teams.

  Note: We don't extend from enum to allow for easy serialization.
  """
  white = 0
  black = 1
  blank = 2


class Board(object):
  """Represents the board of a reversi game."""

  def __init__(self, size, board, turn):
    if size:
      self.board = [[Square.blank for _ in range(size)] for _ in range(size)]
      self.board[size/2][size/2] = self.board[size/2-1][size/2-1] = Square.white
      self.board[size/2][size/2-1] = self.board[size/2-1][size/2] = Square.black
    else:
      self.board = board
    self.turn = turn

  # Creating a new board
  @classmethod
  def makeboard(cls, size):
    return cls(size, None, Square.white)

  # Creating a board in progress
  @classmethod
  def remakeboard(cls, board, turn):
    return cls(None, board, turn)

  def to_json(self):
    """Converts the board to json."""
    return json.dumps(self.board)

  @staticmethod
  def from_json(data, turn):
    """Parses a json board and returns a new Board object.

    Args:
      data: (str) The board, encoded as json.
      turn: (Square) The team set to move next

    Returns:
      Board: The recreated board.
    """
    return Board.remakeboard(json.loads(data), turn)

  def get_size(self):
    """Gets the size of a board side."""
    return len(self.board)

  def get_num_moves(self):
    """Gets the number of moves made in the game."""
    return len(self.board) * len(self.board) - 4 - self.get_squares_left()

  def get_squares_left(self):
    """Gets the number of blank squares on the board."""
    remaining = 0
    for r in self.board:
      for c in r:
        if c == Square.blank:
          remaining += 1
    return remaining

  def get_turn(self):
    """Returns whose turn it is."""
    return self.turn

  def add_piece(self, r, c, team):
    """Validates input and addes a piece to the board.

    Args:
      r: (int) The row.
      c: (int) The column.
      team: (Square) The team making the move.

    Returns:
      int: The number of points scored by the move
    """
    if not self._validate_input(r, c, team):
      return 0
    points = self._flip(r, c, self.turn)
    if points == 0:
      logging.info('Illegal move r%sc%s: no points', r, c)
      return 0
    self.board[r][c] = self.turn
    self._set_next_turn()
    return points

  def _validate_input(self, r, c, team):
    """Ensures move input is a legal move.

    Args:
      r: (int) The row.
      c: (int) The column.
      team: (Square) The team making the move.

    Returns:
      bool: the legality of the move
    """
    if r < 0 or r >= len(self.board) or c < 0 or c >= len(self.board):
      logging.error('Move r%sc%s not in range 0, %s', r, c, len(self.board))
    elif self.turn != team:
      logging.info('Bad Move by player%s: Not your turn', team + 1)
    elif self.board[r][c] != Square.blank:
      logging.info('Bad Move r%sc%s: Not a blank square', r, c)
    else:
      return True
    return False

  def _set_next_turn(self):
    """Determines if players can move and sets the next turn."""

    # Check if each player can move
    cur_turn = self.turn
    self.turn = Square.black
    black_able = self.can_move(Square.black)
    self.turn = Square.white
    white_able = self.can_move(Square.white)
    self.turn = cur_turn
    if not black_able and not white_able:
      logging.info('No more legal moves')
      self.turn = Square.blank

    # Set next turn
    if self.turn == Square.white:
      self.turn = Square.black
      # Break up if statements so that our checks pass validate_input
      if not black_able:
        self.turn = Square.white
    elif self.turn == Square.black:
      self.turn = Square.white
      # Break up if statements so that our checks pass validate_input
      if not white_able:
        self.turn = Square.black

  # Method wrapper for flipping
  def _flip(self, r, c, team):
    return self._validate_flip(r, c, team, True, True)

  # Method wrapper for getting score of a potential flip
  def flip_score(self, r, c, team):
    if self._validate_input(r, c, team):
      return self._validate_flip(r, c, team, False, True)
    return 0

  # Method wrapper for seeing if move is legal. Returns Boolean
  def can_flip(self, r, c, team):
    logging.getLogger().setLevel(logging.ERROR)  # Don't log validation errors
    if (self._validate_input(r, c, team) and
        self._validate_flip(r, c, team, False, False)):
      logging.getLogger().setLevel(logging.DEBUG)
      return True
    logging.getLogger().setLevel(logging.DEBUG)
    return False

  # Internal method for flipping pieces
  # Assumes everything has been validated
  def _flip_pieces(self, pieces):
    for piece in pieces:
      if self.board[piece[0]][piece[1]] == Square.white:
        self.board[piece[0]][piece[1]] = Square.black
      else:
        self.board[piece[0]][piece[1]] = Square.white

  # Internal method for determining move legality and score
  def _validate_flip(self, r, c, team, should_flip, keep_score):
    """Handles validating moves and flipping pieces.

    Args:
      r: (int) The row we're placing a piece.
      c: (int) The column we're placing a piece.
      team: (Square) The team placing the piece.
      should_flip: (bool) Should we actually flip the pieces or just check move?
      keep_score: (bool) Are we checking legality or score?

    Returns:
      int: The move's score (or 1 for score >= 1 if keep_score is false)
    """
    flip_pieces = []
    # Search each direction on the board
    for dr in xrange(-1, 2):
      for dc in xrange(-1, 2):
        if dr == 0 and dc == 0:
          continue
        cur_r = r + dr
        cur_c = c + dc
        found_other = False
        while (cur_r < len(self.board) and cur_r >= 0 and
               cur_c < len(self.board[0]) and cur_c >= 0):
          if self.board[cur_r][cur_c] == Square.blank:
            break
          elif self.board[cur_r][cur_c] == team:
            # If we found the other player in between, flip. Otherwise break
            if found_other:
              if keep_score:
                # Calculate all the flipped pieces
                mv_r = -1 * dr
                mv_c = -1 * dc
                while cur_r + mv_r != r or cur_c + mv_c != c:
                  cur_r += mv_r
                  cur_c += mv_c
                  flip_pieces.append([cur_r, cur_c])
              else:
                # If we're checking that this square has a legal move, it does
                return 1
            break
          else:
            found_other = True
          cur_r += dr
          cur_c += dc

    # Remove duplicate squares
    flip_set = set(tuple(i) for i in flip_pieces)
    if should_flip:
      self._flip_pieces(flip_set)
    return len(flip_set)

  def can_move(self, team):
    """Determines if the given team has a valid move.

    Args:
      team: (Square) The team.

    Returns:
      bool: If the team has a valid move
    """
    for r in xrange(0, len(self.board)):
      for c in xrange(0, len(self.board)):
        if self.can_flip(r, c, team):
          return True
    return False

# Count Squares on a full board to determine the winner
  def who_won(self):
    """Counts the squares on a board to determine the winner.

    Returns:
      Square: The winning team.
    """
    white_advantage = 0

    if self.turn != Square.blank:
      return -1
    for r in xrange(len(self.board)):
      for c in xrange(len(self.board)):
        if self.board[r][c] == Square.white:
          white_advantage += 1
        elif self.board[r][c] == Square.black:
          white_advantage -= 1
    if white_advantage == 0:
      return Square.blank
    elif white_advantage > 0:
      return Square.white
    else:
      return Square.black

  # Count number of pieces that belong to the given team
  def num_pieces(self, team):
    pieces = 0
    for r in xrange(len(self.board)):
      for c in xrange(len(self.board)):
        if self.board[r][c] == team:
          pieces += 1
    return pieces

