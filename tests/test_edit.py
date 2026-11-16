# test_edit.py: add/edit/delete, record locks and column preferences, with a scripted fake database

from contextlib import contextmanager

from gdex_python_gdexms.pages import PAGES


class WriteDB:
   """Fake database: answers selects from rules, counts writes, records every (sql, vals)."""

   def __init__(self, record=None, rights=1, locked=None, lock_count=None, held=1, prefs=None, rowcount=1):
      self.record = record or {}          # row for 'select * ... where <pkey> = %s'
      self.rights = rights                # count for the rights check
      self.locked = locked                # row for the 'is it locked by someone else' check
      self.lock_count = lock_count        # rows the lock update claims (default: all asked)
      self.held = held                    # count for the 'lock still held' check
      self.prefs = prefs or []            # mate_columns rows
      self.rowcount = rowcount
      self.log = []
      self.trans = []

   def begin_request(self):
      pass

   @contextmanager
   def transaction(self):
      self.trans.append('begin')
      try:
         yield self
      except BaseException:
         self.trans.append('rollback')
         raise
      self.trans.append('commit')

   def query(self, sql, vals=None):
      self.log.append((sql, list(vals or [])))
      s = ' '.join(sql.split())
      if s.startswith('insert into') and ' returning ' in s:
         return [{'id': 99}]
      if 'from mate_columns' in s:
         if s.startswith('select id'):
            return [{'id': 5}] if self.prefs else []
         return self.prefs
      if 'count(distinct' in s:
         return [{'num': self.rights}]
      if 'pid > 0 and' in s:
         return [self.locked] if self.locked else []
      if 'and pid = %s and' in s and 'count(*) as num' in s:
         return [{'num': self.held}]
      if s.startswith('select * from'):
         return [dict(self.record)] if self.record else []
      if 'count(*) as num_results' in s:
         return [{'num_results': 0}]
      return []

   def query_one(self, sql, vals=None):
      rows = self.query(sql, vals)
      return rows[0] if rows else None

   def execute(self, sql, vals=None):
      self.log.append((sql, list(vals or [])))
      s = ' '.join(sql.split())
      if s.startswith('update') and "= %s, pid = %s" in s and self.lock_count is not None:
         return self.lock_count
      if s.startswith('update') and "= %s, pid = %s" in s:
         return len(vals) - 5        # lock update: 3 set values + ids + 2 condition values
      return self.rowcount

   def writes(self):
      return [(' '.join(s.split()), v) for s, v in self.log
              if s.lstrip().lower().startswith(('insert', 'update', 'delete'))]


def run(page_name, action, info='', db=None, session=None, cookies=None):
   db = db or WriteDB()
   session = {} if session is None else session
   page = PAGES[page_name](db, session, specialist='zji', page_url='/' + page_name + '.php',
                           cookies=cookies or {'mate_user_id': 'u1'}, action=action, info=info)
   page.init_editor()
   ret = page.editor.main(action, info)
   return ret, db, session


def layer(ret, name):
   vals = [r['value'] for r in ret if r.get('layer_id') == name]
   return vals[-1] if vals else None


def scripts(ret):
   return [r['value'] for r in ret if r['where'] == 'javascript']


# ---- forms ----------------------------------------------------------------------

def test_add_form_has_inputs_defaults_and_selects():
   ret, db, _ = run('dscheck_check', 'add_row')
   html = layer(ret, 'recordLayer')
   assert layer(ret, 'titleLayer') == 'Add A Check Record'
   assert '<form id="cindex-dscheck_add_form"' in html
   assert 'id="command"' in html and 'maxlength="128"' in html
   assert '<textarea id="argv" rows="1" cols="80"' in html
   assert '<option value="R">R - Request Index</option>' in html          # otype select_array
   assert 'id="cindex"' not in html                                         # no A perm
   assert '<input type="text" id="mcount" value="1"' in html               # default
   assert any(sql.startswith('select logname') for sql, _ in db.log)       # specialist select_query
   assert 'showRecordPane();' in scripts(ret)


