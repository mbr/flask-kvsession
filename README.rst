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
* It is possible to securely destroy sessions to protect against replay
  attacks.

Other things are possible with server side session that are impossible with
clients side sessions, like inspecting and manipulating data in absence of the
client.

Flask-KVSession uses the `simplekv <http://github.com/mbr/simplekv>`_-package
for storing session data on a variety of backends, including `redis
<http://redis.io>`_, `memcached <http://memcached.org>`_, SQL databases using
`SQLAlchemy <http://sqlalchemy.org>`_ or just flat files.

Integration with Flask is seamless, once the extension is loaded for a Flask
application, it transparently replaces Flask's own Session management. Any
application working with sessions should work the same with Flask-KVSession
(if it does not, file a bug!).


Documentation and development
=============================

Development `happens on <https://github.com/mbr/flask-kvsession/>`_, you can
find the `documentation on PyPI <http://pythonhosted.org/Flask-KVSession`.


License
=======

Flask-KVSession is `MIT-licensed
<https://github.com/mbr/flask-kvsession/blob/master/LICENSE>`_.
