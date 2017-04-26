import os
import sys
import json
import shutil
import random
import tempfile

import mock

from datetime import datetime, timedelta

from twisted.internet import reactor, task, defer
from twisted.trial import unittest

from ooni.utils import generate_filename, randomSTR, randomDate, LONG_DATE
from ooni.tests.bases import ConfigTestCase

from ooni.deck.store import DeckStore, DEFAULT_DECKS
from ooni.agent.scheduler import ScheduledTask, DidNotRun
from ooni.agent.scheduler import FileSystemlockAndMutex
from ooni.agent.scheduler import SchedulerService

class TestScheduler(unittest.TestCase):
    def test_scheduled_task(self):
        schedule = "@daily"
        identifier = "dummy"
        scheduler_directory = tempfile.mkdtemp()
        scheduled_task = ScheduledTask(schedule=schedule,
                                       identifier=identifier,
                                       scheduler_directory=scheduler_directory
        )
        self.assertEqual(scheduled_task.should_run, True)
        self.assertFailure(scheduled_task.run(), NotImplementedError)
        self.assertEqual(scheduled_task.should_run, True)
        self.assertFalse(os.path.islink(os.path.join(scheduler_directory, identifier + '.lock')))
        shutil.rmtree(scheduler_directory)

    @defer.inlineCallbacks
    def test_call_twice_scheduled_task(self):
        """
        If we call the scheduled task twice in a row the second time it will not run.
        Tests for possible race conditions.
        """
        scheduler_directory = tempfile.mkdtemp()
        spam_path = os.path.join(scheduler_directory, 'spam.txt')
        class DummyST(ScheduledTask):
            def task(subself):
                self.assertTrue(os.path.islink(os.path.join(scheduler_directory, subself.identifier + '.lock')))
                with open(spam_path, 'a') as out_file:
                    out_file.write("I ran\n")

        schedule = "@daily"
        identifier = "dummy"
        dummy_st = DummyST(schedule=schedule,
                           identifier=identifier,
                           scheduler_directory=scheduler_directory
        )

        dummy_st.run()
        yield self.assertFailure(dummy_st.run(), DidNotRun)

        with open(spam_path) as in_file:
            self.assertEqual(len(in_file.readlines()), 1)

        self.assertEqual(dummy_st.should_run, False)
        self.assertFalse(os.path.islink(os.path.join(scheduler_directory, identifier + '.lock')))
        shutil.rmtree(scheduler_directory)

    def test_thundering_herd(self):
        lockno = int(os.getenv('TTH_LOCKNO', str(sys.getrecursionlimit() + 16)))
        scheduler_directory = tempfile.mkdtemp()
        counter = os.path.join(scheduler_directory, 'counter')
        class DummyST(ScheduledTask):
            @defer.inlineCallbacks
            def task(subself):
                self.assertTrue(os.path.islink(os.path.join(scheduler_directory, subself.identifier + '.lock')))
                with open(counter, 'w+') as fd:
                    data = fd.read()
                    fd.seek(0)
                    if not data:
                        fd.write('1')
                        yield task.deferLater(reactor, 1, lambda: 42)
                    else:
                        self.assertTrue(False) # should be unreachable due to schedule
        identifier = "dummy"
        dummy_st = DummyST(schedule='@daily', identifier=identifier, scheduler_directory=scheduler_directory)
        dl = defer.DeferredList([dummy_st.run() for i in xrange(lockno)], consumeErrors=True)
        @dl.addBoth
        def so_what(results):
            self.assertFalse(os.path.islink(os.path.join(scheduler_directory, identifier + '.lock')))
            self.assertEqual(results[0], (True, None)) # do not expect to get `42` here
            for okflag, ex in results[1:]:
                self.assertEqual(okflag, False)
                ex.trap(DidNotRun)
            self.assertEqual(dummy_st.should_run, False)
            with open(counter, 'r') as fd:
                self.assertEqual(fd.read(), '1')
            shutil.rmtree(scheduler_directory)
        return dl

    @defer.inlineCallbacks
    def test_filesystem_lock_and_mutex(self):
        lock_dir = tempfile.mkdtemp()
        lock_path = os.path.join(lock_dir, 'lock')

        lock = FileSystemlockAndMutex(lock_path)

        os.symlink(str(2**30), lock_path) # that's non-existend PID for sure

        lock_count = 100
        unlock_count = 0
        dl = []
        for i in range(lock_count):
            dl.append(lock.acquire())
            if random.choice([0, 1]) == 0:
                unlock_count += 1
                lock.release()

        for i in range(lock_count - unlock_count):
            lock.release()

        yield defer.DeferredList(dl)
        self.assertFalse(lock.locked)

        shutil.rmtree(lock_dir)

