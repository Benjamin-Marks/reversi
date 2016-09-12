gameID = -1;
playerID = -1;
ourTurn = true;


/**
 * Starts a singleplayer game.
 *
 * Calls start to set up global variables, does additional singleplayer updates.
 *
 * @param {int} game: The game's id.
 * @param {string} player: The player's email.
 * @param {Array} board: The array representation of the intial board state.
 */
startSingle = function(game, player, board) {
  start(game, player);
  updateBoard(board);
  document.getElementById('whitescore').innerHTML = "White Score: 2";
  document.getElementById('blackscore').innerHTML = "Black Score: 2";
  var message = document.getElementById('gamenotice');
  message.innerHTML = 'Game Started!';

};

/**
 * Stores gameID, playerIDi, sets onunload to resign from game.
 *
 * @param {int} game: The game's id.
 * @param {string} player: The player's email.
 */
start = function(game, player) {
  gameID = game;
  playerID = player;
  window.onunload = window.onbeforeunload = resign;
};

/**
 * Processes resign request.
 */
resign = function() {
  $.ajax({
    type: "POST",
    url: "/resign",
    data: {gameID: gameID, playerID: playerID},
    success: function(data) {
      var message = document.getElementById('gamenotice');
      message.innerHTML = data['message'];
    }
  });
};

/**
 * Wrapper for receiving channel messages. Parses response.
 *
 * @param {Object} m: The channel's JSON message.
 */
MPMessage = function(m) {
  onMessage(JSON.parse(m.data));
};

/**
 * Processes and displays game updates from server.
 *
 * If there's an error, we just update the message. Otherwise update the board.
 * @param {Object} data: The response data from the server.
 */
onMessage = function(data) {
    if (data['error'] != true) {
        updateBoard(data['board']);
        document.getElementById('whitescore').innerHTML = "White Score: " +
                                                          data['whitescore'];
        document.getElementById('blackscore').innerHTML = "Black Score: " +
                                                          data['blackscore'];
        if (data['ourmove']) {
            document.getElementById('ourmove').innerHTML = "Your Move: " +
                                                           data['ourmove'];
        }
        if (data['theirmove']) {
            document.getElementById('theirmove').innerHTML = "Opponent Move: " +
                                                             data['theirmove'];
        }
        if (data['opponent']) {
            document.getElementById('playvs').innerHTML = "Playing vs: " +
                                                          data['opponent'];
        }
    }
    ourTurn = data['ourTurn'];
    var message = document.getElementById('gamenotice');
    message.innerHTML = data['message'];
};


/**
 * If Player2, tells server to start game.
 *
 * Parses URL string to check for game param. IF it exists, we're player 2.
 */
onOpened = function() {
  var game = location.search.split("game=")[1];
  if (game) {
    $.ajax({
      type: "POST",
      url: "/startgame",
      data: {gameID: gameID, playerID: playerID}
    });
  }
};

/**
 * In multiplayer games, creates the channel for updates from the server.
 *
 * @param {string} token: The unique server token for our channel.
 */
getChannel = function(token) {
  var channel = new goog.appengine.Channel(token);
  var handler = {
    'onopen': onOpened,
    'onmessage': MPMessage,
    'onerror': function() {},
    'onclose': function() {}
  };
  var socket = channel.open(handler);
  ourTurn = false;
};


/**
 * Process move request from player. If it's our turn, send it to server.
 *
 * @param {int} row: The row clicked.
 * @param {int} column: The column clicked.
 */
move = function(row, column) {
  if (ourTurn) {
    ourTurn = false;
    $.ajax({
      type: "POST",
      url: "/move",
      data: {
              row: row,
              column: column,
              gameID: gameID,
              playerID: playerID,
            },
      success: onMessage
    });
  }
};


/**
 * Updates the board on screen with the new board from the server.
 *
 * @param {Array} board: The new board.
 */
updateBoard = function(board) {
  var board = JSON.parse(board);
  for (var r = 0; r < board.length; r++) {
    for (var c = 0; c < board.length; c++) {
      var cell = document.getElementById('r'+ r + 'c' + c);
      if (board[r][c] == 0) { //White
        cell.innerHTML = '<img src="/img/white.png"></img>';
      } else if (board[r][c] == 1) { //Black
        cell.innerHTML = '<img src="/img/black.png"></img>';
      } else { //Blank
        cell.innerHTML = "";
      }
    }
  }
};


/**
 * Process request to join lobby. Called on lobby screen.
 *
 * @param {int} lobby: The lobby we want to join.
 */
joingame = function(lobby) {
  $.ajax({
    type: "POST",
    url: "/joingame",
    data: {lobby:lobby},
    success: function(data) {
      data = JSON.parse(data);
      if (data['owngame'] == true) {
        alert("You can't join your own lobby");
      } else  if (data['gone'] == true) {
        alert("This lobby no longer exists");
      } else{
        window.location.href =  "/multigame?game=" + lobby;
      }
    }
  });
};
