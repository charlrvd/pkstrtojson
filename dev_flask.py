from flask import Flask
from flask import render_template
from pokerstarsgame import Pokerstarsgame
import os, json

app = Flask(__name__)

@app.route("/")
def chart():
    gamefile = 'HH20180626_T2342391818.txt'
    with open('hands/' + gamefile, 'r') as fl:
        lines = fl.read()
        fl.closed
    game_list = [x for x in lines.split('\n')]
    game = Pokerstarsgame(game_list)
    game.generate_hands()
    #print(game.get_players_infos())
    for player, values in game.get_players_infos().items():
        print(player)
        print(values)
    print(game.get_players_infos())
    data = game.get_players_infos()
    #return json.dumps(game.get_players_infos())
    return render_template('index.html', data=data)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