def random_measurement_name(start_date=None, end_date=None):
    # By default we use as start date something in the past 6 days and end
    # date today.
    if start_date is None:
        start_date = datetime.now() - timedelta(days=6)
    if end_date is None:
        end_date = datetime.now()

    test_details = dict(
        test_name=random.choice(['http_invalid_request_line',
                                 'web_connectivity',
                                 'http_header_field_manipulation',
                                 'vanilla_tor',
                                 'new_test_name']),
        probe_cc=randomSTR(2, num=False), # XXX this should be a valid CC
        probe_asn='AS'+str(random.randint(0, 2**16)),
        test_start_time=randomDate(start_date, end_date).strftime(LONG_DATE)
    )
    return generate_filename(test_details)

def get_measurement_header():
    return {
        'probe_asn': 'AS'+str(random.randint(0, 2**16)),
        'probe_cc': randomSTR(2, num=False),
        'probe_ip': '127.0.0.1',
        'probe_city': None,
        'software_name': 'ooniprobe',
        'software_version': '0.0.0',
        'options': {},
        'annotations': {},
        'data_format_version': '0.2.0',
        'test_name': 'dummy',
        'test_version': '0.0.0',
        'test_helpers': {},
        'test_start_time': '2016-01-01 01:01:01',
        'test_runtime': 0.1,
        'input_hashes': [],
        'report_id': randomSTR(100),
        'test_keys': {},
        'input': ''
    }

def write_dummy_measurements(fh, size=100):
    """
    :param fh: an open file handle
    :param size: size of the measurements in bytes to write
    :return: The actual size that has been written.
    """
    written_size = 0
    while written_size < size:
        entry = get_measurement_header()
        entry['test_keys']['data'] = randomSTR(int(size / 10))
        data = json.dumps(entry)
        written_size += len(data)
        fh.write(data)
    return written_size


DUMMY_DECK = """
---
name: Dummy deck
description: Dummy deck
schedule: "@daily"
tasks:
- name: Dummy bar
  ooni:
    test_name: http_header_field_manipulation
"""

