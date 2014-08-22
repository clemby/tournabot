#!/usr/bin/env python

from __future__ import print_function, division

from datetime import datetime
from dateutil import parser
import json

from twisted.internet import protocol
from twisted.words.protocols import irc
import pytz


state = {
    'tournament': {
        'team_size_limit': float('inf')
    },
    'bot': {
        'nick': 'tournabot',
        'sassy': False,
    },
    'teams': {},
    'matches': {},
    'unconfirmed_results': {},
}


state_file = 'records.json'
cmd_prefix = '.'


def save():
    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)


def load():
    with open(state_file, 'r') as f:
        global state
        state = json.load(f)


def timedelta_fmt(td):
    """
    Format a timedelta.

    :returns: a string in the format "DD days, HH:MM:SS" if the timedelta is
    greater than one day; otherwise "HH:MM:SS".

    """
    days = td.days
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if days > 0:
        return '{} days, {} hours, {} minutes'.format(
            days, hours, minutes, seconds)
    if hours > 0:
        return '{} hours, {} minutes, {} seconds'.format(hours, minutes,
                                                         seconds)
    if minutes > 0:
        return '{} minutes, {} seconds'.format(minutes, seconds)
    return '{} seconds'.format(seconds)


def time_difference(utc_now, time_str):
    if time_str is None:
        return ''
    try:
        time = parser.parse(time_str)
    except Exception:
        return ''
    return timedelta_fmt(time - utc_now)


def register(bot, user, chan, args):
    """
    Register a team.

    Expects eg.

        .register

    (for 1v1 tournament) or

        .register team_name member1 member2 ...

    for a tournament with multiplayer teams.

    """
    player_name = user.split('!')[0]
    if state['tournament']['team_size_limit'] == 1:
        if args:
            bot.say(chan, 'Expected no arguments (1v1 tournament)')
            return
        members = [player_name]
        team_name = player_name
    else:
        if not args:
            bot.say(
                chan,
                'Expected <teamname> <member> [member [... member]]'
                ' (multiplayer tournament)'
            )
            return
        team_name = args[0]
        members = args[1:]

    team = state['teams'].get(team_name)

    if team is not None:
        bot.say(chan,
                'Team {} already registered by {}! Current members: {}'.format(
                    team_name, team['creator'], ','.join(team['members'])))
        return

    create_team(name=team_name, members=members, creator=player_name)
    bot.say(
        chan,
        'Team {} successfully registered by {} with members {}. '
        'Thanks for participating!'.format(team_name, player_name, members)
    )


def create_team(name, members, creator):
    state['teams'][name] = {
        'members': members,
        'creator': creator,
        'games': 0,
        'wins': 0,
        'losses': 0,
        'draws': 0,
        'attended': 0,
        'forfeited': 0,
    }


def claim_result(bot, user, chan, args):
    """
    Report a game result.

    Any user can report the result. Required format is eg.

        .result match_id winning_team_name

    """
    if len(args) != 2:
        bot.say(chan, 'Expected: <command> <match-id> <winning-team-name>')
        return

    match_name, team_name = args
    match = state['matches'].get(match_name)
    team = state['teams'].get(team_name)
    if match is None:
        bot.say(chan, 'Unable to find match {}'.format(match_name))
        return
    if team is None:
        bot.say(chan, 'Unable to find team {}'.format(team_name))
        return

    state['unconfirmed_results'][match_name] = team_name
    result(bot, user, chan, args)


def result(bot, user, chan, args):
    """
    Report a game result.

    Required format is eg.

        .confirm match_id winning_team_name

    Automatically confirms the result if the reporting user is a member of one
    of the losing teams.

    """
    player = user.split('!')[0]
    if len(args) != 2:
        bot.say(chan, 'Expected: <command> <match-id> <winning-team-name>')
        return

    all_teams = state['teams']
    all_unconfirmed_results = state['unconfirmed_results']
    all_matches = state['matches']

    match_name, winning_team_name = args
    match = all_matches.get(match_name)
    if match is None:
        bot.say(chan, 'Unable to find match {}'.format(match_name))
        return
    team = all_teams.get(winning_team_name)
    if team is None:
        bot.say(chan, 'Unable to find team {}'.format(winning_team_name))
        return

    all_unconfirmed_results[match_name] = winning_team_name

    player_is_loser = False
    losing_teams = [
        all_teams[name] for name in match['teams'] if name != winning_team_name
    ]
    for losing_team in losing_teams:
        if player in losing_team['members']:
            player_is_loser = True
            break

    if not player_is_loser:
        bot.say(chan, 'Result must be confirmed by a loser in the match')
        return

    close_match(match, winning_team_name, losing_teams)
    bot.say(chan, '{match} won by {team}. Congratulations!'.format(
        match=match['id'], team=winning_team_name))


