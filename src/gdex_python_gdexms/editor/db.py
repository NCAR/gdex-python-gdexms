"""Database adapter: rda_python_common's PgDBI made safe for a web worker.

PgDBI was written for command-line tools. In a web worker it must never exit the
process, never send abort emails, and must not leave a half-done transaction
behind for the next request. This module wraps it so that:

- Any database error is raised as EditorDBError (a Flask error handler turns it
  into the editor's normal error response) instead of returning FAILURE or
  calling sys.exit().
- Emails are never sent.
- Rows come back as a list of dicts instead of PgDBI's column-oriented dict.
- Values are always bound (cndvals), never pasted into SQL. Table and column
  names cannot be bound, so they must pass valid_ident()/valid_dsid() first.

One EditorDB per worker process (get_db()); PgDBI keeps a single connection and
is not thread-safe, so gunicorn runs sync workers with no threads.
"""

import os
import re
import tempfile
from contextlib import contextmanager

from rda_python_common.pg_dbi import PgDBI

IDENT_RE = re.compile(r'^[a-z_][a-z0-9_]*$')
DSID_RE = re.compile(r'^[a-z]\d{6}$')


class EditorDBError(Exception):
   """A database operation failed; the message is safe to show to a specialist."""


def valid_ident(name):
   """Return name if it is a plain lowercase SQL identifier, else raise ValueError."""
   if not isinstance(name, str) or not IDENT_RE.match(name):
      raise ValueError("Invalid SQL identifier: {!r}".format(name))
   return name


def valid_dsid(dsid):
   """Return dsid if it looks like a current GDEX dataset id (e.g. d627000), else raise ValueError."""
   if not isinstance(dsid, str) or not DSID_RE.match(dsid):
      raise ValueError("Invalid dataset id: {!r}".format(dsid))
   return dsid


class EditorDB(PgDBI):
   """PgDBI that raises EditorDBError instead of exiting, and never emails."""

   def __init__(self):
      super().__init__()
      self.PGLOG['BCKGRND'] = 1     # nothing echoed to the console
      self.PGLOG['DBRETRY'] = 2     # fail fast enough for gunicorn's request timeout
      self.PGLOG['LOGPATH'] = os.environ.get('GDEXMS_LOGPATH', tempfile.gettempdir())
      self.PGLOG['LOGFILE'] = os.environ.get('GDEXMS_LOGFILE', 'rda_config.log')
      self.PGLOG['ERRFILE'] = ''    # derived from LOGFILE: rda_config.err
      self.lasterr = None

   # ---- PgDBI/PgLOG overrides ------------------------------------------------

   def pglog(self, msg, logact=None):
      """Log as PgLOG does, but remember the last error so callers can raise it."""
      if logact is not None and logact & (self.ERRLOG | self.EXITLG):
         self.lasterr = (msg or 'Database error').strip()
      return super().pglog(msg, logact)

   def pgexit(self, stat=0):
      """Never exit the worker: drop the (possibly broken) connection and raise."""
      self.drop_connection()
      raise EditorDBError(self.lasterr or 'Database error')

   def send_email(self, subject=None, receiver=None, msg=None, sender=None, logact=None):
      """Never email from the web app; the message is already in the log file."""
      self.PGLOG['EMLMSG'] = ''
      return self.SUCCESS

   # ---- connection / request lifecycle ----------------------------------------

   def drop_connection(self):
      """Roll back anything pending and close the connection; the next query reconnects."""
      if self.pgdb:
         try:
            if not self.pgdb.closed:
               if self.curtran: self.pgdb.rollback()
               self.pgdb.close()
         except Exception:
            pass
      self.pgdb = self.PGLOG['PGDBBUF'] = None
      self.curtran = 0

   def begin_request(self):
      """Reset per-request state; abort a transaction a failed request left open."""
      self.lasterr = None
      self.PGLOG['EMLMSG'] = ''
      if self.curtran: self.aborttran()

   @contextmanager
   def transaction(self):
      """Run the block in one transaction: commit on success, roll back on any error."""
      self.starttran()
      try:
         yield self
      except BaseException:
         self.aborttran()
         raise
      else:
         self.endtran()

   def _call(self, func, *args, **kwargs):
      self.lasterr = None
      ret = func(*args, **kwargs)
      if self.lasterr: raise EditorDBError(self.lasterr)
      return ret

   # ---- query helpers (values always bound) -----------------------------------

   def one(self, tables, fields, cond=None, vals=None):
      """Return the first matching row as a dict, or None."""
      rec = self._call(self.pgget, tables, fields, cond, 0, cndvals=vals)
      return rec or None

   def rows(self, tables, fields, cond=None, vals=None):
      """Return all matching rows as a list of dicts."""
      cols = self._call(self.pgmget, tables, fields, cond, None, cndvals=vals)
      if not cols: return []
      names = list(cols)
      return [dict(zip(names, vals)) for vals in zip(*(cols[n] for n in names))]

   def count(self, tables, cond=None, vals=None):
      """Return the number of matching rows."""
      return self._call(self.pgget, tables, None, cond, 0, cndvals=vals) or 0

   def insert(self, table, record, getid=None):
      """Insert one record; returns the new id when getid names the id column."""
      return self._call(self.pgadd, valid_ident(table), record, None, getid)

   def update(self, table, record, cond, vals=None):
      """Update matching rows; returns the row count."""
      return self._call(self.pgupdt, valid_ident(table), record, cond, None, cndvals=vals)

   def delete(self, table, cond, vals=None):
      """Delete matching rows; returns the row count."""
      return self._call(self.pgdel, valid_ident(table), cond, None, cndvals=vals)

   def execute(self, sqlstr, vals=None):
      """Run a non-SELECT statement; returns the row count."""
      return self._call(self.pgexec, sqlstr, None, cndvals=vals)


_DB = None
_DBPID = None


def get_db():
   """Return this worker process's EditorDB, creating it on first use (fork-safe)."""
   global _DB, _DBPID
   if _DB is None or _DBPID != os.getpid():
      _DB = EditorDB()
      _DBPID = os.getpid()
   return _DB
