import threading
from stockfish import Stockfish


class StockfishService:
    def __init__(self, *args, **kwargs):
        self.stockfish = kwargs.get('stockfish')
        self.lock = threading.Lock()

    @staticmethod
    def build(path):
        try:
            stockfish = Stockfish(path=path)
        except Exception as e:
            print(e)
        stockfish.update_engine_parameters({
            'Hash': 2048,
            'Threads': 4,
            'Minimum Thinking Time': 10,
        })
        return StockfishService(stockfish=stockfish)

    def get_stockfish(self):
        return self.stockfish

    def acquire_lock(self):
        self.lock.acquire()

    def release_lock(self):
        self.lock.release()

    def get_top_moves(self, fen, n):
        self.acquire_lock()
        try:
            self.stockfish.set_fen_position(fen)
            top_moves = self.stockfish.get_top_moves(n)
        finally:
            self.release_lock()
        return top_moves

    def get_game_by_pgn(self, pgn):
        self.stockfish.reset_engine_parameters()
        self.stockfish.set_


if __name__ == '__main__':
    try:
        fish = StockfishService.build(path='/opt/homebrew/bin/stockfish')
    except Exception as e:
        fish = StockfishService.build(path='/usr/local/bin/stockfish')
    fish.acquire_lock()
    fish.stockfish.set_fen_position(
        'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR')
    top_moves = fish.stockfish.get_top_moves(5)
    print(top_moves)
    fish.release_lock()