def close_match(match, winner_name, losing_teams=None):
    """
    Close a match entry.

    - Sets the winner of the match;
    - increments the appropriate counts (eg. win/lose) for involved teams;
    - updates the next match's teams (if appropriate);
    - removes any unconfirmed results for this match.

    """
    all_teams = state['teams']
    if losing_teams is None:
        losing_teams = [
            all_teams[name] for name in match['teams'] if name != winner_name
        ]

    match['winner'] = winner_name
    for losing_team in losing_teams:
        losing_team['games'] += 1
        losing_team['losses'] += 1
        losing_team['attended'] += 1

    winning_team = all_teams[winner_name]
    winning_team['games'] += 1
    winning_team['wins'] += 1
    winning_team['attended'] += 1

    next_match_name = match['next']
    if next_match_name is not None:
        next_match = state['matches'][next_match_name]
        next_match['teams'].append(winner_name)

    # Remove any unconfirmed results for this match, if any.
    state['unconfirmed_results'].pop(match['id'], None)


def add_match(name, time=None, teams=[], next_id=None, winner=None):
    """Add a match entry."""
    team_names = [
        team if isinstance(team, str) else team['id']
        for team in teams
    ]
    state['matches'][name] = {
        'id': name,
        'next': next_id,
        'winner': winner,
        'teams': team_names,
        'time': time,
    }


def remaining(bot, user, chan, args):
    """Show remaining matches."""
    matches = [
        match for match in state['matches'].values()
        if match['winner'] is None
    ]

    def order_with_nonentries_last(x, y):
        time_x = x.get('time')
        if time_x is None:
            return 1
        time_y = y.get('time')
        if time_y is None:
            return -1
        return cmp(time_x, time_y)

    matches.sort(order_with_nonentries_last)
    bot.say(chan, 'Remaining matches:')

    utc_now = datetime.utcnow().replace(tzinfo=pytz.utc)
    for match in matches:
        teams = match.get('teams') or []
        minimum_teams = state['tournament'].get('match_size_minimum')
        if minimum_teams:
            teams.extend(['TBA'] * (minimum_teams - len(teams)))
        teams_str = ' vs. '.join(teams)

        match_time = match.get('time')
        if match_time:
            timeleft = time_difference(utc_now, match_time)
            time_str = str(timeleft) if timeleft else 'Pending'
        else:
            time_str = 'Pending'
        bot.say(chan, '{name} [{time}]: {teams}'.format(
            name=match['id'], time=time_str, teams=teams_str))


def reload_state(bot, user, chan, args):
    load()


def rules(bot, user, chan, args):
    rules = state.get('rules')
    if rules:
        bot.say(chan, 'Tournament rules:')
        for rule in rules:
            bot.say(chan, rule)
    else:
        bot.say(chan, 'There are no rules!')


def unconfirmed(bot, user, chan, args):
    unconfirmed = state.get('unconfirmed_results')
    if unconfirmed:
        bot.say(chan, 'Unconfirmed results:')
        for key, winner in unconfirmed.items():
            bot.say(chan, '{} won by {}'.format(key, winner))
    else:
        bot.say(chan, 'There are no unconfirmed results')


def show_help(bot, user, chan, args):
    bot.say(chan, 'Supported commands:')
    bot.say(chan, '  ' + ' '.join(
        '%s%s' % (cmd_prefix, k) for k in cmds.keys()))


cmds = {
    'register': register,
    'help': show_help,
    'result': result,
    'remaining': remaining,
    'reload': reload_state,
    'rules': rules,
    'unconfirmed': unconfirmed,
}


class Bot(irc.IRCClient):
    @property
    def nickname(self):
        return self.factory.nickname

    def signedOn(self):
        print('Signed on as %s.' % self.nickname)
        self.join(self.factory.channel)

    def joined(self, channel):
        print('Joined %s.' % channel)

    def say(self, channel, msg):
        if type(msg) is unicode:
            msg = msg.encode('utf-8')
        irc.IRCClient.say(self, channel, msg)

    def privmsg(self, user, channel, msg):
        if not msg.startswith(cmd_prefix):
            return

        parts = msg[len(cmd_prefix):].split(' ')
        cmd = cmds.get(parts[0])

        if not cmd:
            if state.get('bot') and state['bot'].get('sassy'):
                self.say(channel, 'Eh?')
            return

        cmd(self, user, channel, parts[1:])
        save()


class BotFactory(protocol.ClientFactory):
    protocol = Bot

    def __init__(self, channel, nickname):
        self.channel = channel
        self.nickname = nickname

    def clientConnectionLost(self, connector, reason):
        print('Connection lost. Reason: %s' % reason)
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print('Connection failed. Reason: %s' % reason)
        connector.connect()
