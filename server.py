from flask import Flask, request, jsonify
from flask_cors import CORS
from stockfish import Stockfish

app = Flask(__name__)
CORS(app, origins=['http://localhost:3000'], allow_headers='Content-Type')

stockfish = None


def getStockfish():
    global stockfish
    if not stockfish:
        stockfish = Stockfish(path='/opt/homebrew/bin/stockfish')
        stockfish.update_engine_parameters({
            'Hash': 2048,
            'Threads': 4,
            'Minimum Thinking Time': 10,
        })
    return stockfish


def resetStockfish():
    print('wtf?')
    global stockfish
    stockfish = None
    getStockfish()


stockfish = getStockfish()


@app.route('/', methods=['GET'])
def test_server():
    return 'Server is running'


@app.route('/reset', methods=['POST'])
def reset():
    resetStockfish()
    return jsonify({'message': 'Stockfish reset'})


@app.route('/game-evals', methods=['POST'])
def calculate_game_evals():
    try:
        stockfish = getStockfish()
        req = request.json
        stockfish.set_fen_position(req.get('fen'))
        evaluations = []
        for move in req.get('moves'):
            stockfish.make_moves_from_current_position([move])
            evaluations.append(stockfish.get_evaluation().get('value'))
        response = {'evaluations': evaluations}
        return jsonify(response)
    except Exception as e:
        print(e)
        return jsonify({'error': 'Something went wrong'})


@app.route('/position-eval', methods=['POST'])
def calculate_position_eval():
    try:
        stockfish = getStockfish()
        fen = request.json.get('fen')
        stockfish.set_fen_position(fen)
        evaluation = stockfish.get_evaluation()
        response = {'evaluation': evaluation.get('value')}
        return jsonify(response)
    except Exception as e:
        print(e)
        return jsonify({'error': 'Something went wrong', evaluation: 0})


@app.route('/previews', methods=['POST'])
def calculate_previews():
    try:
        stockfish = getStockfish()
        fen = request.json['fen']
        previewCount = int(request.json['previewCount'])
        depth = int(request.json['depth'])
        previews = []
        stockfish.set_fen_position(fen)
        top_moves = stockfish.get_top_moves(previewCount)
        print('top_moves', top_moves)
        for start_move in top_moves:
            stockfish.reset_engine_parameters()
            stockfish.set_fen_position(fen)
            preview = {
                'startingPosition': fen,
                'moves': [],
                'evaluations': [],
            }
            startMove = start_move.get('Move')
            preview['moves'].append(startMove)
            stockfish.make_moves_from_current_position([startMove])
            preview['evaluations'].append(
                stockfish.get_evaluation().get('value'))
            for _ in range(depth - 1):
                best_move = stockfish.get_best_move()
                preview['moves'].append(best_move)
                stockfish.make_moves_from_current_position([best_move])
                preview['evaluations'].append(
                    stockfish.get_evaluation().get('value'))
                if not best_move:
                    preview['moves'].append('')
                    preview['evaluations'].append(0)
                    continue
            previews.append(preview)
        response = {'previews': previews}
        print(response)
        return jsonify(response)
    except Exception as e:
        print(e)
        return jsonify({'error': 'Something went wrong'})


if __name__ == '__main__':
    app.run(port=5000, debug=True)
