class Player:
    def __init__(self, name):
        self.name = name
        self.walks = 0
        self.global_vpip = 0
        self.global_af = 0
        self.global_pfr = 0
        self.vpip = 0
        self.af = 0
        self.pfr = 0
        self.raise_pre = 0
        self.call_pre = 0

    def update(self, action, action_name):
        #print(self.name + ' ' + action + ' during ' + action_name)
        self.walks += 1
        if action_name == 'preflop' and action == 'raise':
            self.raise_pre += 1
        elif action_name == 'preflop' and action == 'call':
            self.call_pre += 1

    def get_vpip(self):
        if self.walks > 0:
            self.vpip = (self.raise_pre + self.call_pre) / self.walks
            return self.vpip
        else:
            return 0

    def get_pfr(self):
        if self.walks > 0:
            self.pfr = self.raise_pre / self.walks
            return self.pfr
        else:
            return 0

    def get_af(self):
        pass

    def save_mongo(self):
        pass
