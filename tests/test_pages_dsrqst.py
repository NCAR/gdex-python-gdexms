# test_pages_dsrqst.py: the DSRQST pages (request, partition, limits, files, tar files, history)

import re
from contextlib import contextmanager

import pytest

from gdex_python_gdexms.pages.dsrqst_dslimit import DsrqstDslimit
from gdex_python_gdexms.pages.dsrqst_file import DsrqstFile
from gdex_python_gdexms.pages.dsrqst_partition import DsrqstPartition
from gdex_python_gdexms.pages.dsrqst_purge import DsrqstPurge
from gdex_python_gdexms.pages.dsrqst_request import DsrqstRequest
from gdex_python_gdexms.pages.dsrqst_tarfile import DsrqstTarfile
from gdex_python_gdexms.pages.dsrqst_userlimit import DsrqstUserlimit


class DB:
   """Fake database: canned table rows, a record for edit forms, lookups by SQL substring."""

   def __init__(self, rows=None, record=None, lookups=None, before=None, rights=1):
      self.rows = rows or []
      self.record = record or {}
      self.lookups = lookups or {}         # substring of SQL -> row dict (None = no row)
      self.before = before or []           # rows for the before-edit cache select
      self.rights = rights
      self.log = []
      self.trans = []

   def begin_request(self):
      pass

   @contextmanager
   def transaction(self):
      self.trans.append('begin')
      yield self
      self.trans.append('commit')

   def query(self, sql, vals=None):
      vals = list(vals or [])
      self.log.append((sql, vals))
      s = ' '.join(sql.split())
      if s.startswith('insert into') and ' returning ' in s:
         return [{'id': 99}]
      if 'mate_columns' in s:
         return []
      if 'count(distinct' in s:
         return [{'num': self.rights}]
      if 'pid > 0 and' in s:
         return []
      if 'and pid = %s and' in s and 'count(*) as num' in s:
         return [{'num': len(vals) - 2}]
      if 'count(*) as num_results' in s:
         return [{'num_results': len(self.rows)}]
      if 'as total_' in s:
         return [{'total_count': len(self.rows), 'total_size': 0}]
      for key, row in self.lookups.items():
         if key in s:
            return [row] if row else []
      if s.startswith('select rindex, status from'):
         return [dict(r) for r in self.before]
      if s.startswith('select * from'):
         return [dict(self.record)] if self.record else []
      if s.startswith('select') and ' from dssdb.' in s:
         return [dict(r) for r in self.rows]
      return []

   def query_one(self, sql, vals=None):
      rows = self.query(sql, vals)
      return rows[0] if rows else None

   def execute(self, sql, vals=None):
      vals = list(vals or [])
      self.log.append((sql, vals))
      s = ' '.join(sql.split())
      if s.startswith('update') and '= %s, pid = %s' in s:
         return len(vals) - 5        # lock update: 3 set values + ids + 2 condition values
      return 1

   def writes(self):
      return [(' '.join(s.split()), v) for s, v in self.log
              if s.lstrip().lower().startswith(('insert', 'update', 'delete'))]


def run(cls, action, info='', db=None, session=None):
   db = db or DB()
   session = {} if session is None else session
   page = cls(db, session, specialist='zji', page_url='/x.php', cookies={'mate_user_id': 'u1'},
              action=action, info=info)
   page.init_editor()
   ret = page.editor.main(action, info)
   return ret, db, session, page


def layer(ret, name):
   vals = [r['value'] for r in ret if r.get('layer_id') == name]
   return vals[-1] if vals else None


def scripts(ret):
   return [r['value'] for r in ret if r['where'] == 'javascript']


ALL = [
   (DsrqstRequest, 'Request Information', {'rindex': 5, 'email': 'a@b.edu', 'status': 'Q'}, True),
   (DsrqstPartition, 'Request Partition Information', {'pindex': 3, 'rindex': 5, 'status': 'Q'}, True),
   (DsrqstDslimit, 'Dataset Limit Information', {'dsid': 'd627000', 'processlimit': 45}, True),
   (DsrqstUserlimit, 'User Request Limit Information', {'email': 'all', 'maxrqstcheck': 10}, True),
   (DsrqstFile, 'Requeset File Information', {'findex': 1, 'wfile': 'f1.nc', 'rindex': 5}, False),
   (DsrqstTarfile, 'Requeset Tar File Information', {'tindex': 2, 'wfile': 't1.tar', 'rindex': 5}, False),
   (DsrqstPurge, 'Request History', {'rindex': 5, 'email': 'a@b.edu', 'exectime': 3725}, False),
]


@pytest.mark.parametrize('cls,title,row,can_add', ALL)
def test_update_html_and_forms(cls, title, row, can_add):
   ret, db, _, _ = run(cls, 'update_html', db=DB(rows=[row]))
   assert layer(ret, 'titleLayer') == title
   assert 'mateTable' in layer(ret, 'tableLayer')
   ret, _, _, page = run(cls, 'add_row')
   if can_add:
      assert '_add_form"' in layer(ret, 'recordLayer')
   else:
      assert 'A' not in page.editor.permissions
   ret, _, _, page = run(cls, 'edit_row', str(row[page.editor.primary_col]), db=DB(record=row))
   assert '_edit_form"' in layer(ret, 'recordLayer')


