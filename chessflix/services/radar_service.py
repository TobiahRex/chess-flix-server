from datetime import datetime
import numpy as np
import json
import io
import chess
import chess.pgn
import statistics
from tqdm import tqdm
import matplotlib.pyplot as plt

from chessflix.services.stockfish_service import StockfishService
from chessflix.services.chess_dot_com_service import ChessDotComService


class RadarService:
    def __init__(self, *args, **kwargs):
        self.stockfish_service = kwargs.get('stockfish_service')
        self.chessdotcom_service = kwargs.get('chessdotcom_service')
        self.features = [
            'space',
            'piece_mobility',
            'pawn_structure_health',
            'king_safety',
            'attacked_pieces',
            'tactical_opps',
            'material_balance',
            'central_control',
            'kingside_attack',
            'queenside_attack',
            'strong_threats',
            'forks',
            'checks_captures_threats'
        ]
        self.trained_stats = kwargs.get('trained_stats', {})
        self.normalize_scores = kwargs.get('normalize_scores', True)

    @staticmethod
    def build(stockfish_service, stats_file, normalize_scores=True):
        f = open(stats_file, 'r')
        trained_stats = json.load(f)
        f.close()
        return RadarService(
            normalize_scores=normalize_scores,
            trained_stats=trained_stats,
            stockfish_service=stockfish_service,
            chessdotcom_service=ChessDotComService.build(),
        )

    def get_features_by_fen(self, fen):
        features = {
            'space': self.calculate_space(fen),
            'piece_mobility': self.calculate_piece_mobility(fen),
            'pawn_structure_health': self.calculate_pawn_structure_health(fen),
            'king_safety': self.calculate_king_safety(fen),
            'attacked_pieces': self.calculate_attacked_pieces(fen),
            'tactical_opps': self.calculate_tactical_opps(fen),
            'material_balance': self.calculate_material_balance(fen),
            'central_control': self.calculate_central_control(fen),
            'kingside_attack': self.calculate_kingside_attack(fen),
            'queenside_attack': self.calculate_queenside_attack(fen),
            'strong_threats': self.calculate_strong_threats(fen),
            'forks': self.calculate_forks(fen),
            'checks_captures_threats': self.calculate_checks_captures_threats(fen),
        }
        return features

    def calculate_piece_mobility(self, fen):
        board = chess.Board(fen)
        weights = {
            chess.PAWN: 1,
            chess.KNIGHT: 3,
            chess.BISHOP: 3,
            chess.ROOK: 5,
            chess.QUEEN: 9,
            chess.KING: 0  # Ignore the king's mobility for simplicity
        }
        max_potential = {
            chess.PAWN: 3,  # Maximum potential for pawn is 1 if not blocked
            chess.KNIGHT: 8,  # Maximum potential for knight is 8
            # Maximum potential for bishop is 13 (diagonal squares)
            chess.BISHOP: 13,
            # Maximum potential for rook is 14 (vertical and horizontal squares)
            chess.ROOK: 14,
            # Maximum potential for queen is 27 (vertical, horizontal, and diagonal squares)
            chess.QUEEN: 27
        }
        white_mobility = 0
        black_mobility = 0
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece is not None:
                mobility = len(list(board.attacks(square)))
                weight = weights.get(piece.piece_type, 0)
                max_potential_squares = max_potential.get(piece.piece_type, 0)
                if piece.color == chess.WHITE:
                    white_mobility += mobility * weight / \
                        max_potential_squares if max_potential_squares > 0 else 0
                else:
                    black_mobility += mobility * weight / \
                        max_potential_squares if max_potential_squares > 0 else 0
        # Scale the mobility scores to the range of 0 to 10
        result = self.calculate_final_score(
            {
                'attribute': 'piece_mobility',
                'white_score': round(white_mobility, 6),
                'black_score': round(black_mobility, 6),
            },
        )
        return result

    def calculate_pawn_structure_health(self, fen):
        board = chess.Board(fen)
        white_pawn_score = 0
        black_pawn_score = 0
        white_pawns = [square for square in chess.SQUARES if board.piece_at(
            square) == chess.Piece(chess.PAWN, chess.WHITE)]
        black_pawns = [square for square in chess.SQUARES if board.piece_at(
            square) == chess.Piece(chess.PAWN, chess.BLACK)]
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece is not None and piece.piece_type == chess.PAWN:
                pawn_score = 10
                if piece.color == chess.WHITE:
                    # Check if the pawn is isolated
                    file_idx = chess.square_file(square)
                    if not any(
                        board.piece_at(chess.square(file_idx, r)) == chess.Piece(
                            chess.PAWN, chess.WHITE)
                        for r in range(8)
                        if r != chess.square_rank(square) and chess.square(file_idx, r) < 64
                    ):
                        pawn_score -= 2
                    # Check if the pawn is backward
                    if chess.square_rank(square) < 7 and not any(
                        board.piece_at(chess.square(
                            file_idx + d, chess.square_rank(square) + 1)) == chess.Piece(chess.PAWN, chess.WHITE)
                        for d in (-1, 0, 1)
                        if chess.square(file_idx + d, chess.square_rank(square) + 1) < 64
                    ):
                        pawn_score -= 1
                    # Check if the pawn is doubled
                    if len(white_pawns) > 1 and any(
                        chess.square_file(p) == file_idx and p != square
                        for p in white_pawns
                        if p < 64
                    ):
                        pawn_score -= 1
                    white_pawn_score += pawn_score
                else:
                    file_idx = chess.square_file(square)
                    if not any(
                        board.piece_at(chess.square(file_idx, r)) == chess.Piece(
                            chess.PAWN, chess.BLACK)
                        for r in range(8)
                        if r != chess.square_rank(square) and chess.square(file_idx, r) < 64
                    ):
                        pawn_score -= 2
                    if chess.square_rank(square) > 0 and not any(
                        board.piece_at(chess.square(
                            file_idx + d, chess.square_rank(square) - 1)) == chess.Piece(chess.PAWN, chess.BLACK)
                        for d in (-1, 0, 1)
                        if chess.square(file_idx + d, chess.square_rank(square) - 1) < 64
                    ):
                        pawn_score -= 1
                    if len(black_pawns) > 1 and any(
                        chess.square_file(p) == file_idx and p != square
                        for p in black_pawns
                        if p < 64
                    ):
                        pawn_score -= 1
                    black_pawn_score += pawn_score
        # Scale the scores to the range of 0 to 10
        return self.calculate_final_score(
            {
                'attribute': 'pawn_structure_health',
                'white_score': round(white_pawn_score, 4),
                'black_score': round(black_pawn_score, 4)
            },
        )

    def calculate_king_safety(self, fen):
        board = chess.Board(fen)
        white_kingside_squares = [
            chess.E1, chess.G1, chess.F1, chess.H1, chess.E2, chess.G2, chess.F2, chess.H2]
        black_kingside_squares = [
            chess.E8, chess.G8, chess.F8, chess.H8, chess.E7, chess.G7, chess.F7, chess.H7]
        white_queenside_squares = [
            chess.D1, chess.C1, chess.B1, chess.A1, chess.D2, chess.C2, chess.B2, chess.A2]
        black_queenside_squares = [
            chess.D8, chess.C8, chess.B8, chess.A8, chess.D7, chess.C7, chess.B7, chess.A7]
        white_attack = 0
        black_attack = 0
        black_king_sqr = board.king(chess.BLACK)
        white_king_sqr = board.king(chess.WHITE)
        ks_attack = self.calculate_kingside_attack(fen)
        qs_attack = self.calculate_queenside_attack(fen)
        if black_king_sqr in black_kingside_squares:
            white_attack += ks_attack.get('white_score')
        elif black_king_sqr in black_queenside_squares:
            white_attack += qs_attack.get('white_score')
        if white_king_sqr in white_kingside_squares:
            black_attack += ks_attack.get('black_score')
        elif white_king_sqr in white_queenside_squares:
            black_attack += qs_attack.get('black_score')
        return self.calculate_final_score({
            'attribute': 'king_safety',
            'white_score': black_attack,
            'black_score': white_attack
        })

    def calculate_attacked_pieces(self, fen):
        """Calculates the number of attacked pieces for each player. An attacked piece is
        defined as a piece that is being attacked by an opponent's piece. For example, if
        a white knight is attacking a black queen, then that is an attacked piece.

        """
        def get_piece_weight(piece_type):
            if piece_type == chess.QUEEN:
                return 9
            elif piece_type == chess.ROOK:
                return 5
            elif piece_type == chess.BISHOP or piece_type == chess.KNIGHT:
                return 3
            elif piece_type == chess.PAWN:
                return 1
            else:
                return 0
        board = chess.Board(fen)
        white_attacked_pieces = 0
        black_attacked_pieces = 0
        for square in chess.SQUARES:
            attacker = board.piece_at(square)
            if not attacker:
                continue
            attack_sqrs = list(board.attacks(square))
            for i, attack_sqr in enumerate(attack_sqrs):
                attacked_piece = board.piece_at(attack_sqr)
                # if it's an empty square or the piece is the same color as the attacker, continue
                if not attacked_piece or attacked_piece.color == attacker.color:
                    continue
                else:
                    good_attack = False
                    attacker_weight = get_piece_weight(attacker.piece_type)
                    attacked_piece_weight = get_piece_weight(
                        attacked_piece.piece_type)
                    # if attacked_piece_weight >= attacker_weight it's a candidate capture
                    if attacked_piece_weight >= attacker_weight:
                        good_attack = True
                    # otherwise we need to check if the attacked piece is defended
                    else:
                        defender_sqrs = list(board.attackers(
                            not attacker.color, attack_sqr))
                        if not defender_sqrs:
                            good_attack = True
                        else:
                            for defender_sqr in defender_sqrs:
                                has_defender = board.piece_at(defender_sqr)
                                if has_defender:
                                    break  # the capture would loose material
                                else:
                                    good_attack = True
                    if good_attack:
                        if attacker.color == chess.WHITE:
                            white_attacked_pieces += attacked_piece_weight
                        else:
                            black_attacked_pieces += attacked_piece_weight
        return self.calculate_final_score(
            {
                'attribute': 'attacked_pieces',
                'white_score': white_attacked_pieces,
                'black_score': black_attacked_pieces
            },
        )

    def calculate_tactical_opps(self, fen):
        """Aggregates the attacking potential of both sides;
        - Central control
        - Kingside Attacks
        - Queenside Attacks
        - Threats: Checks, Captures, Threats
        - Threats: smaller weighted pieces attacking larger weighted pieces
        - Tactical opportunities (forks, skewers, pins, discovered attacks, etc.)

        Args:
            fen (string): Chess position fen
        """
        strong_threats = self.calculate_strong_threats(fen)
        tactical_opps = self.calculate_forks(fen)
        cct = self.calculate_checks_captures_threats(fen)
        # Aggregate the scores
        white_score = (
            strong_threats.get('white_score') +
            tactical_opps.get('white_score') +
            cct.get('white_score')
        ) / 3
        black_score = (
            strong_threats.get('black_score') +
            tactical_opps.get('black_score') +
            cct.get('black_score')
        ) / 3
        return self.calculate_final_score(
            {
                'attribute': 'tactical_opps',
                'white_score': white_score,
                'black_score': black_score
            },
        )

    def calculate_central_control(self, fen):
        board = chess.Board(fen)
        # Define the material values of the pieces
        weights = {
            chess.PAWN: 1,
            chess.KNIGHT: 3,
            chess.BISHOP: 3,
            chess.ROOK: 5,
            chess.QUEEN: 9
        }
        # Define the central squares
        central_squares = [chess.E4, chess.D4, chess.E5, chess.D5]
        # Initialize counters for central control
        white_control = 0
        black_control = 0
        max_control = 0
        # Iterate over the central squares
        for square in central_squares:
            # Check if the square is attacked by White
            white_attackers_sqrs = list(board.attackers(chess.WHITE, square))
            has_defender = bool(board.attackers(chess.BLACK, square))
            for attacker_sqr in white_attackers_sqrs:
                piece_weight = weights.get(
                    board.piece_at(attacker_sqr).piece_type, 0)
                if has_defender:
                    white_control += piece_weight / 2
                else:
                    white_control += piece_weight
                max_control += piece_weight
            # Check if the square is attacked by Black
            black_attackers = list(board.attackers(chess.BLACK, square))
            has_defender = bool(board.attackers(chess.WHITE, square))
            for attacker_sqr in black_attackers:
                piece_weight = weights.get(
                    board.piece_at(attacker_sqr).piece_type, 0)
                if has_defender:
                    black_control += piece_weight / 2
                else:
                    black_control += piece_weight
                max_control += piece_weight
        return self.calculate_final_score({
            'attribute': 'central_control',
            'white_score': white_control,
            'black_score': black_control
        })

    def calculate_kingside_attack(self, fen):
        board = chess.Board(fen)
        # Define the material values of the pieces
        weights = {
            chess.PAWN: 1,
            chess.KNIGHT: 3,
            chess.BISHOP: 3,
            chess.ROOK: 5,
            chess.QUEEN: 9
        }
        # Define the kingside squares
        white_kingside_squares = [
            chess.E1, chess.G1, chess.F1, chess.H1, chess.E2, chess.G2, chess.F2, chess.H2]
        black_kingside_squares = [
            chess.E8, chess.G8, chess.F8, chess.H8, chess.E7, chess.G7, chess.F7, chess.H7]
        # Initialize counters for kingside attacks
        white_attack = 0
        black_attack = 0
        max_attack = 0
        # Iterate over the kingside squares
        for square in white_kingside_squares:
            if board.is_attacked_by(chess.BLACK, square):
                for attacker_sqr in list(board.attackers(chess.BLACK, square)):
                    piece_weight = weights.get(
                        board.piece_at(attacker_sqr).piece_type, 0)
                    has_defender = bool(board.attackers(chess.WHITE, square))
                    if has_defender:
                        black_attack += piece_weight / 2
                    else:
                        black_attack += piece_weight
                    max_attack += piece_weight
        for square in black_kingside_squares:
            if board.is_attacked_by(chess.WHITE, square):
                for attacker_sqr in list(board.attackers(chess.WHITE, square)):
                    piece_weight = weights.get(
                        board.piece_at(attacker_sqr).piece_type, 0)
                    has_defender = bool(board.attackers(chess.BLACK, square))
                    if has_defender:
                        white_attack += piece_weight / 2
                    else:
                        white_attack += piece_weight
                    max_attack += piece_weight
        # Scale the attack scores to the range of 0 to 10
        return self.calculate_final_score({
            'attribute': 'kingside_attack',
            'white_score': white_attack,
            'black_score': black_attack
        })

    def calculate_queenside_attack(self, fen):
        board = chess.Board(fen)
        weights = {
            chess.PAWN: 1,
            chess.KNIGHT: 3,
            chess.BISHOP: 3,
            chess.ROOK: 5,
            chess.QUEEN: 9
        }
        white_queenside_squares = [
            chess.D1, chess.C1, chess.B1, chess.A1, chess.D2, chess.C2, chess.B2, chess.A2]
        black_queenside_squares = [
            chess.D8, chess.C8, chess.B8, chess.A8, chess.D7, chess.C7, chess.B7, chess.A7]
        white_attack = 0
        black_attack = 0
        max_attack = 0
        for square in black_queenside_squares:
            if board.is_attacked_by(chess.WHITE, square):
                for attacker_sqr in list(board.attackers(chess.WHITE, square)):
                    piece = board.piece_at(attacker_sqr)
                    piece_weight = weights.get(piece.piece_type, 0)
                    has_defender = bool(board.attackers(chess.BLACK, square))
                    if has_defender:
                        white_attack += piece_weight / 2
                    else:
                        white_attack += piece_weight
                    max_attack += piece_weight
        for square in white_queenside_squares:
            if board.is_attacked_by(chess.BLACK, square):
                for attacker_sqr in list(board.attackers(chess.BLACK, square)):
                    piece = board.piece_at(attacker_sqr)
                    piece_weight = weights.get(piece.piece_type, 0)
                    has_defender = bool(board.attackers(chess.WHITE, square))
                    if has_defender:
                        black_attack += piece_weight / 2
                    else:
                        black_attack += piece_weight
                    max_attack += piece_weight
        return self.calculate_final_score({
            'attribute': 'queenside_attack',
            'white_score': white_attack,
            'black_score': black_attack
        })

    def calculate_checks_captures_threats(self, fen):
        board = chess.Board(fen)
        weights = {
            chess.PAWN: 1,
            chess.KNIGHT: 3,
            chess.BISHOP: 3,
            chess.ROOK: 5,
            chess.QUEEN: 9
        }
        # Initialize counters for checks, captures, and threats
        white_checks = 0
        white_captures = 0
        white_threats = 0
        black_checks = 0
        black_captures = 0
        black_threats = 0
        # Iterate over all squares on the board
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            # Check if the square is occupied by a piece
            if piece is not None:
                attacks = board.attacks(square)
                attacked_weight = weights.get(piece.piece_type, 0)
                # Check if the piece is checking the opponent's king
                if piece.color == chess.WHITE and piece.piece_type != chess.KING and board.is_check():
                    white_checks += attacked_weight
                elif piece.color == chess.BLACK and piece.piece_type != chess.KING and board.is_check():
                    black_checks += attacked_weight
                # Check if the piece is capturing an opponent's piece
                if piece.color == chess.WHITE and attacks and [board.piece_at(a).color for a in attacks if board.piece_at(a)].count(chess.BLACK):
                    white_captures += attacked_weight
                elif piece.color == chess.BLACK and attacks and [board.piece_at(a).color for a in attacks if board.piece_at(a)].count(chess.WHITE):
                    black_captures += attacked_weight
                # Check if the piece is threatening an opponent's piece
                if piece.color == chess.WHITE and attacks:
                    white_threats += attacked_weight
                elif piece.color == chess.BLACK and attacks:
                    black_threats += attacked_weight
        # Calculate the maximum count of checks, captures, and threats
        total_checks = (white_checks + black_checks)
        total_captures = (white_captures + black_captures)
        total_threats = (white_threats + black_threats)
        # Scale the scores to the range of 0 to 10
        white_checks_score = white_checks / \
            total_checks if total_checks > 0 else 0
        white_captures_score = white_captures / \
            total_captures if total_captures > 0 else 0
        white_threats_score = white_threats / \
            total_threats if total_threats > 0 else 0
        black_checks_score = black_checks / \
            total_checks if total_checks > 0 else 0
        black_captures_score = black_captures / \
            total_captures if total_captures > 0 else 0
        black_threats_score = black_threats / \
            total_threats if total_threats > 0 else 0
        checks = {
            'attribute': 'checks',
            'white_score': white_checks_score,
            'black_score': black_checks_score
        }
        captures = {
            'attribute': 'captures',
            'white_score': white_captures_score,
            'black_score': black_captures_score
        }
        threats = {
            'attribute': 'threats',
            'white_score': white_threats_score,
            'black_score': black_threats_score
        }
        return self.calculate_final_score({
            'attribute': 'checks_captures_threats',
            'white_score': sum(
                [checks.get('white_score'), captures.get('white_score'), threats.get('white_score')]),
            'black_score': sum(
                [checks.get('black_score'), captures.get('black_score'), threats.get('black_score')]),
        })

    def calculate_strong_threats(self, fen):
        """Calculates the number of strong threats for each player. A strong threat is
        defined as a piece that is attacking a piece of greater value. For example, if
        a white knight is attacking a black queen, then that is a strong threat. If a
        black pawn is attacking a white knight, then that is not a strong threat.
        """
        board = chess.Board(fen)
        # Define the weights of the pieces
        weights = {
            chess.PAWN: 1,
            chess.KNIGHT: 3,
            chess.BISHOP: 3,
            chess.ROOK: 5,
            chess.QUEEN: 9
        }
        # Initialize counters for strong threats
        white_threats = 0
        black_threats = 0
        max_threats = 0
        # Iterate over all squares on the board
        for square in chess.SQUARES:
            attacker = board.piece_at(square)
            if attacker and attacker.piece_type != chess.KING:
                attacker_weight = weights.get(attacker.piece_type, 0)
                attacked_squares = list(board.attacks(square))
                for attacked_square in attacked_squares:
                    attacked_piece = board.piece_at(attacked_square)
                    if attacked_piece and attacked_piece.color != attacker.color:
                        attacked_weight = weights.get(
                            attacked_piece.piece_type, 0)

                        if attacker_weight > attacked_weight:
                            has_defender = bool(board.attackers(
                                attacked_piece.color, attacked_square))
                            if has_defender:
                                white_threats += (
                                    attacked_weight / 2) if attacker.color == chess.WHITE else 0
                                black_threats += (
                                    attacked_weight / 2) if attacker.color == chess.BLACK else 0
                            else:
                                white_threats += attacked_weight if attacker.color == chess.WHITE else 0
                                black_threats += attacked_weight if attacker.color == chess.BLACK else 0
                            max_threats += 1
        return self.calculate_final_score({
            'attribute': 'strong_threats',
            'white_score': white_threats,
            'black_score': black_threats
        })

    def calculate_forks(self, fen):
        board = chess.Board(fen)
        # Define the weights of the pieces
        weights = {
            chess.PAWN: 1,
            chess.KNIGHT: 3,
            chess.BISHOP: 3,
            chess.ROOK: 5,
            chess.QUEEN: 9
        }
        # Initialize counters for strong tactical opportunities
        white_tactical_opportunities = 0
        black_tactical_opportunities = 0
        # Iterate over all squares on the board
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece and piece.piece_type != chess.KING:
                # Check for forks
                attacks = list(board.attacks(square))
                attacks_for_fork = 2
                for attacked_square in attacks:
                    attacked_piece = board.piece_at(attacked_square)
                    if attacked_piece and attacked_piece.color != piece.color:
                        piece_weight = weights.get(
                            attacked_piece.piece_type, 0)
                        has_defender = bool(board.attackers(
                            attacked_piece.color, attacked_square))
                        attacks_for_fork -= 1
                        if attacks_for_fork == 0:
                            if piece.color == chess.WHITE:
                                if has_defender:
                                    # print(f'White forks a defended piece on {chess.square_name(attacked_square)}')
                                    white_tactical_opportunities += (
                                        piece_weight / 2)
                                else:
                                    # print(f'White fork on {chess.square_name(attacked_square)}')
                                    white_tactical_opportunities += piece_weight
                            else:
                                if has_defender:
                                    # print(f'Black forks a defended piece on {chess.square_name(attacked_square)}')
                                    black_tactical_opportunities += (
                                        piece_weight / 2)
                                else:
                                    # print(f'Black fork on {chess.square_name(attacked_square)}')
                                    black_tactical_opportunities += piece_weight
        return self.calculate_final_score({
            'attribute': 'forks',
            'white_score': white_tactical_opportunities,
            'black_score': black_tactical_opportunities
        })

    def calculate_material_balance(self, fen):
        board = chess.Board(fen)
        # Define the material values of the pieces
        weights = {
            chess.PAWN: 1,
            chess.KNIGHT: 3,
            chess.BISHOP: 3,
            chess.ROOK: 5,
            chess.QUEEN: 9
        }
        # Initialize counters for white and black material
        white_material = 0
        black_material = 0
        # Iterate over all squares on the board
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece:
                piece_weight = weights.get(piece.piece_type, 0)
                if piece.color == chess.WHITE:
                    white_material += piece_weight
                else:
                    black_material += piece_weight
        # Scale the material balance to the range of 0 to 10
        white_score = white_material
        black_score = black_material
        return self.calculate_final_score({
            'attribute': 'material_balance',
            'white_score': white_score,
            'black_score': black_score
        })

    def calculate_space(self, fen):
        """Calculates the space advantage for each player based on the number of squares
        controlled by each player. "Control" is defined as the number of squares that are
        attacked by a player's pieces, and or defended by a player's pawns. For example
        if a white pawn is on the square e4, and there are no black pieces or pawns
        attacking the squares e3, e2, or e1, then white controls those squares. If black
        does attack e3, e2, or e1, then white's credit for defending those squares is
        reduced by 50%. The same is true for black.

        Args:
            fen (string): Chess position fen

        Returns:
            dict: Space advantage for each player
        """
        board = chess.Board(fen)
        white_squares = set()
        black_squares = set()

        for square in chess.SQUARES:
            attackers = board.attackers(chess.WHITE, square)
            defenders = board.attackers(chess.BLACK, square)

            if attackers or defenders:
                if not attackers:
                    white_squares.add(square)
                elif not defenders:
                    black_squares.add(square)
                else:
                    # Reduce credit for squares both attacked and defended by 50%
                    white_squares.add(square)
                    black_squares.add(square)

        white_space = len(white_squares)
        black_space = len(black_squares)

        return self.calculate_final_score({
            'attribute': 'space',
            'white_score': white_space,
            'black_score': black_space
        })

    def calculate_tempo(self, fen):
        pass

    def plot_radar(self, attributes):
        # Define the attribute names
        attribute_names = list(attributes.keys())
        # Get the attribute values for white and black
        white_values = []
        black_values = []
        for attr in attribute_names:
            attr_values = attributes.get(attr, {})
            white_values.append(attr_values.get('white_score'))
            black_values.append(attr_values.get('black_score'))
        # Calculate the total number of attributes
        num_attributes = len(attribute_names)
        # Create a list of angles for the radar plot
        angles = np.linspace(0, 2 * np.pi, num_attributes,
                             endpoint=False).tolist()

        # Close the plot by appending the first angle value
        angles.append(angles[0])
        # Create a figure and axis for the plot
        fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
        # Set the axis limits
        ax.set_ylim([0, 10])
        # Plot the white attribute values
        ax.plot(angles, white_values + [white_values[0]],
                color="orange", linewidth=2, linestyle='solid', label='White')
        ax.fill(angles, white_values +
                [white_values[0]], color="orange", alpha=0.10)
        # Plot the black attribute values
        ax.plot(angles, black_values + [black_values[0]],
                color="blue", linewidth=2, linestyle='solid', label='Black')
        ax.fill(angles, black_values +
                [black_values[0]], color="blue", alpha=0.10)
        # Set the attribute names as labels for each axis
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(attribute_names)
        # Set the title and legend
        ax.set_title('Player Attributes', fontsize=14)
        ax.legend(loc='upper right')
        # Show the plot
        plt.show()

    def train_stats_by_username(self, username='MagnusCarlsen', limit=100):
        """Train the model by calculating the standard deviation and mean for each attribute
        based on a players games.

        Args:
            username (string): The Chess.com username of the player to train the model with

        Returns:
            dict: Stats for each attribute
        """
        pgn_games = self.chessdotcom_service.get_games_by_username(
            username, get_pgns=True, limit=limit)
        attribute_scores = {f: [] for f in self.features}
        with tqdm(total=len(pgn_games), desc='PGNs', leave=False) as pbar_1:
            for pgn_game in pgn_games:
                game = chess.pgn.read_game(io.StringIO(pgn_game))
                headers = dict(game.headers)
                if headers.get('Variant', ''):
                    continue
                board = game.board()
                with tqdm(total=len(list(game.mainline_moves())), desc='FEN features', leave=False) as pbar_2:
                    for move in game.mainline_moves():
                        board.push(move)
                        fen = board.fen()
                        if fen:
                            features = self.get_features_by_fen(fen)
                            # Iterate over each attribute and calculate results separately
                            for attribute, scores in list(features.items()):
                                attribute_scores[attribute].append(
                                    scores.get('white_score'))
                                attribute_scores[attribute].append(
                                    scores.get('black_score'))
                        pbar_2.update(1)
                pbar_1.update(1)
        # Calculate standard deviation and mean for each attribute
        stats = {}
        with tqdm(total=len(attribute_scores), desc='Stats', leave=False) as pbar_3:
            for attribute, scores in attribute_scores.items():
                stats[attribute] = {
                    'std_dev': statistics.stdev(scores),
                    'mean': statistics.mean(scores),
                    'mode': statistics.mode(scores),
                    'max': max(scores),
                    'min': min(scores),
                }
            pbar_3.update(1)
        self.trained_stats = stats
        f = open(
            f'trained_stats_{username}_{limit}_{format(datetime.now(), "%Y-%m-%d")}.json', 'w')
        f.write(json.dumps({
            'username': username,
            'game_count': limit,
            'trained_stats': stats
        }, indent=4))
        f.close()
        print(stats)
        return stats

    def calculate_final_score(self, input_scores):
        # Get Standard Deviation and Mean for each attribute
        if not self.normalize_scores:
            return input_scores
        attr = input_scores.get('attribute', '')
        if not attr:
            raise Exception('Attribute is required')
        if attr == 'pawn_structure_health':
            print()
        std_dev = self.trained_stats.get(
            'trained_stats').get(attr, {}).get('std_dev')
        mean = self.trained_stats.get(
            'trained_stats').get(attr, {}).get('mean')
        if not std_dev or not mean:
            raise Exception('Standard Deviation and Mean are required')
        # Calculate z-scores
        white_z_score = self.calc_z_score(
            input_scores.get('white_score'), mean, std_dev)
        black_z_score = self.calc_z_score(
            input_scores.get('black_score'), mean, std_dev)
        # Rescale the z-scores to the range of 0 to 10
        white_scaled_score = min(self.rescale_value(white_z_score), 10)
        black_scaled_score = min(self.rescale_value(black_z_score), 10)
        return {
            'attribute': attr,
            'white_score': round(white_scaled_score, 4),
            'black_score': round(black_scaled_score, 4),
        }

    @staticmethod
    def calc_z_score(value, mean, std_dev):
        return (value - mean) / std_dev

    @staticmethod
    def rescale_value(z_score, upper_bound=10, lower_bound=0):
        """Map the z-scores to the desired range (0 to 10). You can use linear interpolation to achieve this. The formula for linear interpolation is:

        rescaled_value = (z-score - min_z) * (new_max - new_min) / (max_z - min_z) + new_min

        In this formula, the new_min is 0, and the new_max is 10. min_z and max_z represent the minimum and maximum possible z-scores.

        Args:
            z_score (_type_): _description_
            upper_bound (_type_): _description_
            lower_bound (_type_): _description_

        Returns:
            _type_: _description_
        """
        min_z = -3
        max_z = 3
        return (z_score - min_z) * (upper_bound - lower_bound) / (max_z - min_z) + lower_bound


