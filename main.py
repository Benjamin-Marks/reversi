"""The Views in the reversi app.

Renders all of the pages on the website
"""
import logging
import os

from board import Board
from board import Square
from game import get_account
from game import JoinGameRequest
from game import MoveRequest
from game import ResignRequest
from game import StartMPGameRequest
import jinja2
from models import Account
from models import Game
from models import Lobby
from models import NumGames
import webapp2

from google.appengine.api import channel
from google.appengine.api import users
from google.appengine.ext import ndb


class MainPage(webapp2.RequestHandler):
  """The Website's landing page, verifies user account."""

  def get(self):
    # Make user's account if they don't have one
    get_account(users.get_current_user().email())

    self.response.write(render({}, 'index.html'))


class AIGamePage(webapp2.RequestHandler):
  """Renders single player games."""

  def get(self):
    """Renders jinja template to set up game."""
    template_values = {
        'singleplayer': True,
        'playing': False
    }
    self.response.write(render(template_values, 'game.html'))

  def post(self):
    """Creates singleplayer game.

    We receive user parameters for difficulty and board size, create the
    database representation of the game, and start broadcasting.
    """
    # Set up the game
    size = int(self.request.get('size'))
    player1 = users.get_current_user().email()
    ai = self.request.get('ai')

    # Add Game to Datastore
    our_game_num = get_game_num()
    board = Board.makeboard(size)
    our_game = Game(id=our_game_num, size=size, turn=Square.white,
                    player1=player1, singleplayer=True, player2=ai,
                    board=board.to_json())
    our_game.put()

    template_values = {
        'playing': True,
        'opponent': ai,
        'size': size,
        'singleplayer': True,
        'gameID': our_game_num,
        'playerID': player1,
        'data': board.to_json()
    }
    self.response.write(render(template_values, 'game.html'))


class MultiLobbyPage(webapp2.RequestHandler):
  """Renders list of players waiting for multiplayer opponents."""

  def get(self):
    """Gets list of lobbies, renders them."""
    lobbies = Lobby.query().fetch()
    lobby_render = []
    if lobbies:
      no_lobbies = False
      for lobby in lobbies:
        lobby_render.append([lobby.player, lobby.elo, lobby.key.id()])
    else:
      no_lobbies = True

    template_values = {
        'lobbies': lobby_render,
        'no_lobbies': no_lobbies
    }
    self.response.write(render(template_values, 'lobby.html'))


class MultiGamePage(webapp2.RequestHandler):
  """Renders multiplayer game."""

  def get(self):
    """Loads lobby parameters or joins game.

    This function is called in one of two scenarios. A player is either making
    a lobby, in which case we show them a board size option, or they are
    joining an existing lobby, in which case we add them to the game and
    remove the lobby.
    """
    player = users.get_current_user().email()
    template_values = {}
    # If we're a lobby request, just load the game screen
    if self.request.get('makelobby'):
      template_values['playing'] = False
      # Check if player already has a lobby
      lobby = Lobby.query(Lobby.player == player).get()
      if lobby:
        template_values['multi_error'] = True
        template_values['error_message'] = (
            "You've already made a lobby. Leave it before making another")
    else:
      # Is requester joining a game?
      game = self.request.get('game')
      if game:
        lobby = ndb.Key('Lobby', long(game)).get()
        if not lobby:
          logging.info('Player %s joined a nonexistant lobby', player)
          template_values['multi_error'] = True
          template_values['error_message'] = 'This Lobby no longer exists'
        else:
          # Add our info to the game, destroy the lobby
          our_game_num = lobby.game
          our_game = Game.query(Game.id == our_game_num).get()
          if game:
            our_game.player2 = player
            opponent = our_game.player1
            our_game.put()

            lobby.key.delete()
            logging.info("Player %s joined %s's lobby", player, opponent)
          else:
            # If the game somehow doesn't exist, display error
            template_values['multi_error'] = True
            template_values['error_message'] = 'Could not find this lobby'
            logging.error('Error loading game %s', our_game_num)
      else:
        logging.info('Illegal multigame load')
        template_values['multi_error'] = True
        template_values['error_message'] = 'Make a lobby before coming here.'
        self.response.write(render(template_values, 'game.html'))

    # If we're rendering a game, do that. Otherwise show standard page
    if (template_values.get('multi_error') or
        template_values.get('playing') is False):
      self.response.write(render(template_values, 'game.html'))
    else:
      self.render_multi_page(our_game, False)

  def post(self):
    """Called when a player finished a lobby. Sets up Game and Lobby objects."""
    player = get_account(users.get_current_user().email())
    size = int(self.request.get('size'))
    opponent = 'Nobody'
    board = Board.makeboard(size)
    our_game_num = get_game_num()
    our_game = Game(id=our_game_num, size=size, turn=Square.white,
                    player1=player.id, player2=opponent,
                    singleplayer=False, board=board.to_json())
    our_game.put()

    # Add game_num to lobby, put it into db
    lobby = Lobby(player=player.id, elo=player.elo, game=our_game_num)
    lobby.put()
    logging.info('Player %s made a new lobby game %s', player.id, our_game_num)

    self.render_multi_page(our_game, True)

  def render_multi_page(self, game, is_owner):
    """Renders multiplayer game.

    Args:
      game: (Game) The game we are rendering.
      is_owner: (bool) Is player1 rendering?
    """
    player = game.player1 if is_owner else game.player2
    opponent = game.player2 if is_owner else game.player1

    token = channel.create_channel(player)
    template_values = {
        'playing': True,
        'token': token,
        'opponent': opponent,
        'size': game.size,
        'gameID': game.id,
        'playerID': player,
        'data': game.board
    }
    self.response.write(render(template_values, 'game.html'))


class RankingPage(webapp2.RequestHandler):
  """Displays ranking of current users and their elos."""

  def get(self):
    """Gets a sorted list of players from the database, render them."""
    players = sorted(Account.query().fetch(),
                     key=lambda account: account.elo, reverse=True)
    template_values = {
        'players': players
    }
    self.response.write(render(template_values, 'ranking.html'))


def get_game_num():
  """Loads NumGames, retrieves the next number and increment."""
  num_games = NumGames.query().get()
  if num_games is None:
    num_games = NumGames(num=0)
    our_game_num = 0
  else:
    our_game_num = num_games.num + 1
    num_games.num = our_game_num
  num_games.put()
  return our_game_num


def render(values, template_name):
  """JINJA rendering helper method.

  Args:
    values: (dict) The values to pass to the jinja template.
    template_name: (str) The filename of the template to load.

  Returns:
    str: The rendered html page.
  """
  values['logout'] = users.create_logout_url('/')
  template = jinja_environment.get_template(template_name)
  return template.render(values)


jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/single', AIGamePage),
    ('/multi', MultiLobbyPage),
    ('/multigame', MultiGamePage),
    ('/rankings', RankingPage),
    ('/move', MoveRequest),
    ('/resign', ResignRequest),
    ('/joingame', JoinGameRequest),
    ('/startgame', StartMPGameRequest)
], debug=True)

