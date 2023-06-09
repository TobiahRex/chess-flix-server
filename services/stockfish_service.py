import threading
from stockfish import Stockfish

class StockfishService:
    def __init__(self):
        self.stockfish = None
        self.lock = threading.Lock()

    def build(self, path):
        self.stockfish = Stockfish(path)

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
