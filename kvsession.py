#!/usr/bin/env python
# coding=utf8

from flask.session import Session
from random import SystemRandom
import time

random_source = SystemRandom()


def generate_session_key(expires=None, bits=64):
    if not isinstance(expires, int):
        expires = time.mktime(expires.timetuple())
    elif not expires:
        expires = 0

    idbits = random_source.getrandbits(bits)

    return '%d_%d' % (idbits, expires)


def open_session(self, request):
    key = self.secret_key
    if key is not None:
        pass #  create or load session instance here


class KVSession(Session):
    def serialize(self, expires=None):
        # get session serialization
        sdata = super(KVSession, self).serialize(expires)

        # store sdata, receive key
        # only exceptions expected are ValueErrors, which should never happen
        # with proper key generation and IOErrors, which we do not want to
        # catch here
        key = self.store.put(data=sdata)

        return key

    @classmethod
    def unserialize(self, string, secret_key):
        key = string

        # load sdata from store
        try:
            string = self.store.get(key)
        except KeyError:
            # someone deleted the session
            pass

        # unserialize "normally"
        return super(KVSession, self).unserialize(string, secret_key)
