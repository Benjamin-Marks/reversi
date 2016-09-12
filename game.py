"""The controllers for the reversi game.

Processes requests send from clients, updates database objects and notifies
clients accordingly.
"""
import json
import logging

import ai
from board import Board
from board import Square
from models import Account
from models import Game
from models import Lobby
import webapp2

from google.appengine.api import channel
from google.appengine.api import users
from google.appengine.ext import ndb


class StartMPGameRequest(webapp2.RequestHandler):
  """Handles initiating multiplayer game."""

  def post(self):
    """Starts multiplayer game.

    Player2 will send this request upon connecting to a lobby. Retrieve game
    they started, and send channel messages to both users that we've started.

    Sent Parameters:
      gameID: (int) The game being started
      playerID: (str) Player2's email
    """
    game_id = self.request.get('gameID')
    player_id = self.request.get('playerID')
    # Confirm game exists and this is player2
    game = Game.query(Game.id == int(game_id)).get()
    if game and game.player2 == player_id:
      board = Board.makeboard(game.size)
      game.board = board.to_json()
      response = {
          'board': game.board,
          'whitescore': 2,
          'blackscore': 2,
          'ourTurn': False,
          'ourmove': ' ',
          'theirmove': ' ',
          'message': "Game Started! Opponent's Turn"
      }
      channel.send_message(game.player2, json.dumps(response))
      response['ourTurn'] = True
      response['opponent'] = game.player2
      response['message'] = 'Game Started! Your Turn'
      channel.send_message(game.player1, json.dumps(response))
    else:
      logging.error('Received invalid request from %s for game %s', player_id,
                    game_id)


class ResignRequest(webapp2.RequestHandler):
  """Handles resign request from the client."""

  def post(self):
    """Validate resign request, close game, update user(s).

    Sent Parameters:
      gameID: (int) The id of the game being played.
      playerID: (str) The email of the resigning player.

    Retrieve the game. If it was a lobby, delete the lobby. If it was a game,
    resign from the game. If it was multiplayer, update the other user and
    update stats accordingly.
    """
    response = {}
    game_id = self.request.get('gameID')
    player_id = self.request.get('playerID')
    game = Game.query(Game.id == int(game_id)).get()
    if game and not game.done:
      # If this was a lobby, delete it
      if game.player2 == 'Nobody':
        logging.info("Deleting %s's lobby", game.player1)
        response['message'] = "You've closed this lobby"
        lobby = Lobby.query(Lobby.player == game.player1).get()
        if lobby:
          lobby.key.delete()
        game.key.delete()
      else:
        if game.player1 == player_id:
          game.winner = Square.black
          game.done = True
        elif game.player2 == player_id:
          game.winner = Square.white
          game.done = True
        else:
          logging.critical('hacking attempt?')
        # If we're a multiplayer game, tell the other player and update stats
        if not game.singleplayer:
          update_rankings(game)
          message = {
              'message': 'Your opponent resigned',
              'error': True
              }
          opponent = game.player1 if game.player2 == player_id else game.player2
          channel.send_message(opponent, json.dumps(message))
        response['message'] = 'You have resigned'
        game.put()
    elif game.done:
      response['message'] = 'This Game Is Already Over'
      response['error'] = True

    self.response.headers['Content-Type'] = 'application/json'
    self.response.write(json.dumps(response))


class JoinGameRequest(webapp2.RequestHandler):
  """Handles client request to join an existing lobby."""

  def post(self):
    """Gets the user asking to join the lobby and validates the request.

    Sent Parameters:
      lobby: (long) The lobby the client wants to join.
    """
    response = {}
    user = get_account(users.get_current_user().email())
    lobby = ndb.Key('Lobby', long(self.request.get('lobby'))).get()
    # Make sure lobby exists
    if lobby:
      # Don't join your own lobby
      if lobby.player == user.id:
        response['ownlobby'] = True
    else:
      response['gone'] = True

    self.response.write(json.dumps(response))


