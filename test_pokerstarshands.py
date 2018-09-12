from pokerstarsgame import Pokerstarsgame
import os, re
import json

gamefiledir = "hands"
#gamefile = "HH20180626 T2342396672 No Limit Hold'em $0.91 + $0.09.txt"
gamefile = 'HH20180626_T2342391818.txt'

with open(gamefiledir + '/' + gamefile, 'r') as fl:
    lines = fl.read()
fl.closed

gamelist = [x for x in lines.split('\n')]

game = Pokerstarsgame(gamelist, game_filename=gamefile)

game.generate_hands()

print(game.get_json_hands())
#print(game.get_game_infos())
#print(game.get_hands_number())
game.save_mongo()
