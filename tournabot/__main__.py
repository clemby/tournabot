from twisted.internet import reactor
import tournabot


try:
    tournabot.load()
except Exception as e:
    print(e)

channel = None
nickname = None

bot_config = tournabot.state.get('bot')
if bot_config:
    channel = bot_config.get('channel')
    nickname = bot_config.get('nick')

channel = channel or '#clembtest'
nickname = nickname or 'tournabot'

if type(channel) is unicode:
    channel = channel.encode('utf-8')
if type(nickname) is unicode:
    nickname = nickname.encode('utf-8')

print("connecting to {}".format(channel))
reactor.connectTCP(
    'irc.freenode.org',
    6667,
    tournabot.BotFactory(channel, nickname)
)
reactor.run()
