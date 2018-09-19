import re, json
import pymongo
from pymongo import MongoClient
from pymongo.collection import Collection
from settings import Settings
from player import Player

class Pokerstarsgame:
    def __init__(self, gamelog, game=None, game_filename=None):
        """
        gamelog parameter is an array with element beeing lines
        of the logs file
        game parameter is the name of the game. Optionnal or set on
        object creation
        game_filename is the name of the gamefile. Optionnal or
        set on object creation. will parse the name from the filename
        """
        regex_gameid = re.compile(r'^.*Tournament #(\d+),.*$')
        self.gamelog = gamelog
        self.hands = []
        self.hands_id = []
        self.players = {} # player objects
        self.init_mongo = False
        if re.match(r'^.*\$([\d\.]+)\+\$([\d\.]+) USD.*$', gamelog[0]):
            price = re.search(r'^.*\$([\d\.]+)\+\$([\d\.]+) USD.*$',
                              gamelog[0])
            self.game_price = float(price.group(1)) + float(price.group(2))
        else:
            self.game_price = 0.0
        if game is not None:
            self.game_id = game
        elif game_filename is not None:
            game_id = re.search(r'^.*(T\d+).*$', game_filename).group(1)
            self.game_id = game_id
        elif re.match(regex_gameid, self.gamelog[0]):
            self.game_id = 'T' + str(re.search(regex_gameid, gamelog[0]).group(1))
        else:
            raise NameError("game name is not readable or not set properly")
        self.check = re.compile(r'^(.*): (checks)\s+$')
        self.bet = re.compile(r'^(.*): (bets) (\d+)$')
        self.fold = re.compile(r'^(.*): (folds)\s+$')
        self.rais = re.compile(r'^(.*): (raises) (\d+) to (\d+)$')
        self.call = re.compile(r'^(.*): (calls) (\d+)$')
        self.betai = re.compile(r'^(.*): (bets) (\d+) and is all-in$')
        self.raisai = re.compile(r'^(.*): (raises) (\d+) to (\d+) an.*-in$')
        self.callai = re.compile(r'^(.*): (calls) (\d+) and is all-in$')
        self.unclbt = re.compile(r'^Uncalled bet \((\d+)\).*to (.*)$')
        self.clfpot = re.compile(r'^(.*) ?collected (\d+) from pot$')
        self.noshow = re.compile(r'^(.*): doesn\'t show hand $')

    def _hands_to_dict(self, log):
        """parse the game logfile to an array of dictionnary of hands"""
        parse_hand = {}
        # parsing hand ID
        hand_n = re.search(r'^.*Hand #(\d+): .*$', log[0]).group(1)
        parse_hand['_id'] = hand_n
        self.hands_id.append(hand_n)
        parse_hand['game_id'] = self.game_id
        # parsing button position
        button = re.search(r'^.*#(\d).*$', log[1]).group(1)
        parse_hand['Button'] = button
        i = 2 # i is the cursor on the gamelog
        # parsing players
        parse_hand['players'] = []
        while re.search(r'^Seat \d:.*$', log[i]):
            player = {}
            p = re.search(r'^.* ?(\d): (.*) \((\d+).*$', log[i])
            player['name'] = p.group(2)
            player['stack'] = p.group(3)
            player['seat'] = p.group(1)
            parse_hand['players'].append(player)
            i += 1
        # store player list
        player_list = [p['name'] for p in parse_hand['players']]
        # update player object list if needed or create it
        for p in player_list:
            if not p in self.players.keys():
                self.players[p] = Player(p)
        # parsing deal action
        # blinds
        parse_hand['ante'] = []
        while re.search(r'^.*posts.*$', log[i]):
            blind = re.search(r'^(.*): posts ([a-z ]+) (\d+).*$', log[i])
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
        if re.search(r'^Dealt.*$', log[i]):
            parse_hand['cards'] = re.search(r'^.*(\[.*\])$', log[i]).group(1)
        else:
            parse_hand['cards'] = ''
        i += 1
        # preflop action
        preflop = []
        while not re.search(r'^\*\*\*.*\*\*\*.*$', log[i]):
            preflop.append(log[i])
            i += 1
        parse_hand['preflop'] = self._parse_action('preflop', preflop, len(player_list))

        # parsing FLOP
        try:
            dealt_cards = re.search(r'^\*\*\* FLOP \*\*\* \[(.*)\]$', log[i]).group(1)
        except AttributeError:
            summary = log[i+1:]
            parse_hand['summary'] = self._parse_summary(summary)
            return parse_hand
        i += 1
        flop = []
        while not re.search(r'^\*\*\*.*\*\*\*.*$', log[i]):
            flop.append(log[i])
            i += 1
        parse_hand['flop'] = self._parse_action('flop', flop, len(player_list))
        parse_hand['flop'].append({'card': dealt_cards})

        # parsing TURN
        try:
            turn_card = re.search(r'^\*\*\* TURN \*\*\*.*\[(.*)\]$', log[i]).group(1)
        except AttributeError:
            summary = log[i+1:]
            parse_hand['summary'] = self._parse_summary(summary)
            return parse_hand
        i += 1
        turn = []
        while not re.search(r'^\*\*\*.*\*\*\*.*$', log[i]):
            turn.append(log[i])
            i += 1
        parse_hand['turn'] = self._parse_action('turn', turn, len(player_list))
        parse_hand['turn'].append({'card': turn_card})

        # parsing RIVER
        try:
            river_card = re.search(r'^\*\*\* RIVER \*\*\*.*\[(.*)\]$', log[i]).group(1)
        except AttributeError:
            summary = log[i+1:]
            parse_hand['summary'] = self._parse_summary(summary)
            return parse_hand
        i += 1
        river = []
        while not re.search(r'^\*\*\*.*\*\*\*.*$', log[i]):
            river.append(log[i])
            i += 1
        parse_hand['river'] = self._parse_action('river', river, len(player_list))
        parse_hand['river'].append({'card': river_card})

        # parsing SHOWDOWN
        if re.match(r'^\*\*\* SUMMARY \*\*\*.*$', log[i]):
            summary = log[i+1:]
            parse_hand['summary'] = self._parse_summary(summary)
            return parse_hand
        i += 1
        showdown = []
        while not re.search(r'^\*\*\*.*\*\*\*.*$', log[i]):
            showdown.append(log[i])
            i += 1
        parse_hand['showdown'] = self._parse_showdown(showdown)
        return parse_hand

    def _parse_showdown(self, showdown):
        """
        parse showdown lines
        """
        shows = re.compile(r'^(.*): shows \[(.*?)\] \((.*)\)$')
        wins = re.compile(r'^(.*?) collected (\d+)\sfrom\s(.*)$')
        finish = re.compile(r'^(.*?) finished.*in (.*?) place\s+$')
        show_list = []
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
            if not show:
                show["error"] = "parse did not work for showdown line"
                show["line"] = line
            show_list.append(show)
        return show_list

    def _parse_action(self, action_name, action_list, player_nb):
        # need to add number of player to keep track of tour de table
        # pour calculer les pfr vpip etc...
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
            act = {}
            if re.match(self.check, action) and action_name != 'preflop':
                f = re.search(self.check, action)
                act['player'] = f.group(1)
                act['action'] = f.group(2)
                # update player
                self.players[f.group(1)].update('check', action_name)
            elif re.match(self.bet, action) and action_name != 'preflop':
                f = re.search(self.bet, action)
                act['player'] = f.group(1)
                act['action'] = f.group(2)
                act['chips'] = f.group(3)
                # update player
                self.players[f.group(1)].update('bet', action_name)
            elif re.match(self.fold, action):
                f = re.search(self.fold, action)
                act['player'] = f.group(1)
                act['action'] = f.group(2)
            elif re.match(self.rais, action):
                f = re.search(self.rais, action)
                act['player'] = f.group(1)
                act['action'] = f.group(2)
                act['chips'] = f.group(3)
                act['chiptotal'] = f.group(4)
                # update player
                self.players[f.group(1)].update('raise', action_name)
            elif re.match(self.call, action):
                f = re.search(self.call, action)
                act['player'] = f.group(1)
                act['action'] = f.group(2)
                act['chiptotal'] = f.group(3)
                # update player
                self.players[f.group(1)].update('call', action_name)
            elif re.match(self.betai, action):
                f = re.search(self.betai, action)
                act['player'] = f.group(1)
                act['action'] = f.group(2)
                act['chips'] = f.group(3)
                act['all-in'] = True
                # update player
                self.players[f.group(1)].update('betallin', action_name)
            elif re.match(self.raisai, action):
                f = re.search(self.raisai, action)
                act['player'] = f.group(1)
                act['action'] = f.group(2)
                act['chips'] = f.group(3)
                act['chiptotal'] = f.group(4)
                act['all-in'] = True
                # update player
                self.players[f.group(1)].update('raiseallin', action_name)
            elif re.match(self.callai, action):
                f = re.search(self.callai, action)
                act['player'] = f.group(1)
                act['action'] = f.group(2)
                act['chiptotal'] = f.group(3)
                act['all-in'] = True
                # update player
                self.players[f.group(1)].update('callallin', action_name)
            elif re.match(self.unclbt, action):
                f = re.search(self.unclbt, action)
                act['player'] = f.group(2)
                act['uncallbet'] = f.group(1)
            elif re.match(self.clfpot, action):
                f = re.search(self.clfpot, action)
                act['player'] = f.group(1)
                act['collect'] = f.group(2)
            elif re.match(self.noshow, action):
                f = re.search(self.noshow, action)
                act['player'] = f.group(1)
                act['cards'] = 'NoShow'
            if not action:
                act["error"] = "parse did not work for action line"
                act["line"] = action
            act['id'] = action_id
            action_id += 1
            parsed_action.append(act)
        return parsed_action

    def _parse_summary(self, slines):
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

    def generate_hands(self):
        """generate the list of hands on dictionnary type"""
        hand = []
        for line in self.gamelog:
            # hands in the log file are separated by empty lines
            # will then add all consecutive line to a list
            # send the list to process function for parsing 
            # then clear for next hand processing
            if line == '':
                if len(hand) > 1:
                    self.hands.append(self._hands_to_dict(hand))
                    del hand[:]
                    hand = []
                continue
            else:
                hand.append(line)

    def get_json_hands(self):
        return json.dumps(self.hands)

    def get_hands_number(self):
        return len(self.hands)

    def get_players_infos(self):
        r = {}
        for name, obj in self.players.items():
            pfr = obj.get_pfr() * 100
            vpip = obj.get_vpip() * 100
            r[name] = {'pfr': '{:.2f}'.format(pfr),
                       'vpip': '{:.2f}'.format(vpip)}
        return r

    def get_game_infos(self, out_json=True):
        gameid = int(re.search(r'(\d+)', self.game_id).group(1))
        data = {}
        data["hands"] = self.hands_id
        data["entry_price"] = self.game_price
        data["_id"] = gameid
        if out_json:
            return json.dumps(data)
        return data

    def initmongo(self):
        if self.init_mongo:
            return
        settings = Settings()
        self.mongo_client = MongoClient(settings.mongo_host,
                                        settings.mongo_port)
        self.mongo_db = self.mongo_client[settings.mongo_db_name]
        self.init_mongo = True

    def save_mongo(self):
        """
        save hands to collection `hands`
        and save infos to collection `games`
        """
        settings = Settings()
        db_name = settings.mongo_db_name
        if not self.init_mongo:
            self.initmongo()
        # save hands
        try:
            self.mongo_db.hands.insert_many(
                    self.hands
                    )
        except pymongo.errors.BulkWriteError:
            print('Duplicate id already in use '
                  + self.game_id)
        else:
            print("Saved " + str(self.get_hands_number()) +
                  " hands to " + db_name +
                  " in collection `hands`")

        # save game infos
        try:
            self.mongo_db.games.insert_one(
                    self.get_game_infos(out_json=False)
                    )
        except pymongo.errors.DuplicateKeyError:
            print('Duplicate id already in use '
                    + self.game_id)
        else:
            print("Saved game information" +
                  " to " + db_name +
                  " in collection `games`")
