from datetime import datetime
import time

from flask_kvsession import SessionID


def test_serialize():
    t = int(time.time())
    dt = datetime.utcfromtimestamp(t)
    sid = SessionID(1234, dt)

    assert '%x_%x' % (1234, t) == sid.serialize()


def test_automatic_created_date():
    start = datetime.utcnow()
    sid = SessionID(0)
    end = datetime.utcnow()

    assert start <= sid.created <= end


def test_serialize_unserialize():
    dt = datetime(2011, 7, 9, 13, 14, 15)
    id = 59034

    sid = SessionID(id, dt)
    data = sid.serialize()

    SessionID(123)

    restored_sid = sid.unserialize(data)

    assert sid.id == restored_sid.id
    assert sid.created == restored_sid.created
