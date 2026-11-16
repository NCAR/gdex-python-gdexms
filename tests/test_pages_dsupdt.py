# test_pages_dsupdt.py: dsupdt_control, dsupdt_localfile, dsupdt_remotefile and dsrqst_control pages

from contextlib import contextmanager

import pytest

from gdex_python_gdexms.pages.dsrqst_control import DsrqstControl
from gdex_python_gdexms.pages.dsupdt_control import DsupdtControl
from gdex_python_gdexms.pages.dsupdt_localfile import DsupdtLocalfile
from gdex_python_gdexms.pages.dsupdt_remotefile import DsupdtRemotefile

PAGES = {'dsupdt_control': DsupdtControl, 'dsupdt_localfile': DsupdtLocalfile,
         'dsupdt_remotefile': DsupdtRemotefile, 'dsrqst_control': DsrqstControl}


class PageDB:
   """Fake database: table rows, one edit record, substring lookups; records every (sql, vals)."""

   def __init__(self, rows=None, record=None, lookups=None):
      self.rows = rows or []
      self.record = record or {}
      self.lookups = lookups or {}      # substring of SQL -> list of rows
      self.log = []

   def begin_request(self):
      pass

   @contextmanager
   def transaction(self):
      yield self

   def query(self, sql, vals=None):
      self.log.append((sql, list(vals or [])))
      s = ' '.join(sql.split())
      for key, rows in self.lookups.items():
         if key in s:
            return [dict(r) for r in rows]
      if 'mate_columns' in s:
         return []
      if 'count(*) as num_results' in s:
         return [{'num_results': len(self.rows)}]
      if 'count(distinct' in s:
         return [{'num': 1}]
      if 'pid > 0 and' in s:
         return []
      if 'and pid = %s and' in s and 'count(*) as num' in s:
         return [{'num': 1}]
      if s.startswith('select * from'):
         return [dict(self.record)] if self.record else []
      if s.startswith('select') and ' from dssdb.' in s and 'limit %s' in s:
         return [dict(r) for r in self.rows]
      return []

   def query_one(self, sql, vals=None):
      rows = self.query(sql, vals)
      return rows[0] if rows else None

   def execute(self, sql, vals=None):
      self.log.append((sql, list(vals or [])))
      s = ' '.join(sql.split())
      if s.startswith('update') and '= %s, pid = %s' in s:
         return len(vals) - 5
      return 1

   def find(self, needle):
      return [(' '.join(s.split()), v) for s, v in self.log if needle in ' '.join(s.split())]


def build(page_name, action, info='', db=None):
   db = db or PageDB()
   page = PAGES[page_name](db, {}, specialist='zji', page_url='/' + page_name + '.php',
                           cookies={'mate_user_id': 'u1'}, action=action, info=info)
   page.init_editor()
   return page, db


def run(page_name, action, info='', db=None):
   page, db = build(page_name, action, info, db)
   ret = page.editor.main(action, info)
   return ret, db, page


def layer(ret, name):
   vals = [r['value'] for r in ret if r.get('layer_id') == name]
   return vals[-1] if vals else None


TABLES = {
   'dsupdt_control': ('dcupdt', 'Update Control Information', {'cindex': 5, 'cntlid': 'gfs-daily', 'dsid': 'd083002'}),
   'dsupdt_localfile': ('dlupdt', 'DSUPDT Local File Information',
                        {'lindex': 8, 'locfile': 'gfs.<YYYYMMDD>.grb', 'dsid': 'd083002'}),
   'dsupdt_remotefile': ('drupdt', 'DSUPDT Remote File Information',
                         {'rindex': 4, 'remotefile': 'remote.<YYYYMMDD>', 'dsid': 'd083002'}),
   'dsrqst_control': ('rcrqst', 'Request Control Information', {'cindex': 3, 'dsid': 'd083002', 'rqsttype': 'S'}),
}

ADD_TITLES = {'dsupdt_control': 'Add An Update Control', 'dsupdt_localfile': 'Add A Local File Record',
              'dsupdt_remotefile': 'Add A Remote File Record', 'dsrqst_control': 'Add A Request Control'}
