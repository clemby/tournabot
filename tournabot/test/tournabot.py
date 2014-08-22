import unittest
from mock import Mock
from datetime import datetime

from .. import tournabot


class TournabotTestCase(unittest.TestCase):
    def setUp(self):
        self.bot = Mock()
        self.chan = Mock()
        self.player_name = 'PlayerName'
        self.user = self.player_name + '!~client@loc.at.ion'
        self.team_args = []
        tournabot.state = {
            'teams': {},
            'matches': {},
            'unconfirmed_results': {},
        }


class RegisterSinglePlayerTeam(TournabotTestCase):
    def setUp(self):
        TournabotTestCase.setUp(self)
        tournabot.state['tournament'] = {
            'team_size_limit': 1
        }
        self.team_name = self.player_name
        self.team_key = self.team_name

    def test_creates_team(self):
        tournabot.register(self.bot, self.user, self.chan, self.team_args)
        print('state', tournabot.state)
        self.assertTrue(self.team_name in tournabot.state['teams'])
        self.assertTrue(
            isinstance(tournabot.state['teams'].get(self.team_name), dict)
        )

    def test_sets_team_counts_to_zero(self):
        """Check the wins, losses, etc. counts are zero."""
        tournabot.register(self.bot, self.user, self.chan, self.team_args)
        registered = tournabot.state['teams'][self.team_name]
        for key in ['attended', 'forfeited', 'draws', 'wins', 'losses',
                    'games']:
            self.assertEqual(registered.get(key), 0)

    def test_sets_members(self):
        tournabot.register(self.bot, self.user, self.chan, self.team_args)
        registered = tournabot.state['teams'][self.team_name]
        self.assertEqual(registered.get('members'), ['PlayerName'])

    def test_sets_creator(self):
        tournabot.register(self.bot, self.user, self.chan, self.team_args)
        registered = tournabot.state['teams'][self.team_key]
        self.assertEqual(registered.get('creator'), self.team_name)

    def test_1v1_args_error(self):
        """Check for an error message when input is incorrect."""
        tournabot.register(self.bot, self.user, self.chan, [
            'erroneous', 'extra', 'args'
        ])
        pass


class RegisterMultiPlayerTeam(TournabotTestCase):
    def setUp(self):
        TournabotTestCase.setUp(self)
        tournabot.state['tournament'] = {
            'team_size_limit': 4
        }
        self.team_name = 'Team Name'
        self.team_key = self.team_name
        self.team_members = ['Member1', 'MeMbAr2', 'mMmMMM MMM']
        self.team_args = [self.team_name] + self.team_members

    def test_creates_team(self):
        tournabot.register(self.bot, self.user, self.chan, self.team_args)
        self.assertTrue(self.team_name in tournabot.state['teams'])
        self.assertTrue(
            isinstance(tournabot.state['teams'].get(self.team_key), dict)
        )

    def test_sets_team_counts_to_zero(self):
        """Check the wins, losses, etc. counts are zero."""
        tournabot.register(self.bot, self.user, self.chan, self.team_args)
        registered = tournabot.state['teams'][self.team_key]
        for key in ['attended', 'forfeited', 'draws', 'wins', 'losses',
                    'games']:
            self.assertEqual(registered.get(key), 0)

    def test_sets_members(self):
        tournabot.register(self.bot, self.user, self.chan, self.team_args)
        registered = tournabot.state['teams'][self.team_key]
        self.assertEqual(registered.get('members'), self.team_members)

    def test_sets_creator(self):
        tournabot.register(self.bot, self.user, self.chan, self.team_args)
        registered = tournabot.state['teams'][self.team_key]
        self.assertEqual(registered.get('creator'), self.player_name)


class Result(TournabotTestCase):
    def setUp(self):
        TournabotTestCase.setUp(self)
        tournabot.create_team(name='TeamA', members=['A1', 'A2'], creator='A1')
        tournabot.create_team(name='TeamB', members=['B1', 'B2'], creator='B1')
        tournabot.add_match(name='Final', teams=['TeamA', 'TeamB'])
        self.match = tournabot.state['matches']['Final']

        self.winner_name = 'A2'
        self.winner = self.winner_name + '!~client@loc.at.ion'
        self.loser_name = 'B2'
        self.loser = self.loser_name + '!~client@loc.at.ion'

    def test_error_if_invalid_args(self):
        pass

    def test_error_if_invalid_team(self):
        pass

    def test_error_if_invalid_match(self):
        pass

    def test_does_not_write_if_user_is_not_loser(self):
        tournabot.result(self.bot, self.winner, self.chan, ['Final', 'TeamA'])
        self.assertEqual(self.match.get('winner'), None)

    def test_adds_unconfirmed_result_if_user_is_not_loser(self):
        tournabot.result(self.bot, self.winner, self.chan, ['Final', 'TeamA'])
        unconfirmed_results = tournabot.state['unconfirmed_results']
        self.assertIn('Final', unconfirmed_results)
        self.assertEqual(unconfirmed_results['Final'], 'TeamA')

    def test_writes_result_if_user_is_loser(self):
        tournabot.result(self.bot, self.loser, self.chan, ['Final', 'TeamA'])
        self.assertEqual(self.match.get('winner'), 'TeamA')

    def test_removes_unconfirmed_result_if_user_is_loser(self):
        unconfirmed = tournabot.state['unconfirmed_results']
        unconfirmed['Final'] = 'TeamA'
        tournabot.result(self.bot, self.loser, self.chan, ['Final', 'TeamA'])
        self.assertNotIn('Final', unconfirmed)


