import threading
from stockfish import Stockfish


class StockfishService:
    def __init__(self, *args, **kwargs):
        self.fish = kwargs.get("stockfish")
        self.lock = threading.Lock()

    @staticmethod
    def build(path):
        try:
            fish = Stockfish(
                path=path,
                depth=10,
            )
            fish.update_engine_parameters(
                {
                    "Hash": 2048,
                    "Threads": 4,
                    "Minimum Thinking Time": 10,
                }
            )
            return StockfishService(stockfish=fish)
        except Exception as e:
            print(e)

    def get_stockfish(self):
        return self.fish

    def acquire_lock(self):
        self.lock.acquire()

    def release_lock(self):
        self.lock.release()

    def get_top_moves(self, fen, n):
        self.acquire_lock()
        try:
            self.fish.set_fen_position(fen)
            top_moves = self.fish.get_top_moves(n)
        finally:
            self.release_lock()
        return top_moves

    def get_game_by_pgn(self, pgn):
        self.fish.reset_engine_parameters()
        self.fish.set_


if __name__ == "__main__":
    try:
        f = StockfishService.build(path="/opt/homebrew/bin/stockfish")
    except Exception as e:
        f = StockfishService.build(path="/usr/local/bin/stockfish")
    f.acquire_lock()
    f.fish.set_fen_position("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR")
    top_moves = f.fish.get_top_moves(5)
    print(top_moves)
    f.release_lock()
