# -*- coding: utf-8 -*-
"""
    flaskext.kvsession
    ~~~~~~~~~~~~~~~~~~

    Drop-in replacement module for Flask sessions that uses a
    :class:`simplekv.KeyValueStore` as a
    backend for server-side sessions.
"""


import calendar
from datetime import datetime
try:
    import json
except ImportError:
    import simplejson as json
import hmac
from random import SystemRandom
import re

from itsdangerous import Signer, BadSignature


try:
    from flask.sessions import SessionMixin, SessionInterface
except ImportError:
    # pre-0.8, these are replacements for the new session interface
    # see http://flask.pocoo.org/snippets/52/
    class SessionInterface(object):
        pass

    class SessionMixin(object):
        def _get_permanent(self):
            return self.get('_permanent', False)

        def _set_permanent(self, value):
            self['_permanent'] = bool(value)

        permanent = property(_get_permanent, _set_permanent)
        del _get_permanent, _set_permanent

        new = False
        modified = True


class SessionID(object):
    def __init__(self, id, created=None):
        if None == created:
            created = datetime.utcnow()

        self.id = id
        self.created = None

    def has_expired(self, lifetime, now=None):
        now = now or datetime.utcnow()
        return now > self.created + lifetime

    def serialize(self):
        return '%x_%x' % (self.id,
                          calendar.timegm(self.created.utctimetuple()))

    @classmethod
    def unserialize(self, string):
        id_s, created_s = string.split('_')
        return cls(int(id_s, 16), datetime.fromtimestamp(int(created_s, 16)))


class KVSession(dict, SessionMixin):
    def destroy(self):
        """Destroys a session completely, by deleting all keys and removing it
        from the internal store immediately.

        This allows removing a session for security reasons, e.g. a login
        stored in a session will cease to exist if the session is destroyed.
        """
        for k in self.keys():
            del self[k]

        self.store.delete(self.sid_s)

        self.modified = False
        self.new = False


class KVSessionInterface(SessionInterface):
    def __init__(self, store, random_source=None):
        self.store = store
        self.random_source = random_source or SystemRandom()

    def open_session(self, app, request):
        key = self.app.secret_key

        if key is not None:
            session_cookie = request.cookies.get('SESSION_COOKIE_NAME', None)

            if session_cookie:
                s = Signer(secret_key)

                try:
                    # restore the cookie, if it has been manipulated,
                    # we will find out here
                    sid_s = s.unsign(session_cookie)
                    sid = SessionID.unserialize(sid_s)

                    if sid.has_expired(
                        app.config['PERMANENT_SESSION_LIFETIME']):
                        return None #  the session has expired, no need to even
                                    #  check if it exists

                    # retrieve from store
                    s = KVSession(json.loads(self.store.get(sid_s)))
                    s.sid_s = sid_s
                except (BadSignature, KeyError):
                    # either the cookie was manipulated or we did not find the
                    # session in the backend.
                    pass
            else:
                s = KVSession() #  create an empty session
                s.new = True

            s.store = self.store
            return s

    def save_session(self, app, session, response):
        if session.modified:
            # create a new session id
            # we do this everytime to avoid session fixation
            sid = SessionID(
                self.random_source.getrandbits(app.config['SESSION_KEY_BITS']))

            sid_s = sid.serialize()

            if not session.new:
                # remove the old session
                self.store.delete(session.sid_s) # store session data
            self.store.put(sid_s, json.dumps(session))

            # save sid_s in session cookie
            cookie_data = Signer(app.secret_key).sign(sid_s)

            response.set_cookie(key=app.config['SESSION_COOKIE_NAME'],
                                value=cookie_data,
                                expires=self.get_expiration_time(app, session),
                                domain=self.get_cookie_domain(app))


class KVSessionExtension(object):
    """Activates Flask-KVSession for an application.

    :param session_kvstore: An object supporting the
                            `simplekv.KeyValueStore` interface that session
                            data will be store in.
    :param app: The app to activate. If not `None`, this is essentially the
                same as calling :meth:`init_app` later."""
    key_regex = re.compile('^[0-9a-f]+_[0-9a-f]+$')

    def __init__(self, session_kvstore, app=None, random_source=None):
        self.session_kvstore = session_kvstore
        self.random_source = random_source

        if app:
            self.init_app(app)

    def cleanup_sessions(self):
        """Removes all expired session from the store.

        Periodically, this function should be called to remove sessions from
        the backend store that have expired, as they are not removed
        automatically.

        This function retrieves all session keys, checks they are older than
        ``PERMANENT_SESSION_LIFETIME`` and if so, removes them.

        Note that no distinction is made between non-permanent and permanent
        sessions."""
        for key in self.session_kvstore.keys():
            m = self.key_regex.match(key)
            now = datetime.utcnow()
            if m:
                # read id
                sid = SessionID.unserialize(key)

                # remove if expired
                if sid.has_expired(
                    self.app.config['PERMANENT_SESSION_LIFETIME'],
                    now
                ):
                    self.session_kvstore.delete(key)

    def init_app(self, app):
        """Initialize application and KVSession.

        This will replace the session management of the application with
        Flask-KVSession's."""
        self.app = app
        app.config.setdefault('SESSION_KEY_BITS', 64)

        if not hasattr(app, 'session_interface'):
            app.open_session = lambda r: \
                app.session_interface.open_session(app, r)
            app.save_session = lambda s, r: \
                app.session_interface.save_session(app, s, r)

        app.session_interface = KVSessionInterface(self.store,
                                                   self.random_source)
