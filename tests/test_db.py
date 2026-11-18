# test_db.py: EditorDB adapter, with a fake connection (no database needed)

import psycopg
import pytest

from gdex_python_gdexms.editor import db as dbmod
from gdex_python_gdexms.editor.db import EditorDB, EditorDBError, valid_dsid, valid_ident


class FakeCursor:
   def __init__(self, conn):
      self.conn = conn
      self.rowcount = 2
      self.description = [('dsid', 25), ('title', 25)]

   def execute(self, sql, params=None):
      if sql.startswith('SET search_path'): return
      self.conn.log.append((sql, params))
      if self.conn.fail: raise self.conn.fail

   def fetchone(self): return ('d627000', 'ERA5')
   def fetchall(self): return [('d627000', 'ERA5'), ('d633000', 'JRA-3Q')]
   def close(self): pass


class FakeConn:
   def __init__(self):
      self.log = []
      self.fail = None
      self.closed = False
      self.autocommit = True
      self.commits = self.rollbacks = 0

   def cursor(self): return FakeCursor(self)
   def commit(self): self.commits += 1
   def rollback(self): self.rollbacks += 1
   def close(self): self.closed = True


@pytest.fixture
def db(tmp_path, monkeypatch):
   monkeypatch.setenv('GDEXMS_LOGPATH', str(tmp_path))
   d = EditorDB()
   conn = FakeConn()
   d.pgdb = conn
   d.pgconnect = lambda *a, **k: setattr(d, 'pgdb', conn) or conn
   d.conn = conn
   return d


def test_rows_and_one(db):
   assert db.rows('dataset', 'dsid, title', "dsid LIKE %s", ('d6%',)) == [
      {'dsid': 'd627000', 'title': 'ERA5'}, {'dsid': 'd633000', 'title': 'JRA-3Q'}]
   assert db.conn.log[-1] == ("SELECT dsid, title FROM dataset WHERE dsid LIKE %s", ('d6%',))
   assert db.one('dataset', 'dsid, title', "dsid = %s", ('d627000',)) == {'dsid': 'd627000', 'title': 'ERA5'}


def test_writes_bind_values(db):
   assert db.update('dscheck', {'pid': 9}, "cindex = %s AND pid = 0", (7,)) == 2
   assert db.conn.log[-1][1] == (9, 7)
   assert db.delete('dsgroup', "gindex = %s", (3,)) == 2
   assert db.execute("UPDATE dataset SET version = version + 1 WHERE dsid = %s", ('d627000',)) == 2


def test_db_error_raises_not_exits(db):
   db.PGLOG['DBRETRY'] = 0    # a hand-made error has no sqlstate, so skip the retry sleeps
   db.conn.fail = psycopg.errors.UndefinedTable('relation "nope" does not exist')
   with pytest.raises(EditorDBError):
      db.rows('nope', 'dsid')


def test_exit_path_raises_and_never_emails(db, monkeypatch):
   sent = []
   monkeypatch.setattr(dbmod.PgDBI, 'send_email', lambda *a, **k: sent.append(a))
   db.PGLOG['EMLMSG'] = 'pending'
   with pytest.raises(EditorDBError, match='fatal'):
      db.pglog('fatal problem', db.LGEREX)
   assert not sent and db.pgdb is None


def test_transaction_commit_and_rollback(db):
   with db.transaction():
      db.update('dscheck', {'pid': 1}, "cindex = %s", (1,))
   assert db.conn.commits == 1 and db.curtran == 0
   with pytest.raises(RuntimeError):
      with db.transaction():
         db.update('dscheck', {'pid': 1}, "cindex = %s", (1,))
         raise RuntimeError('boom')
   assert db.conn.rollbacks == 1 and db.curtran == 0


def test_identifier_checks():
   assert valid_ident('wfile_d627000') == 'wfile_d627000'
   assert valid_dsid('d627000') == 'd627000'
   for bad in ('wfile; drop table x', 'Name', ''):
      with pytest.raises(ValueError): valid_ident(bad)
   with pytest.raises(ValueError): valid_dsid('ds627.0')
