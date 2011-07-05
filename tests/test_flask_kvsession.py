#!/usr/bin/env python
# coding=utf8

import sys

if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest

import time

from flaskext.kvsession import generate_session_key


class TestGenerateSessionKey(unittest.TestCase):
    def test_id_well_formed(self):
        for i in xrange(0,100):
            key = generate_session_key(time.time())

            self.assertRegexpMatches(key, r'^[0-9a-f]+_[0-9a-f]+$')

    def test_non_expiring_id_has_timestamp_0(self):
        key = generate_session_key()
        id, timestamp = key.split('_')

        self.assertEqual(int(timestamp), 0)

    def test_timestamp_set_properly(self):
        time = 0x823aC

        key = generate_session_key(expires=time)
        id, timestamp = key.split('_')

        self.assertEqual(timestamp, '823ac')

    def test_ids_generated_unique(self):
        ids = set()

        for i in xrange(0,10**5):
            id, timestamp = generate_session_key().split('_')

            self.assertNotIn(id, ids)
            ids.add(id)
