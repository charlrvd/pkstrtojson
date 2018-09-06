import os
import re
import json

# will use below for bulk
#files = [f for f in os.listdir('handshistory')
#         if os.path.isfile(os.path.join('handshistory', f))
#            and not re.match('^.*Play.*$', f)]
#print(len(files))

parse_res = {}
hand = []
# tmp while dev
f_in = "HH20180626_T2342391818.txt"

#f_in = input('file > ')

# regex with original name
#game_name = re.search(r'^.*? (.*).txt', f_in).group(1)
game_name = re.search(r'^.*_(.*)\.txt$', f_in).group(1)
parse_res['Game'] = game_name
parse_res['hands'] = []

# regex used later on
check = re.compile(r'^(.*): (checks)\s+$')
bet = re.compile(r'^(.*): (bets) (\d+)$')
fold = re.compile(r'^(.*): (folds)\s+$')
rais = re.compile(r'^(.*): (raises) (\d+) to (\d+)$')
call = re.compile(r'^(.*): (calls) (\d+)$')
betai = re.compile(r'^(.*): (bets) (\d+) and is all-in$')
raisai = re.compile(r'^(.*): (raises) (\d+) to (\d+) and is all-in$')
callai = re.compile(r'^(.*): (calls) (\d+) and is all-in$')
unclbt = re.compile(r'^Uncalled bet \((\d+)\).*to (.*)$')
clfpot = re.compile(r'^(.*) ?collected (\d+) from pot$')
noshow = re.compile(r'^(.*): doesn\'t show hand $')

with open('hands/' + f_in, 'r') as fl:
    open_f = fl.read()
fl.closed

def process_hand(li):
    lines_li = len(li)
    parse_hand = {}
    # parsing hand ID
    hand_n = re.search(r'^.*Hand #(\d+): .*$', li[0]).group(1)
    parse_hand['id'] = hand_n
    # parsing button position
    button = re.search(r'^.*#(\d).*$', li[1]).group(1)
    parse_hand['Button'] = button
    # below parsing players
    i = 2
    parse_hand['players'] = []
    while re.search(r'^Seat \d:.*$', li[i]):
        player = {}
        p = re.search(r'^.* ?(\d): (.*) \((\d+).*$', li[i])
        player['name'] = p.group(2)
        player['stack'] = p.group(3)
        player['seat'] = p.group(1)
        parse_hand['players'].append(player)
        i += 1
    # store player list for later use
    player_list = [p['name'] for p in parse_hand['players']]
    # parsing deal action
    # blinds
    parse_hand['ante'] = []
    while re.search(r'^.*posts.*$', li[i]):
        blind = re.search(r'^(.*): posts ([a-z ]+) (\d+).*$', li[i])
        blind_type = 'ante'
        if blind.group(2) == 'big blind':
            blind_type = 'bb'
        elif blind.group(2) == 'small blind':
            blind_type = 'sb'
        if blind_type != 'ante':
            parse_hand[blind_type] = {'value': blind.group(3), 
                                        'player': blind.group(1)}
        else:
            parse_hand[blind_type].append({'value': blind.group(3), 
                                            'player': blind.group(1)})
        i += 1
    # preflop
    i += 1
    # User cards
    if re.search(r'^Dealt.*$', li[i]):
        parse_hand['cards'] = re.search(r'^.*(\[.*\])$', li[i]).group(1)
    else:
        parse_hand['cards'] = ''
    i += 1
    # preflop action
    preflop = []
    while not re.search(r'^\*\*\*.*\*\*\*.*$', li[i]):
        preflop.append(li[i])
        i += 1
    parse_hand['preflop'] = parse_action('preflop', preflop)

    # parsing FLOP
    try:
        dealt_cards = re.search(r'^\*\*\* FLOP \*\*\* \[(.*)\]$', li[i]).group(1)
    except AttributeError:
        summary = li[i+1:]
        parse_hand['summary'] = parse_summary(summary)
        return parse_hand
    i += 1
    flop = []
    while not re.search(r'^\*\*\*.*\*\*\*.*$', li[i]):
        flop.append(li[i])
        i += 1
    parse_hand['flop'] = parse_action('flop', flop)
    parse_hand['flop'].append({'dealt_cards': dealt_cards})

    # parsing TURN
    try:
        turn_card = re.search(r'^\*\*\* TURN \*\*\*.*\[(.*)\]$', li[i]).group(1)
    except AttributeError:
        summary = li[i+1:]
        parse_hand['summary'] = parse_summary(summary)
        return parse_hand
    i += 1
    turn = []
    while not re.search(r'^\*\*\*.*\*\*\*.*$', li[i]):
        turn.append(li[i])
        i += 1
    parse_hand['turn'] = parse_action('turn', turn)
    parse_hand['turn'].append({'turn_card': turn_card})

    # parsing RIVER
    try:
        river_card = re.search(r'^\*\*\* RIVER \*\*\*.*\[(.*)\]$', li[i]).group(1)
    except AttributeError:
        summary = li[i+1:]
        parse_hand['summary'] = parse_summary(summary)
        return parse_hand
    i += 1
    river = []
    while not re.search(r'^\*\*\*.*\*\*\*.*$', li[i]):
        river.append(li[i])
        i += 1
    parse_hand['river'] = parse_action('river', river)
    parse_hand['river'].append({'turn_card': river_card})

    # parsing SHOWDOWN
    i += 1
    showdown = []
    while not re.search(r'^\*\*\*.*\*\*\*.*$', li[i]):
        showdown.append(li[i])
        i += 1
    parse_hand['showdown'] = parse_showdown(showdown)
    
    #print(li[i])

    #print(json.dumps(parse_hand))
    #print(parse_hand)
    return parse_hand