def test_edit_form_locks_record():
   rec = {'cindex': 7, 'command': 'dsarch', 'workdir': '/a "b"', 'specialist': 'zji', 'pid': 0, 'lockhost': ''}
   ret, db, session = run('dscheck_check', 'edit_row', '7', db=WriteDB(record=rec))
   html = layer(ret, 'recordLayer')
   assert 'id="cindex-dscheck_edit_form"' in html
   assert '<textarea id="workdir" rows="1" cols="80" maxlength="128" >/a &quot;b&quot;</textarea>' in html
   assert 'id="command"' not in html                                       # no E perm
   assert "updateRow('7','cindex-dscheck');" in html
   lock = [w for w in db.writes() if 'pid = %s' in w[0]][0]
   assert lock[0].startswith('update dssdb.dscheck set lockhost = %s, pid = %s, chktime = %s where cindex in (%s)')
   assert lock[1][0] == 'rda_config' and lock[1][3] == '7'
   assert session['cindex-dschecklockInfo']['id'] == '7'
   assert 'set_edit_timeout();' in scripts(ret)


def test_edit_refused_when_locked_by_daemon():
   rec = {'cindex': 7, 'command': 'dsarch'}
   db = WriteDB(record=rec, locked={'cindex': 7, 'lockhost': 'casper', 'pid': 1234})
   ret, db, session = run('dscheck_check', 'edit_row', '7', db=db)
   assert any('disableEditPage' in s and 'locked by casper(1234)' in s for s in scripts(ret))
   assert 'set_edit_timeout();' not in scripts(ret)
   assert not db.writes()


def test_edit_gone_record():
   ret, _, _ = run('rdadb_org_type', 'edit_row', 'NOPE', db=WriteDB(record={}))
   assert scripts(ret)[0].startswith("toAjaxTableEditor('update_html','Edit screen was closed")


# ---- update ---------------------------------------------------------------------

def test_update_row_binds_values_and_ignores_unknown_fields():
   info = {'old_primary_key_value': 'NCAR', 'org_type': 'NCAR', 'description': "Lab's staff",
           'nosuch; drop table x': 'y'}
   ret, db, _ = run('rdadb_org_type', 'update_row', info, db=WriteDB(record={'org_type': 'NCAR'}))
   upd = [w for w in db.writes() if w[0].startswith('update dssdb.org_type')]
   assert upd == [('update dssdb.org_type set org_type = %s, description = %s where org_type in (%s)',
                   ['NCAR', "Lab's staff", 'NCAR'])]
   assert db.trans == ['begin', 'commit']
   assert layer(ret, 'titleLayer') == 'Organization Type Information'     # back to the table


def test_update_row_required_field_error():
   db = WriteDB(record={'org_type': 'NCAR'})
   page = PAGES['rdadb_org_type'](db, {}, specialist='zji', cookies={'mate_user_id': 'u1'}, action='update_row')
   page.init_editor()
   page.editor.columns['description']['req'] = True
   ret = page.editor.main('update_row', {'old_primary_key_value': 'NCAR', 'org_type': 'NCAR', 'description': ' '})
   assert not db.writes()
   assert 'Please correct the fields in red' in layer(ret, 'titleLayer')
   assert '$("description_label_cell").setStyle("color: #f90d0d;");' in scripts(ret)
   assert '$("org_type_label_cell").setStyle("color: #333;");' in scripts(ret)


def test_update_without_lock_is_refused_on_locking_page():
   info = {'old_primary_key_value': '7', 'dsid': 'd627000'}
   ret, db, _ = run('dscheck_check', 'update_row', info, db=WriteDB(record={'cindex': 7}))
   assert not [w for w in db.writes() if 'set dsid' in w[0]]
   assert any('record lock was lost' in s for s in scripts(ret))