# ---- dsrqst_request ----------------------------------------------------------------

def test_request_config():
   _, _, _, page = run(DsrqstRequest, 'update_html')
   ed = page.editor
   assert ed.before_edit_array == ['status']
   assert ed.after_edit_fun == page.check_status and ed.after_add_fun == page.set_default_values
   assert ed.lock_info['host'] == 'lockhost' and ed.lock_info['time'] == 'locktime'
   assert list(ed.columns).count('priority') == 1


def test_request_after_add_sets_defaults_from_ruser():
   info = {'email': 'jo@ucar.edu', 'dsid': 'd627000', 'rqsttype': 'C', 'status': 'W', 'specialist': 'zji'}
   db = DB(lookups={'from ruser': {'lstname': "O'Brien-Smith"}})
   run(DsrqstRequest, 'insert_row', info, db=db)
   ruser = [e for e in db.log if 'from ruser' in e[0]][0]
   assert ruser == ('select lname lstname from ruser where email = %s AND end_date IS NULL', ['jo@ucar.edu'])
   assert not [e for e in db.log if 'from wuser' in e[0]]
   upd = [w for w in db.writes() if w[0].startswith('UPDATE dsrqst')][0]
   assert upd[0] == "UPDATE dsrqst SET fromflag = 'M', date_rqst = %s, time_rqst = %s, rqstid = %s WHERE rindex = %s"
   assert re.match(r'^\d{4}-\d\d-\d\d$', upd[1][0]) and re.match(r'^\d\d:\d\d:\d\d$', upd[1][1])
   assert upd[1][2:] == ['OBRIENSMITH99', '99']
   assert db.trans == ['begin', 'commit']


def test_request_after_add_falls_back_to_wuser_then_email():
   info = {'email': 'jo.x@ucar.edu', 'dsid': 'd627000', 'specialist': 'zji'}
   db = DB(lookups={'from ruser': None, 'from wuser': {'lstname': 'Doe'}})
   run(DsrqstRequest, 'insert_row', info, db=db)
   assert [e for e in db.log if 'from wuser' in e[0]][0][1] == ['jo.x@ucar.edu']
   assert [w for w in db.writes() if w[0].startswith('UPDATE dsrqst')][0][1][2] == 'DOE99'

   db = DB(lookups={'from ruser': None, 'from wuser': None})
   run(DsrqstRequest, 'insert_row', info, db=db)
   assert [w for w in db.writes() if w[0].startswith('UPDATE dsrqst')][0][1][2] == 'JOX99'


def test_request_after_add_without_email():
   db = DB()
   run(DsrqstRequest, 'insert_row', {'dsid': 'd627000', 'specialist': 'zji'}, db=db)
   upd = [w for w in db.writes() if w[0].startswith('UPDATE dsrqst')][0]
   assert upd[0] == "UPDATE dsrqst SET fromflag = 'M', date_rqst = %s, time_rqst = %s WHERE rindex = %s"
   assert upd[1][2] == '99'
   assert not [e for e in db.log if 'ruser' in e[0]]


def edit_then_update(cls, ids, info, before):
   """Open the edit screen (takes the record lock), then submit the update in the same session."""
   session = {}
   record = dict(before[0]) if before else {}
   if len(ids) == 1:
      run(cls, 'edit_row', ids[0], db=DB(record=record), session=session)
      action = 'update_row'
   else:
      run(cls, 'edit_mult_rows', {str(i): v for i, v in enumerate(ids)}, db=DB(record=record), session=session)
      action = 'update_mult_rows'
   ret, db, _, page = run(cls, action, info, db=DB(record=record, before=before, rights=len(ids)), session=session)
   return ret, db, page


def ptrqst_writes(db):
   return [w for w in db.writes() if w[0].startswith('UPDATE dssdb.ptrqst')]


def test_request_edit_e_to_q_requeues_partitions():
   info = {'old_primary_key_value': '5', 'status': 'Q', 'time_purge': '00:00:00', 'date_purge': '2026-12-01'}
   ret, db, page = edit_then_update(DsrqstRequest, ['5'], info, [{'rindex': 5, 'status': 'E'}])
   upd = [w for w in db.writes() if w[0].startswith('update dssdb.dsrqst set')][0]
   assert upd == ('update dssdb.dsrqst set status = %s, time_purge = %s, date_purge = %s where rindex in (%s)',
                  ['Q', '00:00:00', '2026-12-01', '5'])
   assert page.editor.before_edit == {'5': {'status': 'E'}}
   assert ptrqst_writes(db) == [("UPDATE dssdb.ptrqst SET status = 'Q' WHERE rindex = %s AND status = 'E'", ['5'])]


