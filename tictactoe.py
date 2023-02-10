class TicTacToe:
    N = 0
    O = 1
    X = 2
    WIN_O = 11
    WIN_X = 12

    def __init__(self, game=None):
        self.current_turn = self.X
        if game is None:
            self.current_board = [
                [self.N, self.N, self.N],
                [self.N, self.N, self.N],
                [self.N, self.N, self.N]
            ]
        else:
            self._load_from_list(game)

    def _load_from_list(self, game_list):
        self.current_turn = self.X
        self.current_board = []

        for item in game_list:
            item = int(item)
            if self.current_board == [] or len(self.current_board[-1]) == 3:
                self.current_board.append([])

            self.current_board[-1].append(item)
            if item != self.N:
                self._swap_current_turn()

    def get_game_list(self):
        game_list = []
        for row in self.current_board:
            for item in row:
                game_list.append(item)

        return game_list

    def take_turn(self, player, row, col):
        if player != self.current_turn:
            raise TicTacToeWrongPlayerError

        if not (0 <= row <= 2 and 0 <= col <= 2):
            raise TicTacToeInvalidMoveError

        if self.current_board[row][col] != self.N:
            raise TicTacToeInvalidMoveError

        
        self.current_board[row][col] = player
        self._swap_current_turn()

    def check_game_over(self):
        o_won = [self.O, self.O, self.O]
        x_won = [self.X, self.X, self.X]

        for row_i in range(3):
            if self.current_board[row_i] == o_won:
                self.current_board[row_i] = [self.WIN_O, self.WIN_O, self.WIN_O]
                return True
            elif self.current_board[row_i] == x_won:
                self.current_board[row_i] = [self.WIN_X, self.WIN_X, self.WIN_X]
                return True

        for col_i in range(3):
            col_list = [row[col_i] for row in self.current_board]
            if col_list == o_won:
                for row_i in range(3):
                    self.current_board[row_i][col_i] = self.WIN_O
                return True
            elif col_list == x_won:
                for row_i in range(3):
                    self.current_board[row_i][col_i] = self.WIN_X
                return True
        
        first_diagonal = [self.current_board[i][i] for i in range(3)]
        if first_diagonal == o_won:
            for i in range(3):
                self.current_board[i][i] = self.WIN_O
            return True
        elif first_diagonal == x_won:
            for i in range(3):
                self.current_board[i][i] = self.WIN_X
            return True

        second_diagonal = [self.current_board[i][2 - i] for i in range(3)]
        if second_diagonal == o_won:
            for i in range(3):
                self.current_board[i][2 - i] = self.WIN_O
            return True
        elif second_diagonal == x_won:
            for i in range(3):
                self.current_board[i][2 - i] = self.WIN_X
            return True
        
        return False

    def board_full(self):
        for row in self.current_board:
            for cell in row:
                if int(cell) == self.N:
                    return False

        return True

    def __str__(self):
        str_lookup = {
            self.N: '   ',
            self.X: ' X ',
            self.O: ' O ',
            self.WIN_O: '*O*',
            self.WIN_X: '*X*'
        }

        col_sep = '|'
        row_sep = '\n-----------\n'

        return \
        f'{str_lookup[self.current_board[0][0]]}{col_sep}{str_lookup[self.current_board[0][1]]}{col_sep}{str_lookup[self.current_board[0][2]]}{row_sep}' + \
        f'{str_lookup[self.current_board[1][0]]}{col_sep}{str_lookup[self.current_board[1][1]]}{col_sep}{str_lookup[self.current_board[1][2]]}{row_sep}' + \
        f'{str_lookup[self.current_board[2][0]]}{col_sep}{str_lookup[self.current_board[2][1]]}{col_sep}{str_lookup[self.current_board[2][2]]}'

    def _swap_current_turn(self):
        self.current_turn = self.O if self.current_turn == self.X else self.X




class TicTacToeException(Exception):
    pass

class TicTacToeWrongPlayerError(TicTacToeException):
    pass

class TicTacToeInvalidMoveError(TicTacToeException):
    pass