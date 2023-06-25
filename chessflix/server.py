from flask import Flask, request, jsonify
from flask_cors import CORS

from services.stockfish_service import StockfishService
from handlers.evaluation_handler import EvaluationHandler

app = Flask(__name__)
CORS(app, origins=['http://localhost:3000'], allow_headers='Content-Type')

try:
    # stockfish_service = StockfishService.build(path='/opt/homebrew/bin/stockfish')
    stockfish_service = StockfishService.build(path='/usr/local/bin/stockfish')
except Exception as e:
    stockfish_service = StockfishService.build(path='/opt/homebrew/bin/stockfish')
eval_handler = EvaluationHandler.build(stockfish_service)


@app.route('/', methods=['GET'])
def test_server():
    return 'Server is running'

@app.route('/reset', methods=['POST'])
def reset():
    stockfish_service.build(path='/usr/local/bin/stockfish')
    return jsonify({'message': 'Stockfish reset'})


@app.route('/eval/game', methods=['POST'])
def calculate_game_evals():
    try:
        req = request.json
        fen = req.get('fen')
        moves = req.get('moves')
        payload = eval_handler.calculate_game_evaluations(fen, moves)
        print(payload)
    except Exception as e:
        print(e)
        return jsonify({'error': 'Something went wrong'})

@app.route('/eval/position', methods=['POST'])
def calculate_position_eval():
    try:
        fen = request.json.get('fen')
        payload = eval_handler.calculate_position_evaluation(fen)
        print(payload)
        return jsonify(payload)
    except Exception as e:
        print(e)
        return jsonify({'error': 'Something went wrong', 'evaluation': 0})


@app.route('/eval/previews', methods=['POST'])
def calculate_previews():
    try:
        fen = request.json['fen']
        preview_count = int(request.json['previewCount'])
        depth = int(request.json['depth'])
        payload = eval_handler.generate_previews(fen, preview_count, depth)
        print(payload)
        return jsonify(payload)
    except Exception as e:
        print(e)
        return jsonify({'error': 'Something went wrong'})


if __name__ == '__main__':
    app.run(port=5000, debug=True)
