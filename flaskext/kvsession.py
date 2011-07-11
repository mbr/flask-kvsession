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
from werkzeug.datastructures import CallbackDict

try:
    from flask.sessions import SessionMixin, SessionInterface
except ImportError:
    # pre-0.8, these are replacements for the new session interface
    # see http://flask.pocoo.org/snippets/52/
    # FIXME: this code should be made legacy and a dependency for
    #        flask >= 0.8 added once it becomes stable
    class SessionInterface(object):
        def get_expiration_time(self, app, session):
            # copied from flask 0.8 source
            if session.permanent:
                return datetime.utcnow() + app.permanent_session_lifetime

        def get_cookie_domain(self, app):
            # copied from flask 0.8 source
            if app.config['SERVER_NAME'] is not None:
                return '.' + app.config['SERVER_NAME'].rsplit(':', 1)[0]

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
        self.created = created

    def has_expired(self, lifetime, now=None):
        now = now or datetime.utcnow()
        return now > self.created + lifetime

    def serialize(self):
        return '%x_%x' % (self.id,
                          calendar.timegm(self.created.utctimetuple()))

    @classmethod
    def unserialize(cls, string):
        id_s, created_s = string.split('_')
        return cls(int(id_s, 16),
                   datetime.utcfromtimestamp(int(created_s, 16)))


class KVSession(CallbackDict, SessionMixin):
    def __init__(self, initial=None):
        def _on_update(d):
            d.modified = True

        CallbackDict.__init__(self, initial, _on_update)

        if not initial:
            self.modified = False

    def destroy(self):
        """Destroys a session completely, by deleting all keys and removing it
        from the internal store immediately.

        This allows removing a session for security reasons, e.g. a login
        stored in a session will cease to exist if the session is destroyed.
        """
        for k in self.keys():
            del self[k]

        if self.sid_s:
            self.store.delete(self.sid_s)

        self.modified = False
        self.new = False

    def regenerate(self):
        self.modified = True

        if self.sid_s:
            # delete old session
            self.store.delete(self.sid_s)

            # remove sid_s, set modified
            self.sid_s = None
            self.modified = True

            # save_session() will take care of saving the session now


class KVSessionInterface(SessionInterface):
    def __init__(self, store, random_source=None):
        self.store = store
        self.random_source = random_source

    def open_session(self, app, request):
        key = app.secret_key

        if key is not None:
            session_cookie = request.cookies.get(
                app.config['SESSION_COOKIE_NAME'],
                None
            )

            if session_cookie:
                try:
                    # restore the cookie, if it has been manipulated,
                    # we will find out here
                    sid_s = Signer(app.secret_key).unsign(session_cookie)
                    sid = SessionID.unserialize(sid_s)

                    if sid.has_expired(
                        app.config['PERMANENT_SESSION_LIFETIME']):
                        return None  # the session has expired, no need to even
                                     # check if it exists

                    # retrieve from store
                    s = KVSession(json.loads(self.store.get(sid_s)))
                    s.sid_s = sid_s
                except (BadSignature, KeyError):
                    # either the cookie was manipulated or we did not find the
                    # session in the backend.
                    return None
            else:
                s = KVSession()  # create an empty session
                s.new = True

            s.store = self.store
            return s

    def save_session(self, app, session, response):
        if session.modified:
            # create a new session id only if requested
            # this makes it possible to avoid session fixation, but prevents
            # full cookie-highjacking if used carefully
            if not getattr(session, 'sid_s', None):
                session.sid_s = SessionID(self.random_source.getrandbits(
                                    app.config['SESSION_KEY_BITS'])
                                ).serialize()

            self.store.put(session.sid_s, json.dumps(session))
            session.new = False

            # save sid_s in session cookie
            cookie_data = Signer(app.secret_key).sign(session.sid_s)

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

    def __init__(self, session_kvstore, app=None):
        self.session_kvstore = session_kvstore

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
        app.config.setdefault('SESSION_RANDOM_SOURCE', None)

        if not hasattr(app, 'session_interface'):
            app.open_session = lambda r: \
                app.session_interface.open_session(app, r)
            app.save_session = lambda s, r: \
                app.session_interface.save_session(app, s, r)

        self.random_source = app.config['SESSION_RANDOM_SOURCE'] or\
                             SystemRandom()

        app.session_interface = KVSessionInterface(self.session_kvstore,
                                                   self.random_source)