class AddMatch(TournabotTestCase):
    def setUp(self):
        tournabot.state['matches'].pop('TheMatch', None)

    def test_adds_entry(self):
        tournabot.add_match(name='TheMatch',
                            teams=['first_team', 'second_team'])
        self.assertIn('TheMatch', tournabot.state['matches'])

    def test_adds_empty_teams_list_by_default(self):
        tournabot.add_match(name='TheMatch')
        self.assertEqual(tournabot.state['matches']['TheMatch'].get('teams'),
                         [])

    def test_can_set_next_match_id(self):
        tournabot.add_match(name='TheMatch',
                            teams=['first_team', 'second_team'],
                            next_id='final')
        self.assertEqual(tournabot.state['matches']['TheMatch'].get('id'),
                         'TheMatch')

    def test_can_set_winner(self):
        tournabot.add_match(name='TheMatch',
                            teams=['first_team', 'second_team'],
                            winner='first_team')
        self.assertEqual(tournabot.state['matches']['TheMatch'].get('winner'),
                         'first_team')


class CloseMatch(TournabotTestCase):
    def setUp(self):
        self.match_id = 'Semifinal'
        self.next_match_id = 'Final'
        tournabot.add_match(name=self.match_id, teams=['team1', 'team2'],
                            next_id=self.next_match_id)
        tournabot.add_match(name=self.next_match_id)
        self.match = tournabot.state['matches'][self.match_id]

        tournabot.tournament_is_1v1 = False
        tournabot.state['teams'] = {
            'team1': {
                'attended': 0,
                'draws': 0,
                'wins': 0,
                'games': 0,
                'losses': 0,
                'forfeited': 0,
                'members': ['player1a', 'player1b'],
            },
            'team2': {
                'attended': 0,
                'draws': 0,
                'wins': 0,
                'games': 0,
                'losses': 0,
                'forfeited': 0,
                'members': ['player2a', 'player2b'],
            },
        }

    def test_sets_winner(self):
        tournabot.close_match(match=self.match, winner_name='team1')
        self.assertEqual(
            tournabot.state['matches'][self.match_id].get('winner'),
            'team1')

    def test_increments_winning_team_counts(self):
        tournabot.close_match(match=self.match, winner_name='team1')
        team = tournabot.state['teams']['team1']

        self.assertEqual(team['attended'], 1)
        self.assertEqual(team['draws'], 0)
        self.assertEqual(team['wins'], 1)
        self.assertEqual(team['losses'], 0)
        self.assertEqual(team['forfeited'], 0)

    def test_increments_losing_team_counts(self):
        tournabot.close_match(match=self.match, winner_name='team1')
        team = tournabot.state['teams']['team2']

        self.assertEqual(team['attended'], 1)
        self.assertEqual(team['draws'], 0)
        self.assertEqual(team['wins'], 0)
        self.assertEqual(team['losses'], 1)
        self.assertEqual(team['forfeited'], 0)

    def test_removes_unconfirmed_results(self):
        tournabot.state['unconfirmed_results'][self.match_id] = 'team1'
        tournabot.close_match(match=self.match, winner_name='team1')

    def test_updates_teams_in_next_match(self):
        tournabot.close_match(match=self.match, winner_name='team1')
        self.assertIn(
            'team1',
            tournabot.state['matches'][self.next_match_id]['teams']
        )


class RemainingMatches(TournabotTestCase):
    def setUp(self):
        self.days = 20
        self.hours = 11
        self.minutes = 36
        self.seconds = 52
        self.first = datetime(2014, 1, 1, 0, 0, 0, 0)
        self.second = datetime(2014, 1, 1 + self.days, self.hours,
                               self.minutes, self.seconds)
        self.timedelta = self.second - self.first
        self.match_date_str = str(self.second)

    def test_timedelta_fmt_function_with_days(self):
        second = datetime(2014, 1, 1 + self.days, self.hours, self.minutes,
                          self.seconds)
        first = datetime(2014, 1, 1, 0, 0, 0)
        self.assertEqual(
            tournabot.timedelta_fmt(second - first),
            '20 days, 11 hours, 36 minutes, 52 seconds'
        )

    def test_timedelta_fmt_function_with_hours(self):
        second = datetime(2014, 1, 1, self.hours, self.minutes, self.seconds)
        first = datetime(2014, 1, 1, 0, 0, 0)
        self.assertEqual(
            tournabot.timedelta_fmt(second - first),
            '11 hours, 36 minutes, 52 seconds'
        )

    def test_timedelta_fmt_function_with_minutes(self):
        second = datetime(2014, 1, 1, 0, self.minutes, self.seconds)
        first = datetime(2014, 1, 1, 0, 0, 0)
        self.assertEqual(
            tournabot.timedelta_fmt(second - first),
            '36 minutes, 52 seconds'
        )

    def test_timedelta_fmt_function_with_seconds(self):
        second = datetime(2014, 1, 1, 0, 0, self.seconds)
        first = datetime(2014, 1, 1, 0, 0, 0)
        self.assertEqual(
            tournabot.timedelta_fmt(second - first),
            '52 seconds'
        )
