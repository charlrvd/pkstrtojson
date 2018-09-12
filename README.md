# pkstrtojson

## Description

Simple script to parse a log file from pokerstart to a json document.
The goal is to store all json history to a database and then run analytics on it for statistics.
Develop a dashboard to watch graph of hands history bankroll evolution and poker stats.

Other possibility when found a good way to stream the history directly when written is to
develop a dynamic dashboard visible while playing.

### Getting started

Quick parse of a game logfile:
```python
>>> from pokerstarsgame import Pokerstarsgame
>>> with open('hands/HH20180626_T2342391818.txt', 'r') as fl:
...     lines = fl.read()
...     fl.closed
... 
False
>>> gamelist = [x for x in lines.split('\n')]
>>> game = Pokerstarsgame(gamelist)
>>> game.get_game_infos()
'{"hands": [], "entry_price": 1.0, "_id": "T2342391818"}'
```

### backend mongodb

```bash
docker run --name pokermongo -v $(pwd)/data:/data/db -p 81:27017 -d mongo
```

#### Save data to mongo

To add
