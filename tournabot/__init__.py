from twisted.internet import reactor

import tournabot
from tournabot import (
    state, state_file, tournament_is_1v1, cmd_prefix, save, load, register,
    create_team, result, close_match, add_match, show_help, Bot, BotFactory)


if __name__ == '__main__':
    try:
        load()
    except Exception as e:
        print(e)
    reactor.connectTCP('irc.freenode.org', 6667, BotFactory('#clembtest'))
    reactor.run()
