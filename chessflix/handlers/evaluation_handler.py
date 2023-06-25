from services.radar_service import RadarService

class EvaluationHandler:
    def __init__(self, *args, **kwargs):
        self.stockfish_service = kwargs.get('stockfish_service')
        self.radar_service = kwargs.get('radar_service')

    @staticmethod
    def build(stockfish_service):
        radar_service = RadarService.build(
            stockfish_service,
            stats_file='trained_stats_MagnusCarlsen_1000_2023-06-26.json',
            normalize_scores=True)
        return EvaluationHandler(
            stockfish_service=stockfish_service,
            radar_service=radar_service
        )

    def calculate_game_evaluations(self, fen, moves):
        results = {
            'evaluations': [],
            'radar_features': []
        }
        stockfish = self.stockfish_service.get_stockfish()
        stockfish.set_fen_position(fen)
        for move in moves:
            stockfish.make_moves_from_current_position([move])
            curr_fen = stockfish.get_fen_position()
            results['evaluations'].append(stockfish.get_evaluation().get('value'))
            results['radar_features'].append(self.radar_service.get_features_by_fen(curr_fen))
        return results

    def calculate_position_evaluation(self, fen):
        stockfish = self.stockfish_service.get_stockfish()
        stockfish.set_fen_position(fen)
        evaluation = stockfish.get_evaluation().get('value')
        radar_features = self.radar_service.get_features_by_fen(fen)
        return {
            'evaluation': evaluation,
            'radar_features': radar_features,
        }

    def generate_previews(self, fen, preview_count, depth):
        stockfish = self.stockfish_service.get_stockfish()
        stockfish.set_fen_position(fen)
        previews = []
        top_moves = stockfish.get_top_moves(fen, preview_count)

        for start_move in top_moves:
            stockfish.reset_engine_parameters()
            stockfish.set_fen_position(fen)
            preview = {
                'startingPosition': fen,
                'moves': [],
                'evaluations': [],
                'radar_features': []
            }
            start_move = start_move.get('Move')
            preview['moves'].append(start_move)
            stockfish.make_moves_from_current_position([start_move])
            preview['evaluations'].append(stockfish.get_evaluation().get('value'))
            for _ in range(depth - 1):
                best_move = stockfish.get_best_move()
                preview['moves'].append(best_move)
                stockfish.make_moves_from_current_position([best_move])
                curr_fen = stockfish.get_fen_position()
                preview['radar_features'].append(self.radar_service.get_features_by_fen(curr_fen))
                preview['evaluations'].append(stockfish.get_evaluation().get('value'))
                if not best_move:
                    preview['moves'].append('')
                    preview['evaluations'].append(0)
                    continue
            previews.append(preview)

        return previews