def test_update_row_without_rights_is_refused():
   info = {'old_primary_key_value': 'NCAR', 'description': 'x'}
   ret, db, _ = run('rdadb_org_type', 'update_row', info, db=WriteDB(record={'org_type': 'NCAR'}, rights=0))
   assert not db.writes()
   assert any('do not have rights' in s for s in scripts(ret))


def test_lock_kept_until_update_then_released():
   session = {}
   rec = {'cindex': 7, 'command': 'dsarch'}
   run('dscheck_check', 'edit_row', '7', db=WriteDB(record=rec), session=session)
   pid = session['cindex-dschecklockInfo']['pid']
   info = {'old_primary_key_value': '7', 'cindex': '7', 'dsid': 'd627000', 'workdir': '', 'command': 'nope'}
   ret, db, session = run('dscheck_check', 'update_row', info, db=WriteDB(record=rec), session=session)
   writes = db.writes()
   assert writes[0] == ('update dssdb.dscheck set cindex = %s, dsid = %s, workdir = %s where cindex in (%s)',
                        ['7', 'd627000', None, '7'])
   release = writes[1]
   assert release[0] == "update dssdb.dscheck set lockhost = '', pid = 0 where cindex in (%s) and pid = %s and lockhost = %s"
   assert release[1] == ['7', pid, 'rda_config']
   assert session['cindex-dschecklockInfo'] is None


def test_update_refused_when_lock_lost():
   session = {}
   rec = {'cindex': 7, 'command': 'dsarch'}
   run('dscheck_check', 'edit_row', '7', db=WriteDB(record=rec), session=session)
   info = {'old_primary_key_value': '7', 'dsid': 'd627000'}
   ret, db, _ = run('dscheck_check', 'update_row', info, db=WriteDB(record=rec, held=0), session=session)
   assert not [w for w in db.writes() if 'set dsid' in w[0]]
   assert any('record lock was lost' in s for s in scripts(ret))


def test_other_action_releases_stale_lock():
   session = {}
   run('dscheck_check', 'edit_row', '7', db=WriteDB(record={'cindex': 7}), session=session)
   _, db, session = run('dscheck_check', 'update_html', db=WriteDB(), session=session)
   assert db.writes()[0][0].startswith("update dssdb.dscheck set lockhost = '', pid = 0 where cindex in (%s)")


def test_update_mult_rows_only_mass_editable_columns():
   info = {'idArr': ['1', '2'], 'inputInfo': {'data_format': 'NetCDF', 'wfile': 'evil', 'wid': '3',
                                             'data_format_em_cb': 'on'}}
   session = {'wfile_dsid': 'd627000'}
   ret, db, _ = run('dsarch_webfile', 'update_mult_rows', info, db=WriteDB(rights=2), session=session)
   upd = [w for w in db.writes() if w[0].startswith('update dssdb.wfile_d627000')]
   assert upd == [('update dssdb.wfile_d627000 set data_format = %s where wid in (%s, %s)', ['NetCDF', '1', '2'])]


def test_edit_mult_form():
   info = {'1': '11', '2': '12'}
   session = {'wfile_dsid': 'd627000'}
   ret, _, _ = run('dsarch_webfile', 'edit_mult_rows', info, db=WriteDB(record={'wid': 11, 'data_format': 'GRIB'}),
                   session=session)
   html = layer(ret, 'recordLayer')
   assert layer(ret, 'titleLayer') == 'Set Common Values For 2 Web Files'
   assert 'id="data_format_em_cb"' in html and 'id="wfile"' not in html and 'id="wid"' not in html
   assert "updateMultRows(new Array('11','12'),'wid-wfile_d627000');" in html


def test_webfile_edit_needs_dataset():
   ret, db, _ = run('dsarch_webfile', 'delete_row', '1', db=WriteDB())
   assert any('Dataset ID first' in s for s in scripts(ret)) and not db.writes()


# ---- insert / copy / delete --------------------------------------------------------