EDIT_TITLES = {'dsupdt_control': 'Edit An Update Control', 'dsupdt_localfile': 'Edit A Local File Record',
               'dsupdt_remotefile': 'Edit A Remote File Record', 'dsrqst_control': 'Edit A Request Control'}


@pytest.mark.parametrize('name', sorted(PAGES))
def test_update_html_renders_table(name):
   table, title, row = TABLES[name]
   ret, db, page = run(name, 'update_html', db=PageDB(rows=[row]))
   assert page.editor.table_name == table
   assert layer(ret, 'titleLayer') == title
   html = layer(ret, 'tableLayer')
   assert 'd083002' in html
   sql, _ = db.find('limit %s offset %s')[-1]
   assert ' from dssdb.{}'.format(table) in sql


@pytest.mark.parametrize('name', sorted(PAGES))
def test_add_row_renders_form(name):
   ret, db, _ = run(name, 'add_row')
   assert layer(ret, 'titleLayer') == ADD_TITLES[name]
   assert '_add_form"' in layer(ret, 'recordLayer')


@pytest.mark.parametrize('name', sorted(PAGES))
def test_edit_row_renders_form(name):
   rec = dict(TABLES[name][2])
   ret, db, _ = run(name, 'edit_row', str(next(iter(rec.values()))), db=PageDB(record=rec))
   assert layer(ret, 'titleLayer') == EDIT_TITLES[name]
   assert '_edit_form"' in layer(ret, 'recordLayer')


def test_lock_info_kept():
   assert build('dsupdt_control', 'update_html')[0].editor.lock_info
   assert build('dsupdt_localfile', 'update_html')[0].editor.lock_info
   assert not build('dsupdt_remotefile', 'update_html')[0].editor.lock_info
   ret, db, _ = run('dsupdt_control', 'edit_row', '5', db=PageDB(record={'cindex': 5}))
   assert any('lockhost' in s and 'chktime' in s for s, _ in db.find('update dssdb.dcupdt set'))
   ret, db, _ = run('dsupdt_localfile', 'edit_row', '8', db=PageDB(record={'lindex': 8}))
   assert any('hostname' in s and 'locktime' in s for s, _ in db.find('update dssdb.dlupdt set'))


# ---- dsupdt_control: selectParentIndex ------------------------------------------

def test_select_parent_index_excludes_own_control():
   ret, db, _ = run('dsupdt_control', 'edit_row', '5', db=PageDB(record={'cindex': 5, 'dsid': 'd083002'}))
   hits = db.find("select cindex, concat(dsid, ' - ', cntlid) from dcupdt")
   assert hits == [("select cindex, concat(dsid, ' - ', cntlid) from dcupdt where cindex <> %s "
                    "order by dsid, cindex", ['5'])]


def test_select_parent_index_all_controls_on_add():
   page, db = build('dsupdt_control', 'add_row')
   info = page.select_parent_index('pindex', '', {})
   assert info['select_query'] == "select cindex, concat(dsid, ' - ', cntlid) from dcupdt order by dsid, cindex"
   assert 'select_vals' not in info and info['valtype'] == 'integer'
   assert 'select_query' not in page.editor.columns['pindex']     # the column itself is untouched


# ---- dsupdt_localfile: checkControlIndex / selectControlIndex --------------------

def test_select_control_index():
   page, _ = build('dsupdt_localfile', 'add_row')
   info = page.select_control_index('cindex', '', {})
   assert info['select_query'] == "select cindex, concat(dsid, ' - ', cntlid) from dcupdt order by dsid, cindex"
   assert info['onchange'] is True and 'select_vals' not in info
   info = page.select_control_index('cindex', '', {'dsid': 'd083002'})
   assert info['select_query'] == 'select cindex, cntlid from dcupdt where dsid = %s order by cindex'
   assert info['select_vals'] == ['d083002'] and info['onchange'] is False


def test_edit_localfile_select_list_bound_to_dataset():
   db = PageDB(record={'lindex': 8, 'dsid': 'd083002', 'cindex': 3},
               lookups={'from dcupdt where dsid = %s': [{'cindex': 3, 'cntlid': 'gfs'}],
                        'select dsid from dcupdt where cindex = %s': [{'dsid': 'd083002'}]})
   ret, db, _ = run('dsupdt_localfile', 'edit_row', '8', db=db)
   assert db.find('select cindex, cntlid from dcupdt where dsid = %s order by cindex')[0][1] == ['d083002']
   assert db.find('select dsid from dcupdt where cindex = %s')[0][1] == ['3']
   assert '<option value="3" selected="selected">3 - gfs</option>' in layer(ret, 'recordLayer')