def parse_showdown(showdown):
    """
    parse showdown lines
    """
    shows = re.compile(r'^(.*): shows \[(.*?)\] \((.*)\)$')
    wins = re.compile(r'^(.*?) collected (\d+)\sfrom\s(.*)$')
    finish = re.compile(r'^(.*?) finished.*in (.*?) place\s+$')
    show_list = []

    #parse_hand['showdown'].append({'player': r_search.group(1),
    #                                'cards': r_search.group(2),
    #                                'cards_value': r_search.group(3)})
    for line in showdown:
        show = {}
        if re.match(shows, line):
            f = re.search(shows, line)
            show['player'] = f.group(1)
            show['cards'] = f.group(2)
            show['hand_text'] = f.group(3)
        elif re.match(wins, line):
            f = re.search(wins, line)
            show['player'] = f.group(1)
            show['chips'] = f.group(2)
            show['pot_name'] = f.group(3)
        elif re.match(finish, line):
            f = re.search(finish, line)
            show['player'] = f.group(1)
            show['finish'] = True
            show['place'] = f.group(2)
        show_list.append(show)
    return show_list

def parse_action(action_name, action_list):
    """
    function to parse lines the line for
    preflop, flop, turn, river
    receive [action_list] as a list of line for the part of the game
    will parse the result into variable 'a' and return it
    """
    parsed_action = []
    action_id = 0
    # possible action
    # - check
    # - bet
    # - fold
    # - raise
    # - call
    # - bet all in
    # - raise all in
    # - call all in
    # uncalled bet
    # callected from pot
    # no show
    for action in action_list:
        act = {'id': action_id}
        if re.match(check, action) and action_name != 'preflop':
            f = re.search(check, action)
            act['player'] = f.group(1)
            act['action'] = f.group(2)
        elif re.match(bet, action) and action_name != 'preflop':
            f = re.search(bet, action)
            act['player'] = f.group(1)
            act['action'] = f.group(2)
            act['chips'] = f.group(3)
        elif re.match(fold, action):
            f = re.search(fold, action)
            act['player'] = f.group(1)
            act['action'] = f.group(2)
        elif re.match(rais, action):
            f = re.search(rais, action)
            act['player'] = f.group(1)
            act['action'] = f.group(2)
            act['chips'] = f.group(3)
            act['chiptotal'] = f.group(4)
        elif re.match(call, action):
            f = re.search(call, action)
            act['player'] = f.group(1)
            act['action'] = f.group(2)
            act['chiptotal'] = f.group(3)
        elif re.match(betai, action):
            f = re.search(betai, action)
            act['player'] = f.group(1)
            act['action'] = f.group(2)
            act['chips'] = f.group(3)
            act['all-in'] = True
        elif re.match(raisai, action):
            f = re.search(raisai, action)
            act['player'] = f.group(1)
            act['action'] = f.group(2)
            act['chips'] = f.group(3)
            act['chiptotal'] = f.group(4)
            act['all-in'] = True
        elif re.match(callai, action):
            f = re.search(callai, action)
            act['player'] = f.group(1)
            act['action'] = f.group(2)
            act['chiptotal'] = f.group(3)
            act['all-in'] = True
        elif re.match(unclbt, action):
            f = re.search(unclbt, action)
            act['player'] = f.group(2)
            act['uncallbet'] = f.group(1)
        elif re.match(clfpot, action):
            f = re.search(clfpot, action)
            act['player'] = f.group(1)
            act['collect'] = f.group(2)
        elif re.match(noshow, action):
            f = re.search(noshow, action)
            act['player'] = f.group(1)
            act['cards'] = 'NoShow'
        action_id += 1
        parsed_action.append(act)
    return parsed_action

def parse_summary(slines):
    """
    gets a list of line of hand summary {slines}
    parse those line to get the pot total and rake
    and the collected chips per used
    """
    s = {}
    # sided pots ex:
    # Total pot 2000 Main pot 1320. Side pot-1 380. Side pot-2 300. | Rake 0
    pot_rake = re.search(r'^.*pot (\d+) \| Rake (\d+)\s+$', slines[0])
    collect = re.compile(r'^Seat.*?: (.*?) .*\((\d+)\)$')
    s['collect'] = []
    if pot_rake is not None:
        s['pot'] = pot_rake.group(1)
        s['rake'] = pot_rake.group(2)
    else:
        s['pot'] = 'Value Error'
        s['rake'] = 'Value Error'
    for line in slines[1:]:
        user_collect = {}
        if re.match(collect, line):
            f = re.search(collect, line)
            user_collect['name'] = f.group(1)
            user_collect['chips'] = f.group(2)
            s['collect'].append(user_collect)
    return s
            

for line in [x for x in open_f.split('\n')]:
    # hands in the log file are separated by empty lines
    # will then add all consecutive line to a list
    # send the list to process function for parsing 
    # then clear for next hand processing
    if line == '':
        if len(hand) > 1:
            parse_res['hands'].append(process_hand(hand))
            del hand[:]
            hand = []
        continue
    else:
        hand.append(line)
#print('done')

print(json.dumps(parse_res))
