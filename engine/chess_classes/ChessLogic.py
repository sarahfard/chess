# -*- coding: utf-8 -*-

from engine.chess_classes import ChessBoard, ChessPiece
from utils import utils
from engine.models import *


class ChessGame:
    def __init__(self, user_id, game_id=None):
        self.board = ChessBoard.Board(user_id=user_id)

        if game_id:
            self.game_id = game_id
            self.load_game(game_id)
        else:
            self.game_data = self.initialize()

    def initialize(self, give_hand_to='white'):
        self.game_data = GamePersistentData.objects.filter(id=self.game_id).first()
        if not self.game_data:
            self.game_data = GamePersistentData()
            self.game_id = self.game_data.id

        self._initialize_castle_data()
        self.game_data.set_data('token/step/name', 'waitCellSource')
        self.game_data.set_data('token/step/side', give_hand_to)

        return self.game_data

    def load_game(self, game_id):
        self.game_id = game_id
        self.game_data = GamePersistentData.objects.filter(id=self.game_id).first()
        self.board.load_grid(self.game_data)
        return True

    def create_game(self):
        pass

    def delete_game(self):
        pass


    def join_game(self, user):
        pass

    def select_colorset(self, user, colorset):
        pass

    def select_side(self, user, side):
        pass


    def move_piece_select_source(self, user, x, y):

        piece = self.board.get_piece_at(y, x)
        if not self._check_color_authorization(piece):
            return False


        current_waited_state = self.game_data.get_data('token/step/name')
        if current_waited_state != 'waitCellSource':
            return False


        data = {
            'line': y,
            'column': x
        }
        self.game_data.set_data('token/step/data', '.')
        self.game_data.set_data('token/step/data/sourceCell', data)
        self.game_data.set_data('token/step/name', 'waitCellTarget')
        return True

    def move_piece_select_target(self, user, x, y):


        current_waited_state = self.game_data.get_data('token/step/name')
        if current_waited_state != 'waitCellTarget':
            return False


        source_line = self.game_data.get_data('token/step/data/sourceCell/line')
        source_column = self.game_data.get_data('token/step/data/sourceCell/column')
        source_piece = self.board.get_piece_at(source_line, source_column)

        if not self._check_color_authorization(source_piece):
            return False


        backup_before_move = self._backup_context_data_before_move()


        if not source_piece.is_move_valid(source_column, source_line, x, y):
            self.game_data.set_data('token/step/data', '.')
            self.game_data.set_data('token/step/name', 'waitCellSource')
            return False


        enpassant_set = None
        if source_piece.role.name == 'P':
            enpassant_set = self._prepare_enpassant_vulnerability(source_column, source_line, source_piece, x, y)
            if enpassant_set:
                pass

        target_piece = self.game_data.get_data('board/{line}/{column}'.format(line=y, column=x))
        ep = False
        enpassed_piece = None
        enpassant_data = self.game_data.get_data('token/step/enpassant')
        if source_piece.role.name == 'P' and enpassant_data:
            src_x = ord(x) - 97
            src_y = int(y)
            if (src_x == enpassant_data['x']) and (src_y == enpassant_data['y']):
                ep = True
                enpassed_x = x
                if source_piece.side.name == 'white':
                    enpassed_y = str(int(y)-1)
                else:
                    enpassed_y = str(int(y) + 1)
                enpassed_piece = self.game_data.get_data('board/{line}/{column}'.format(line=enpassed_y, column=enpassed_x))
                self.game_data.set_data('token/step/data/eaten', enpassed_piece)
                self.game_data.set_data('board/{line}/{column}'.format(line=enpassed_y, column=x), '-')

        rook = False
        if source_piece.role.name == 'K':
            check_castle_case = source_piece.detect_castle_call(source_column, source_line, x, y)
            if check_castle_case:
                source_piece.move_rook(self.game_data, check_castle_case)
                if check_castle_case == 'r1':
                    rook = 'O-O'
                else:
                    rook = 'O-O-O'

        self._clean_castle_data(source_piece)

        self.game_data.set_data('board/{line}/{column}'.format(line=y, column=x), source_piece)

        if target_piece != '-':
            self.game_data.set_data('token/step/data/eaten', target_piece)

        self.game_data.set_data('board/{line}/{column}'.format(line=source_line, column=source_column), '-')

        if not enpassant_set:
            self.board.game_data.pop_data('token/step', 'enpassant')
        data = {
            'line': y,
            'column': x
        }
        self.game_data.set_data('token/step/data/targetCell', data)
        self.board.set_piece_at(y, x, source_piece)
        if self.board.is_kingchecked(source_piece.side.name):
            self._restore_context_data_from_backup(backup_before_move)
            self.game_data.set_data('token/step/data/impossible_move', 'king_checked')
            return False
        self.game_data.set_data('token/step/data/impossible_move', '')

        promo = self._check_promotion(source_piece, data)

        if promo:
            self.game_data.set_data('token/step/name', 'promote')
        else:
            move_data = {
                'source_piece': source_piece,
                'src_x': source_column,
                'src_y': source_line,
                'dest_x': x,
                'dest_y': y,
                'target_piece': target_piece,
                'rook': rook,
                'ep': ep,
                'promo': None,
                'check': None,
            }
            if ep:
                move_data['target_piece'] = enpassed_piece
            else:
                move_data['target_piece'] = target_piece

            self._finalize_turn(move_data)

        return True

    def promote_piece(self, user, role_name):
        current_waited_state = self.game_data.get_data('token/step/name')
        if current_waited_state != 'promote':
            return False

        target_line = self.game_data.get_data('token/step/data/targetCell/line')
        target_column = self.game_data.get_data('token/step/data/targetCell/column')

        side = self.game_data.get_data('token/step/side')
        target_piece_data = {
            "s": side[0:1],
            "r": role_name,
            "n": "%s_promo" % role_name
        }
        self.game_data.set_data('board/{line}/{column}'.format(line=target_line, column=target_column), target_piece_data)

        source_line = self.game_data.get_data('token/step/data/sourceCell/line')
        source_column = self.game_data.get_data('token/step/data/sourceCell/column')
        source_piece = self.board.get_piece_at(target_line, target_column)
        move_data = {
            'source_piece': source_piece,
            'src_x': source_column,
            'src_y': source_line,
            'target_piece': target_piece_data,
            'dest_x': target_column,
            'dest_y': target_line,
            'promo': target_piece_data,
            'rook': None,
            'ep': None,
            'check': None,
        }

        self._finalize_turn(move_data)
        return True

    """ end of game """

    def reset_round(self):
        history = self.game_data.get_data('history')
        game_options = self.game_data.get_data('game_options')
        participants = self.game_data.get_data('participants')
        rounds = self.game_data.get_data('rounds')
        self.game_data.set_data(None, {})
        self.game_data.set_data('history', history)
        self.game_data.set_data('game_options', game_options)
        self.game_data.set_data('participants', participants)
        self.game_data.set_data('rounds', rounds)
        self.initialize()

    def reset_game(self):
        game_options = self.game_data.get_data('game_options')
        participants = self.game_data.get_data('participants')
        self.game_data.set_data(None, {})
        self.game_data.set_data('game_options', game_options)
        self.game_data.set_data('participants', participants)
        self.initialize()

    def accept_checkmate(self):
        self.game_data.set_data('token/step/name', 'checkmate')
        self.game_data.set_data('token/result', 'checkmate')
        self._save_game('checkmate')

        if self._winning_games_gap_reached():
            pass
        else:
            current_round_number = 1
            rounds = self.game_data.get_data('rounds')
            if rounds:
                current_round_number += len(rounds)
            if current_round_number % 2 == 0:
                next_side = 'black'
            else:
                next_side = 'white'
            self.initialize(give_hand_to=next_side)

    def declare_withdraw(self):
        self.game_data.set_data('token/step/name', 'withdraw')
        self.game_data.set_data('token/result', 'checkmate')

        self._save_game('withdraw')
        if self._winning_games_gap_reached():
            pass
        else:
            next_side = 'black' if self.game_data.get_data('token/step/side') == 'white' else 'white'
            self.initialize(give_hand_to=next_side)

    def declare_draw(self):
        pass

    def accept_revanche(self, user):
        pass

    def accept_belle(self, user):
        pass

    def quit_game(self, user):
        pass

    """ private mechanics tools """

    def _initialize_castle_data(self):
        rookable_data = ['r1', 'r2']
        self.game_data.set_data('token/step/castle/white', rookable_data)
        self.game_data.set_data('token/step/castle/black', rookable_data)

    def _winning_games_gap_reached(self):
        winning_games = int(self.game_data.get_data('game_options/winning_games'))
        rounds = self.game_data.get_data('rounds')
        number_of_white_wins = 0
        number_of_black_wins = 0
        for round_k, round in rounds.items():
            if round['winner'] == 'white':
                number_of_white_wins += 1
            elif round['winner'] == 'black':
                number_of_black_wins += 1

        if (number_of_white_wins >= winning_games) or (number_of_black_wins >= winning_games):
            return True
        return False

    def _save_game_result(self, result):
        side = self.game_data.get_data('token/step/side')
        if side == 'white':
            winner_side = 'black'
        else:
            winner_side = 'white'
        rounds = self.game_data.get_data('rounds')
        round_result = dict()
        round_result['result'] = result
        round_result['winner'] = winner_side
        if rounds:
            new_round_path = 'rounds/%d' % (len(rounds) + 1)
        else:
            new_round_path = 'rounds/1'
        self.game_data.set_data(new_round_path, round_result)

        if self._winning_games_gap_reached():
            self.game_data.set_data('result/winner', winner_side)
            round_list = ''
            rounds = self.game_data.get_data('rounds')
            round_count = 1
            while round_count <= len(rounds):
                round_path = 'rounds/%d/winner' % round_count
                round_winner = self.game_data.get_data(round_path)
                if round_winner == 'white':
                    round_list += 'w'
                elif round_winner == 'black':
                    round_list += 'b'
                else:
                    pass
                round_count += 1
            self.game_data.set_data('result/round_list', round_list)

            ranked_game = self.game_data.get_data('game_options/ranked')
            if ranked_game:
                if winner_side == 'white':
                    winner_user = User.objects.filter(id=self.game_data.get_data('participants/white/1')).first()
                    loser_user = User.objects.filter(id=self.game_data.get_data('participants/black/1')).first()
                else:
                    winner_user = User.objects.filter(id=self.game_data.get_data('participants/black/1')).first()
                    loser_user = User.objects.filter(id=self.game_data.get_data('participants/white/1')).first()
                winner_ranking = UserRanking.objects.get_or_create(user=winner_user)[0]
                loser_ranking = UserRanking.objects.get_or_create(user=loser_user)[0]
                winner_old_elo = int(winner_ranking.get_elo('chess'))
                if not winner_old_elo:
                    winner_old_elo = 0
                loser_old_elo = int(loser_ranking.get_elo('chess'))
                if not loser_old_elo:
                    loser_old_elo = 0
                d = loser_old_elo - winner_old_elo
                loser_ranking.update_elo('chess', w=0, d=d, game_id=self.game_data.id,
                                         opponent_id=winner_user.id, opponent_elo=winner_old_elo)
                winner_ranking.update_elo('chess', w=1, d=d, game_id=self.game_data.id,
                                          opponent_id=loser_user.id, opponent_elo=loser_old_elo)

    def _save_game(self, result):
        history = self.game_data.get_data('history')
        game_options = self.game_data.get_data('game_options')
        participants = self.game_data.get_data('participants')
        saved_games = self.game_data.get_data('saved_games')

        self._save_game_result(result)
        rounds = self.game_data.get_data('rounds')
        results = self.game_data.get_data('result')

        history_game = dict()
        history_game['token'] = self.game_data.get_data('token')
        history_game['board'] = self.game_data.get_data('board')
        if history:
            new_game_key = 'game_%02d' % (len(history) + 1)
        else:
            history = dict()
            new_game_key = 'game_01'
        history[new_game_key] = history_game

        self.game_data.set_data(None, {})
        self.game_data.set_data('history', history)
        self.game_data.set_data('game_options', game_options)
        self.game_data.set_data('participants', participants)
        self.game_data.set_data('rounds', rounds)
        self.game_data.set_data('result', results)
        self.game_data.set_data('saved_games', saved_games)

    def _check_promotion(self, piece, data):
        if piece.role.name == 'P':
            if self.game_data.get_data('token/step/side') == 'white':
                promotion_line = 8
            else:
                promotion_line = 1
            if int(data['line']) == int(promotion_line):
                return True
        return False

    def _backup_context_data_before_move(self):
        backup = dict()
        backup['obj_board'] = self.board
        backup['obj_game_data'] = self.game_data
        backup['sql_game_data'] = self.game_data.get_data('')
        return backup

    def _restore_context_data_from_backup(self, backup):
        self.board = backup['obj_board']
        self.game_data = backup['obj_game_data']
        self.game_data.set_data('', backup['sql_game_data'])

    def _prepare_enpassant_vulnerability(self, source_x, source_y, source_piece, target_x, target_y):
        src_x = ord(source_x) - 97
        dest_x = ord(target_x) - 97
        src_y = int(source_y)
        dest_y = int(target_y)
        if source_piece.side.name == 'white':
            start_axis = 2
            enpassant_cell = {'x': dest_x, 'y': int(dest_y) - 1}
        else:
            start_axis = 7
            enpassant_cell = {'x': dest_x, 'y': int(dest_y) + 1}

        if src_y != start_axis:
            return False

        if abs(dest_y - src_y) == 2:
            self.game_data.set_data('token/step/enpassant', enpassant_cell)
            return enpassant_cell
        return False

    def _if_eaten_piece_was(self, piece_role):
        eaten_piece = self.game_data.get_data('token/step/data/eaten')
        if eaten_piece:
            if eaten_piece['r'] == piece_role:
                return True
        return False

    def _check_king_troubles(self, side_name):
        if self._if_eaten_piece_was('K'):
            return True, 'checkmate'

        king = self.board.get_piece_from_role('K', side_name)
        if not king:
            return False, None
        king_c, king_l = self.board.get_piece_coords_from_role('K', side_name)
        if king.is_in_danger(king_c, king_l):
            return True, 'check'
        return False, None

    def _finalize_turn(self, move_data):
        side = self.game_data.get_data('token/step/side')

        self.board.load_grid(self.game_data)

        ennemy_side = 'black' if side == 'white' else 'white'
        king_checks = self._check_king_troubles(ennemy_side)

        if king_checks[1] == 'checkmate':
            move_data['check'] = 'checkmate'
            self.game_data.set_data('token/step/name', 'checkmate')
        else:
            if king_checks[1] == 'check':
                move_data['check'] = 'check'
            self.game_data.set_data('token/step/name', 'waitCellSource')

        if side == 'white':
            self.game_data.set_data('token/step/side', 'black')
        else:
            self.game_data.set_data('token/step/side', 'white')

        self.game_data.add_log(move_data)


    def _check_color_authorization(self, piece):
        playable_color = self.game_data.get_data('token/step/side')
        if piece.side.name != playable_color:
            return False
        return True

    def _clean_castle_data(self, source_piece):
        if source_piece.role.name == 'K':
            self.game_data.set_data('token/step/castle/%s' % source_piece.side.name, '-')
        elif source_piece.role.name == 'R':
            rookables = self.game_data.get_data('token/step/castle/%s' % source_piece.side.name)
            if rookables:
                if source_piece.name in rookables:
                    if len(rookables) == 1:
                        self.game_data.set_data('token/step/castle/%s' % source_piece.side.name, '-')
                    else:
                        rookables.remove(source_piece.name)
                        self.game_data.set_data('token/step/castle/%s' % source_piece.side.name, rookables)
