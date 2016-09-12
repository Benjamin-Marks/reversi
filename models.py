"""Modules used in reversi app.

Representations of user Accounts, games, lobbies for the ndb
"""


from google.appengine.ext import ndb


class NumGames(ndb.Model):
  """Hack to create autoincrement value.

  TODO(benjaminmarks): legit way to do this?
  """
  num = ndb.IntegerProperty()


class Lobby(ndb.Model):
  """A player waiting for a multiplayer game.

  Note: We duplicate player's elo to prevent additional ndb transactions
  """
  player = ndb.StringProperty()
  elo = ndb.IntegerProperty()
  game = ndb.IntegerProperty()


class Game(ndb.Model):
  """A game of reversi."""
  id = ndb.IntegerProperty()
  size = ndb.IntegerProperty()
  moves = ndb.StringProperty()
  turn = ndb.IntegerProperty()
  board = ndb.StringProperty()
  player1 = ndb.StringProperty()
  singleplayer = ndb.BooleanProperty()
  player2 = ndb.StringProperty()
  winner = ndb.IntegerProperty()
  done = ndb.BooleanProperty(default=False)


class Account(ndb.Model):
  """A user's account.

  ID is the user's email
  """
  id = ndb.StringProperty()
  photo = ndb.BlobProperty()
  games = ndb.IntegerProperty()
  wins = ndb.IntegerProperty()
  draws = ndb.IntegerProperty()
  losses = ndb.IntegerProperty()
  elo = ndb.IntegerProperty()