def test_request_mult_edit_e_to_q_only_errored_rows():
   info = {'idArr': ['5', '6', '7'], 'inputInfo': {'status': 'Q'}}
   before = [{'rindex': 5, 'status': 'E'}, {'rindex': 6, 'status': 'O'}, {'rindex': 7, 'status': 'E'}]
   ret, db, page = edit_then_update(DsrqstRequest, ['5', '6', '7'], info, before)
   assert [w for w in db.writes() if w[0].startswith('update dssdb.dsrqst set')][0][1] == ['Q', '5', '6', '7']
   assert [w[1] for w in ptrqst_writes(db)] == [['5'], ['7']]


@pytest.mark.parametrize('old,new', [('Q', 'Q'), ('E', 'O'), ('W', 'Q')])
def test_request_edit_other_status_changes_do_nothing(old, new):
   info = {'old_primary_key_value': '5', 'status': new}
   ret, db, page = edit_then_update(DsrqstRequest, ['5'], info, [{'rindex': 5, 'status': old}])
   assert [w for w in db.writes() if w[0].startswith('update dssdb.dsrqst set')]
   assert not ptrqst_writes(db)


def test_request_edit_without_status_skips_check():
   info = {'old_primary_key_value': '5', 'priority': '3'}
   ret, db, page = edit_then_update(DsrqstRequest, ['5'], info, [{'rindex': 5, 'status': 'E'}])
   assert not ptrqst_writes(db)


def test_request_view_running_status():
   row = {'rindex': 5, 'dsrqst': '0 ', 'note': 'line1\nline2', 'status': 'Q'}
   ret, db, _, _ = run(DsrqstRequest, 'view_row', '5', db=DB(rows=[row], lookups={'where dsrqst.rindex': row}))
   html = layer(ret, 'recordLayer')
   assert '<pre>line1\nline2</pre>' in html


# ---- dsrqst_dslimit / dsrqst_userlimit ----------------------------------------------

def test_dslimit_valid_dataset_id():
   db = DB(lookups={'from dataset where dsid': {'dsid': 'd627000'}})
   _, _, _, page = run(DsrqstDslimit, 'update_html', db=db)
   assert page.valid_dataset_id('dsid', '', {}) and page.valid_dataset_id('dsid', 'all', {})
   assert page.valid_dataset_id('dsid', 'd627000', {})
   assert [e for e in db.log if 'from dataset' in e[0]][-1] == ('select dsid from dataset where dsid = %s',
                                                                 ['d627000'])
   db.lookups = {'from dataset where dsid': None}
   assert not page.valid_dataset_id('dsid', "x' or 1=1", {})


def test_dslimit_insert_rejects_unknown_dataset():
   db = DB(lookups={'from dataset where dsid': None})
   ret, db, _, _ = run(DsrqstDslimit, 'insert_row', {'dsid': 'd999999', 'processlimit': '3'}, db=db)
   assert not db.writes() and 'Please correct' in layer(ret, 'titleLayer')


def test_userlimit_valid_user_email():
   _, _, _, page = run(DsrqstUserlimit, 'update_html')
   assert page.valid_user_email('email', '', {}) and page.valid_user_email('email', 'all', {})
   assert page.valid_user_email('email', 'jo@ucar.edu', {})
   assert not page.valid_user_email('email', 'not-an-email', {})


# ---- dsrqst_file / dsrqst_tarfile / dsrqst_purge --------------------------------------

@pytest.mark.parametrize('cls', [DsrqstFile, DsrqstTarfile])
def test_file_dataset_title(cls):
   db = DB(lookups={'FROM dataset WHERE dsid': {'title': 'ERA5'}})
   _, _, _, page = run(cls, 'update_html', db=db)
   assert page.get_dataset_title('dsid', 'd633000', {}) == 'd633000 - ERA5'
   assert [e for e in db.log if 'FROM dataset' in e[0]][-1] == ('SELECT title FROM dataset WHERE dsid = %s',
                                                                 ['d633000'])
   db.lookups = {'FROM dataset WHERE dsid': None}
   assert page.get_dataset_title('dsid', 'd000000', {}) == 'd000000'
   assert page.get_dataset_title('dsid', '', {}) == ''
   assert 'readonly="readonly"' in page.editor.columns['wfile']['input_info']


def test_purge_group_title_and_interval():
   db = DB(lookups={'FROM dsgroup': {'title': 'Surface'}})
   _, _, _, page = run(DsrqstPurge, 'update_html', db=db)
   assert page.get_group_title('gindex', '3', {'dsid': 'd627000', 'gindex': '3'}) == '3 - Surface'
   assert [e for e in db.log if 'FROM dsgroup' in e[0]][-1] == (
      'SELECT title FROM dsgroup WHERE gindex = %s AND dsid = %s', ['3', 'd627000'])
   assert page.get_group_title('gindex', '0', {'dsid': 'd627000'}) == '0'
   assert page.editor.columns['exectime']['table_fun']('exectime', '3725', {}) == '1H2N5S'
