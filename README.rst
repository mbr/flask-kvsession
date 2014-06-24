Flask-KVSession
===============

.. image:: https://travis-ci.org/mbr/flask-kvsession.svg?branch=master
           :target: https://travis-ci.org/mbr/flask-kvsession

Flask-KVSession is a drop-in replacement for `Flask
<http://flask.pocoo.org>`_'s signed cookie-based session management. Instead of
storing data on the client, only a securely generated ID is stored on the
client, while the actual session data resides on the server.

This has two major advantages:

* Clients no longer see the session information
* It is possible to securely destroy sessions. Even if the session cookie is
  stolen, it is no longer possible to use the session.

Other things are possible with server side session that are impossible with
clients side sessions, like inspecting and manipulating data in absence of the
client. The drawback is that sessions need to be stored. Flask-KVSession uses
the `simplekv <http://github.com/mbr/simplekv>`_-package for storing session
data on a variety of backends.

Integration with Flask is seamless, once the extension is loaded for a Flask
application, it transparently replaces (or rather, extends) Flask's own Session
class for this instance. Any application working with sessions should work the
same with Flask-KVSession.

Documentation
=============
Flask-KVSessions includes good unit test coverage. See also:

* `documentation <http://flask-kvsession.readthedocs.org>`_.
* `development version
  <https://github.com/mbr/flask-kvsession/tarball/master#egg=Flask-KVSession>`_

License
=======
Flask-KVSession is `MIT-licensed
<https://github.com/mbr/flask-kvsession/blob/master/LICENSE>`_.