def test_insert_row_applies_default_and_after_add_hook():
   info = {'command': 'dsarch', 'argv': 'd627000 sw', 'specialist': 'zji', 'mcount': '', 'nosuch': 'x'}
   ret, db, _ = run('dscheck_check', 'insert_row', info)
   ins = [w for w in db.log if w[0].startswith('insert into dssdb.dscheck')][0]
   assert ins[0].startswith('insert into dssdb.dscheck(command, argv, specialist, mcount) values(%s, %s, %s, %s)')
   assert ins[0].endswith('returning cindex') and ins[1] == ['dsarch', 'd627000 sw', 'zji', '1']
   stamp = [w for w in db.writes() if w[0].startswith('UPDATE dscheck SET date')][0]
   assert stamp[1][2] == '99'
   assert db.trans == ['begin', 'commit']


def test_copy_row_prefills_copyable_columns():
   rec = {'org_type': 'NCAR', 'description': 'NCAR staff'}
   ret, _, _ = run('rdadb_org_type', 'copy_row', 'NCAR', db=WriteDB(record=rec))
   html = layer(ret, 'recordLayer')
   assert '>NCAR staff</textarea>' in html                 # description has C
   assert 'id="org_type" value=""' in html                  # org_type has no C


def test_delete_row_and_mult():
   ret, db, _ = run('rdadb_org_type', 'delete_row', 'NCAR', db=WriteDB(record={'org_type': 'NCAR'}))
   assert ('delete from dssdb.org_type where org_type = %s', ['NCAR']) in db.writes()
   ret, db, _ = run('rdadb_org_type', 'delete_mult_rows', {'0': 'A', '1': 'B'}, db=WriteDB(rights=2))
   assert [w[1] for w in db.writes() if w[0].startswith('delete')] == [['A'], ['B']]


def test_delete_refused_when_locked():
   db = WriteDB(locked={'cindex': 7, 'lockhost': 'casper', 'pid': 99})
   ret, db, _ = run('dscheck_check', 'delete_row', '7', db=db)
   assert not [w for w in db.writes() if w[0].startswith('delete')]
   assert any('Cannot delete 1 record! Check Index 7 is locked by casper(99)!' in s for s in scripts(ret))


# ---- column preferences ------------------------------------------------------------

def test_hide_and_show_column():
   ret, db, _ = run('rdadb_org_type', 'hide_column', 'description')
   assert db.writes()[0] == ('insert into mate_columns(mate_user_id, mate_var_prefix, mate_column, order_num, hidden, '
                             'date_updated) values(%s, %s, %s, %s, %s, now())',
                             ['u1', 'org_type-org_type', 'description', 0, 'Yes'])
   ret, db, _ = run('rdadb_org_type', 'show_column', 'description', db=WriteDB(prefs=[{'id': 5}]))
   assert db.writes()[0] == ('update mate_columns set hidden = %s where id = %s', ['No', 5])
   ret, db, _ = run('rdadb_org_type', 'hide_column', 'org_type')     # no H perm: ignored
   assert not db.writes()


def test_show_hide_screen_and_order():
   prefs = [{'mate_column': 'description', 'hidden': 'Yes'}]
   ret, _, _ = run('rdadb_org_type', 'show_hide_columns', db=WriteDB(prefs=prefs))
   assert 'id="description_hide_cb" onchange="showHideColumn(this,\'description\');"  />' in layer(ret, 'tableLayer')
   ret, db, _ = run('rdadb_org_type', 'update_column_order',
                    'columnOrderList[]=description&columnOrderList[]=org_type&columnOrderList[]=bogus')
   assert [w[1][2:4] for w in db.writes()] == [['description', 1], ['org_type', 2]]
   ret, db, _ = run('rdadb_org_type', 'reset_column_order')
   assert db.writes()[0] == ('update mate_columns set order_num = 0 where mate_user_id = %s and mate_var_prefix = %s',
                             ['u1', 'org_type-org_type'])
   assert 'Sortable.create("columnOrderList"' in scripts(ret)[-1]