if __name__ == '__main__':
    try:
        stockfish_service = StockfishService.build(
            path='/opt/homebrew/bin/stockfish')
    except Exception as e:
        stockfish_service = StockfishService.build(
            path='/usr/local/bin/stockfish')
    radar = RadarService.build(
        stockfish_service,
        stats_file='trained_stats_MagnusCarlsen_1000_2023-06-26.json',
        normalize_scores=False
    )
    # create_radar_plot(features_white, features_black)
    # fen = '1r1q1r1k/1N4bp/8/2n1pp2/bpPp1P2/3P2PP/4N1BK/1R1Q1R2 w - - 0 23'
    # fen = '1r1q1r1k/1N1b2bp/8/2n1pp2/PpPp1P2/3P2PP/4N1BK/1R1Q1R2 b - - 0 22'
    # fen = '4r2k/1p5p/8/1P3p2/1r1qpP2/3pQ1PP/3Nn1BK/3R4 w - - 4 38'
    # fen = '1r6/p1Q1k3/6p1/5pP1/8/1p2P1K1/8/8 b - - 2 46'
    fen = '4Q1k1/pp3ppp/3r2n1/1n3q2/7P/1P4P1/P4NB1/3R2K1 b - - 1 29'
    # fen = '1r1q1r1k/1p1b2bp/8/1Nn1pp2/PpPp1P2/3P2PP/4N1BK/1R1Q1R2 b - - 2 22'
    # fen = '1r1q1r1k/1p4bp/8/1bn1pp2/PpPp1P2/3P2PP/4N1BK/1R1Q1R2 w - - 0 23'
    # fen = '8/8/p4pk1/P1R3p1/6Pp/r6P/5P1K/8 b - - 1 48'

    # features = radar.get_features_by_fen(fen)
    # radar.plot_radar(features)
    # print('results: ', features)
    results = radar.train_stats_by_username('MagnusCarlsen', limit=1000)
    results = radar.train_stats_by_username('TobiahsRex', limit=1000)
    # print(results)
    # radar.normalize_values(radar.toby_scores)