class MoveRequest(webapp2.RequestHandler):
  """Handles move requests from client."""

  def post(self):
    """Receives a move request, processes.

    First extracts params:
      gameID: (int) The game in question
      playerID: (str) Email of the player making the move
      row: (int) The row of the move
      column: (int) The column of the move

    We validate that this game exists, this player is in the game, and add
    the piece to the board. If this wasn't a legal move notify the user, if it
    was legal. If the game is singlepalyer, we process the AI's move.

    Singleplayer:
      We then process the AI's move based on the ai set in Game.player2, and if
      the player cannot move we continue ai_moves until the player has a legal
      move, then sync up with MP to pass back user data.

    We then begin writing our response. If it's a multiplayer game, we also
    create a separate response sent through a channel to the player who didn't
    move. If this move ended the game, we update player's rankings.
    """
    response = {}
    mpresponse = {}
    game_id = self.request.get('gameID')
    player_id = self.request.get('playerID')
    row = int(self.request.get('row'))
    column = int(self.request.get('column'))
    # Find the appropriate game, validate
    game = Game.query(Game.id == int(game_id)).get()
    if game and not game.done:
      if game.player1 == player_id:
        team = Square.white
      elif game.player2 == player_id:
        team = Square.black
      else:
        logging.critical('Hacking attempt?')
      if not game.moves:
        moves = []
      else:
        moves = json.loads(game.moves)
      board = Board.from_json(game.board, game.turn)
      points = board.add_piece(row, column, team)
      # Only update things if this is a legal move
      if points > 0:
        moves.append([row, column])
        response['ourmove'] = '( {}, {} )'.format(row + 1, column + 1)
        logging.info('player%s moved r%sc%s', team + 1, row, column)
        other_can_move = False
        if game.singleplayer:
          while board.get_turn() != team and board.get_turn() != Square.blank:
            other_can_move = True
            if game.player2 == 'Novice AI':
              ai_move = ai.novice_move(board)
            elif game.player2 == 'Weak AI':
              ai_move = ai.weak_move(board)
            elif game.player2 == 'Moderate AI':
              ai_move = ai.moderate_move(board)
            elif game.player2 == 'Strong AI':
              ai_move = ai.strong_move(board)
            else:
              logging.error('Player %s playing vs unknown AI %s', player_id, ai)
              return
            board.add_piece(ai_move[0], ai_move[1], Square.black)
            response['theirmove'] = '( {}, {} )'.format(ai_move[0] + 1,
                                                        ai_move[1] + 1)
            moves.append(ai_move)
        else:
          # Multiplayer: see if the other player can move
          other_can_move = (board.get_turn() != team)
        if board.get_turn() != Square.blank:
          # If the other player couldn't move, tell user
          if not other_can_move:
            logging.info('no legal moves for player%s', not team + 1)
            response['message'] = "Opponent can't move. Your turn"
            response['theirmove'] = 'N/A'
            response['ourTurn'] = True
            if not game.singleplayer:
              mpresponse['message'] = "You can't move. Opponent's turn"
              mpresponse['ourmove'] = 'N/A'
              mpresponse['ourTurn'] = False
          else:
            if game.singleplayer:
              response['message'] = 'Your Turn'
              response['ourTurn'] = True
            else:
              response['message'] = "Opponent's Turn"
              mpresponse['message'] = 'Your Turn'
              response['ourTurn'] = False
              mpresponse['ourTurn'] = True
        # If the game's over, update database and determine winner
        else:
          game.done = True
          response['done'] = True
          winner = board.who_won()
          if winner == Square.white:
            winteam = 'White Wins!'
            game.winner = Square.white
          elif winner == Square.black:
            winteam = 'Black Wins!'
            game.winner = Square.black
          else:
            winteam = "It's a Draw!"
            game.winner = Square.blank
          if not game.singleplayer:
            update_rankings(game)
          response['message'] = 'Game Over. {}'.format(winteam)

        game.moves = json.dumps(moves)
        game.board = board.to_json()
        game.turn = board.get_turn()
        game.put()
        response['board'] = game.board
        response['whitescore'] = board.num_pieces(Square.white)
        response['blackscore'] = board.num_pieces(Square.black)

        if not game.singleplayer:
          # If the move checks out, update other player
          mpresponse = dict(response.items() + mpresponse.items())
          mpresponse['theirmove'] = mpresponse['ourmove']
          del mpresponse['ourmove']
          mpplayer = game.player2 if player_id == game.player1 else game.player1
          channel.send_message(mpplayer, json.dumps(mpresponse))
      else:
        # If the move is illegal, send an error
        response['error'] = True
        response['message'] = 'That move is illegal'
        response['ourTurn'] = True
    elif game.done:
      logging.info('Player attempted move on finished game')
      response['message'] = 'This Game Is Already Over'
      response['error'] = True

    else:
      logging.error('Game id%s by %s not found', game_id, player_id)
      response['error'] = True
      response['message'] = 'Database could not find this game'
    self.response.headers['Content-Type'] = 'application/json'
    self.response.write(json.dumps(response))


def update_rankings(game):
  """Determine the winner of a multiplayer game, update account stats.

  Args:
    game: (Game) The game that just finished.
  """
  if not game.done:
    logging.warning('Bad rank update on game %s, not done', game.id)
  if game.singleplayer:
    logging.warning('Bad rank update on game %s, singleplayer', game.id)
  else:
    player1 = get_account(game.player1)
    player1.games += 1
    player2 = get_account(game.player2)
    player2.games += 1
    if game.winner != Square.blank:
      if game.winner == Square.white:
        player1.wins += 1
        player2.losses += 1
        update_elo(player1, player2, False)
      else:
        player1.losses += 1
        player2.wins += 1
        update_elo(player2, player1, False)
    else:
      player1.draws += 1
      player2.draws += 1
      update_elo(player1, player2, True)

    player1.put()
    player2.put()


def update_elo(winner, loser, draw):
  """Updates the elo for the given accounts.

  Args:
    winner: (Account) The winner's account.
    loser: (Account) The loser's account.
    draw: (bool) Was this a draw?
  """
  k_score = 64
  transform_w = float(pow(10, winner.elo/400))
  transform_l = float(pow(10, loser.elo/400))

  expect_w = transform_w/(transform_l + transform_w)
  expect_l = transform_l/(transform_l + transform_w)

  score_w = 1 if (not draw) else 0.5
  score_l = 0 if (not draw) else 0.5

  winner.elo = int(winner.elo + (k_score * (score_w - expect_w)))
  loser.elo = int(loser.elo + (k_score * (score_l - expect_l)))


def get_account(email):
  """Retrieves an account by user's email. If account doesn't exist, make it.

  Args:
    email: (str) The user's email

  Returns:
    Account: The user's account object from ndb
  """
  q = Account.query(Account.id == email)
  account = q.get()
  # New User, create account with default settings
  if account is None:
    logging.info('Making new account for %s', email)
    account = Account(id=email, photo=None,
                      games=0, wins=0, draws=0, losses=0, elo=1200)
    account.put()

  return account