class TestSchedulerService(ConfigTestCase):
    def setUp(self):
        super(TestSchedulerService, self).setUp()

        self.config_patcher = mock.patch('ooni.agent.scheduler.config')
        self.config_m_patcher = mock.patch('ooni.measurements.config')
        self.config_mock = self.config_patcher.start()
        self.config_m_mock = self.config_m_patcher.start()

        self.scheduler_directory = tempfile.mkdtemp()
        self.config_mock.scheduler_directory = self.scheduler_directory

        self.running_path = tempfile.mkdtemp()
        self.config_mock.running_path = self.running_path

        self.config_mock.is_initialized.return_value = True

        self.config_mock.basic.measurement_quota = '100M'

        self.measurements_directory = tempfile.mkdtemp()
        self.config_mock.measurements_directory = self.measurements_directory
        self.create_dummy_measurements()

        self.config_m_mock.measurements_directory = self.measurements_directory

        self.decks_enabled_directory = tempfile.mkdtemp()
        self.decks_available_directory = tempfile.mkdtemp()

        self.deck_store = DeckStore(
            available_directory=self.decks_available_directory,
            enabled_directory=self.decks_enabled_directory
        )

        self.mock_deck = mock.MagicMock()
        self.deck_store.get = lambda deck_id: self.mock_deck
        self.mock_deck.setup.return_value = defer.succeed(None)
        self.mock_deck.run.return_value = defer.succeed(None)

        for deck_name in DEFAULT_DECKS:
            with open(os.path.join(self.decks_available_directory,
                                   '%s.yaml' % deck_name), 'w') as out_file:
                out_file.write(DUMMY_DECK)

    def create_dummy_measurements(self, count=10, size=10*1024):
        for _ in range(count):
            dir_path = os.path.join(
                self.measurements_directory,
                random_measurement_name()
            )
            os.mkdir(dir_path)
            with open(os.path.join(dir_path, "measurements.njson"), 'w') as fh:
                write_dummy_measurements(fh, float(size) / float(count))

    def tearDown(self):
        super(TestSchedulerService, self).tearDown()

        shutil.rmtree(self.measurements_directory)
        shutil.rmtree(self.scheduler_directory)
        shutil.rmtree(self.running_path)

        self.config_patcher.stop()
        self.config_m_patcher.stop()

    @mock.patch('ooni.agent.scheduler.resources')
    @mock.patch('ooni.agent.scheduler.probe_ip')
    @mock.patch('ooni.agent.scheduler.input_store')
    @mock.patch('ooni.agent.scheduler.oonireport')
    def test_deck_run_twice(self, mock_resources, mock_probe_ip,
                            mock_input_store, mock_oonireport):
        mock_probe_ip.geodata['countrycode'] = 'ZZ'
        mock_probe_ip.lookup.return_value = defer.succeed(None)
        mock_probe_ip.resolveGeodata.return_value = defer.succeed(None)

        mock_resources.check_for_update.return_value = defer.succeed(None)

        mock_input_store.update.return_value = defer.succeed(None)

        mock_oonireport.upload_all.return_value = defer.succeed(None)

        mock_director = mock.MagicMock()
        d = defer.Deferred()
        dummy_clock = task.Clock()
        class FakeDatetime(datetime):
            @staticmethod
            def utcnow():
                return datetime(2000,1,1, 7,0,0) + timedelta(seconds=dummy_clock.seconds())
        with mock.patch('ooni.agent.scheduler.deck_store', self.deck_store), \
             mock.patch('ooni.agent.scheduler.datetime', FakeDatetime):
            scheduler_service = SchedulerService(
                director=mock_director,
                _reactor=dummy_clock
            )
            scheduler_service.startService()
            dummy_clock.advance(45)

            # these tasks were run before clock was pumped
            for t in scheduler_service._scheduled_tasks:
                self.assertIn(t.schedule, ('@daily', '@hourly'))
                with open(os.path.join(self.scheduler_directory, t.identifier)) as in_file:
                    self.assertEqual(in_file.read(), '2000-01-01T07:00:00Z')

            # that's leaping clock, it leads to immediate scheduling
            dummy_clock.advance(24 * 60 * 60)
            for t in scheduler_service._scheduled_tasks:
                with open(os.path.join(self.scheduler_directory, t.identifier)) as in_file:
                    self.assertEqual(in_file.read(), '2000-01-02T07:00:45Z')

            # nothing happens during an hour
            dummy_clock.advance(60 * 60 - 46)
            self.assertEqual(FakeDatetime.utcnow(), datetime(2000,1,2, 7,59,59))
            for t in scheduler_service._scheduled_tasks:
                with open(os.path.join(self.scheduler_directory, t.identifier)) as in_file:
                    self.assertEqual(in_file.read(), '2000-01-02T07:00:45Z')

            # that's ticking clock, it smears the load a bit
            dummy_clock.pump([1] * 1800)
            zero, hourly, daily = 0, 0, 0
            for t in scheduler_service._scheduled_tasks:
                with open(os.path.join(self.scheduler_directory, t.identifier)) as in_file:
                    if t.schedule == '@daily':
                        daily += 1
                        self.assertEqual(in_file.read(), '2000-01-02T07:00:45Z')
                    elif t.schedule == '@hourly':
                        hourly += 1
                        # `:[03]0Z` is caused by scheduler resolution & ticking one second a time
                        last_run = in_file.read()
                        self.assertRegexpMatches(last_run, '^2000-01-02T08:0.:[03]0Z$')
                        if last_run == '2000-01-02T08:00:00Z':
                            zero += 1
            self.assertGreater(hourly, 0)
            self.assertGreater(daily, 0)
            self.assertLess(zero, hourly)
            self.assertLessEqual(zero, 1) # should ALMOST never happen

            # leaping to the end of the day
            dummy_clock.advance((datetime(2000,1,2, 23,59,59) - FakeDatetime.utcnow()).total_seconds())
            for t in scheduler_service._scheduled_tasks:
                with open(os.path.join(self.scheduler_directory, t.identifier)) as in_file:
                    if t.schedule == '@daily':
                        self.assertEqual(in_file.read(), '2000-01-02T07:00:45Z')
                    elif t.schedule == '@hourly':
                        self.assertEqual(in_file.read(), '2000-01-02T23:59:59Z')

            # save ~30% of the testcase runtime while ticking through six hours
            for t in scheduler_service._scheduled_tasks[:]:
                if t.schedule == '@hourly':
                    scheduler_service.unschedule(t)

            # ticking through six hours
            dummy_clock.pump([random.uniform(0, 120) for i in xrange(6*60)])
            for t in scheduler_service._scheduled_tasks:
                with open(os.path.join(self.scheduler_directory, t.identifier)) as in_file:
                    # randomized clock kills 30s resolution of the scheduler
                    self.assertRegexpMatches(in_file.read(), '^2000-01-03T0[012]:..:..Z$')
            self.assertGreater(FakeDatetime.utcnow(), datetime(2000,1,3, 5,0,0)) # should be ~6:00

            # verify, that double-run does not happen even in case of reseeding (reboot/restart)
            dummy_clock.advance((datetime(2000,1,3, 23,59,59) - FakeDatetime.utcnow()).total_seconds())
            launches = {}
            while FakeDatetime.utcnow() < datetime(2000,1,4, 6,0,0):
                for t in scheduler_service._scheduled_tasks:
                    with open(os.path.join(self.scheduler_directory, t.identifier)) as in_file:
                        launches.setdefault(t.identifier, set())
                        launches[t.identifier].add(in_file.read())
                    self.assertLessEqual(t._smear_coef, 1.0)
                    t._smear_coef = random.random()
                dummy_clock.advance(random.uniform(0, 120))
            self.assertEqual(len(launches), len(scheduler_service._scheduled_tasks))
            self.assertEqual({k: len(v) for k, v in launches.iteritems()}, dict.fromkeys(launches.iterkeys(), 2))

            # We check that the run method of the deck was called twice
            # NB: That does NOT check that @daily task was called exactly twice
            self.mock_deck.run.assert_has_calls([
                mock.call(mock_director, from_schedule=True), mock.call(mock_director, from_schedule=True)
            ])
            d.callback(None)

        return d

    @mock.patch('ooni.agent.scheduler.resources')
    @mock.patch('ooni.agent.scheduler.probe_ip')
    @mock.patch('ooni.agent.scheduler.input_store')
    @mock.patch('ooni.agent.scheduler.oonireport')
    def test_disk_quota_cleanup(self, mock_resources, mock_probe_ip,
                                mock_input_store, mock_oonireport):

        mock_probe_ip.geodata['countrycode'] = 'ZZ'
        mock_probe_ip.lookup.return_value = defer.succeed(None)
        mock_probe_ip.resolveGeodata.return_value = defer.succeed(None)

        mock_resources.check_for_update.return_value = defer.succeed(None)

        mock_input_store.update.return_value = defer.succeed(None)

        mock_oonireport.upload_all.return_value = defer.succeed(None)

        self.config_mock.basic.measurement_quota = '1M'
        # We create 10MB of measurements
        self.create_dummy_measurements(count=10, size=1*1024*1024)
        measurement_count = len(os.listdir(self.measurements_directory))

        mock_director = mock.MagicMock()
        d = defer.Deferred()
        with mock.patch('ooni.agent.scheduler.deck_store', self.deck_store):

            dummy_clock = task.Clock()
            scheduler_service = SchedulerService(
                director=mock_director,
                _reactor=dummy_clock
            )
            scheduler_service.startService()
            dummy_clock.advance(30)

            now_time = datetime.utcnow()
            DT_FRMT = "%Y-%m-%dT%H:%M:%SZ"

            for t in scheduler_service._scheduled_tasks:
                with open(os.path.join(self.scheduler_directory,
                                       t.identifier)) as in_file:
                    dstr = datetime.strptime(in_file.read(),
                                             DT_FRMT).strftime("%Y-%m-%dT%H")
                    self.assertEqual(dstr, now_time.strftime("%Y-%m-%dT%H"))

            # Ensure there are less measurements than there were at the
            # beginning
            new_measurement_count = len(os.listdir(self.measurements_directory))
            self.assertGreater(measurement_count, new_measurement_count)

            d.callback(None)

        return d