def test_check_control_index():
   db = PageDB(lookups={'select dsid from dcupdt where cindex = %s': [{'dsid': 'd083002'}]})
   page, db = build('dsupdt_localfile', 'add_row', db=db)
   assert page.check_control_index('cindex', '3', {'dsid': 'd083002'}) == '3'
   assert page.check_control_index('cindex', '3', {'dsid': 'd999999'}) == 0
   assert page.check_control_index('dsid', '', {'cindex': '3'}) == 'd083002'
   assert page.check_control_index('dsid', 'd111111', {'cindex': '3'}) == 'd111111'   # no lookup
   assert page.check_control_index('cindex', '3', {}) == '3'                          # no dataset yet
   assert page.check_control_index('cindex', '3; drop', {'dsid': 'd083002'}) == '3; drop'
   assert db.find('select dsid from dcupdt where cindex = %s') == [
      ('select dsid from dcupdt where cindex = %s', ['3'])] * 3


# ---- dsupdt_remotefile: checkLocalIndex / selectLocalIndex -----------------------

def test_select_local_index():
   page, _ = build('dsupdt_remotefile', 'add_row')
   info = page.select_local_index('lindex', '', {'dsid': ''})
   assert info['select_query'] == "select lindex, concat(dsid, ' - ', locfile) from dlupdt order by dsid, lindex"
   assert info['onchange'] is True and 'select_vals' not in info
   info = page.select_local_index('lindex', '', {'dsid': 'd083002'})
   assert info['select_query'] == 'select lindex, locfile from dlupdt where dsid = %s order by lindex'
   assert info['select_vals'] == ['d083002'] and info['onchange'] is False


def test_add_remotefile_refresh_uses_dataset():
   ret, db, _ = run('dsupdt_remotefile', 'add_row', {'dsid': 'd083002'})
   assert db.find('select lindex, locfile from dlupdt where dsid = %s')[0][1] == ['d083002']


def test_check_local_index():
   db = PageDB(lookups={'select dsid from dlupdt where lindex = %s': [{'dsid': 'd083002'}]})
   page, db = build('dsupdt_remotefile', 'add_row', db=db)
   assert page.check_local_index('lindex', '8', {'dsid': 'd083002'}) == '8'
   assert page.check_local_index('lindex', '8', {'dsid': 'd999999'}) == 0
   assert page.check_local_index('dsid', '', {'lindex': '8'}) == 'd083002'
   assert page.check_local_index('dsid', '', {'lindex': ''}) == ''
   assert db.find('select dsid from dlupdt where lindex = %s') == [
      ('select dsid from dlupdt where lindex = %s', ['8'])] * 3


# ---- dsrqst_control: setCarbonCopy and the shared group index callbacks ----------

def test_set_carbon_copy():
   assert DsrqstControl.set_carbon_copy('ccemail', 'S', {'ccemail': ''}) == 'N'
   assert DsrqstControl.set_carbon_copy('ccemail', 'S', {'ccemail': None}) == 'N'
   assert DsrqstControl.set_carbon_copy('ccemail', 'a@b.org', {'ccemail': 'a@b.org'}) == 'a@b.org'


def test_edit_request_control_carbon_copy_and_groups():
   db = PageDB(record={'cindex': 3, 'dsid': 'd083002', 'gindex': 0, 'ccemail': ''},
               lookups={'select count(*) from dsgroup': [{'count': 2}]})
   ret, db, page = run('dsrqst_control', 'edit_row', '3', db=db)
   html = layer(ret, 'recordLayer')
   assert 'id="ccemail"' in html and '>N</textarea>' in html
   assert db.find('select count(*) from dsgroup where dsid = %s')[0][1] == ['d083002']
   assert db.find('select gindex, title from dsgroup where dsid = %s')[0][1] == ['d083002']
   assert page.editor.columns['gindex']['val_fun'] == page.valid_group_index
