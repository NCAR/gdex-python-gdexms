# test_pages_dsarch2_dscheck.py: dsarch saved/backup/help/TACC file pages and dscheck daemon/history/hostname
# pages, with a fake database

import pytest

from gdex_python_gdexms.pages.dsarch_backupfile import DsarchBackupfile
from gdex_python_gdexms.pages.dsarch_helpfile import DsarchHelpfile
from gdex_python_gdexms.pages.dsarch_savedfile import DsarchSavedfile
from gdex_python_gdexms.pages.dsarch_taccfile import DsarchTaccfile
from gdex_python_gdexms.pages.dscheck_daemon import DscheckDaemon
from gdex_python_gdexms.pages.dscheck_history import DscheckHistory
from gdex_python_gdexms.pages.dscheck_hostname import DscheckHostname


class FakeDB:
   """Answers the engine's queries from canned rows/lookups and records every (sql, vals)."""

   def __init__(self, rows=None, lookups=None, record=None):
      self.rows = rows or []
      self.lookups = lookups or {}     # substring of SQL -> row dict
      self.record = record or {}       # row for 'select * from ... where <pkey> = %s'
      self.log = []

   def begin_request(self):
      pass

   def query(self, sql, vals=None):
      self.log.append((sql, list(vals or [])))
      s = ' '.join(sql.split())
      if 'mate_columns' in s:
         return []
      if 'count(*) as num_results' in s:
         return [{'num_results': len(self.rows)}]
      for key, row in self.lookups.items():
         if key in sql:
            return [row]
      if s.startswith('select * from'):
         return [dict(self.record)] if self.record else []
      if s.startswith('select') and '\nfrom dssdb.' in sql:
         return [dict(r) for r in self.rows]
      return []

   def query_one(self, sql, vals=None):
      rows = self.query(sql, vals)
      return rows[0] if rows else None

   def execute(self, sql, vals=None):
      self.log.append((sql, list(vals or [])))
      return 1

   def find(self, needle):
      return [entry for entry in self.log if needle in entry[0]]


def run(cls, action, info='', rows=None, lookups=None, record=None):
   db = FakeDB(rows, lookups, record)
   page = cls(db, {}, specialist='zji', page_url='/x.php', cookies={'mate_user_id': 'u1'},
              action=action, info=info)
   page.init_editor()
   ret = page.editor.main(action, info)
   return ret, db, page


def layer(ret, name):
   vals = [r['value'] for r in ret if r.get('layer_id') == name]
   return vals[-1] if vals else None


PAGES = [
   (DsarchSavedfile, 'sfile', 'sid', {'sid': 3, 'sfile': 'a/b.nc', 'dsid': 'd627000', 'status': 'P'},
    'Saved Glade-Disk/Object-Store File Information'),
   (DsarchBackupfile, 'bfile', 'bid', {'bid': 4, 'bfile': 'd627000_S_4.tar', 'dsid': 'd627000', 'status': 'A'},
    'Quasar Backup/Drdata File Information'),
   (DsarchHelpfile, 'hfile', 'hid', {'hid': 5, 'hfile': 'readme.pdf', 'dsid': 'd627000', 'status': 'P'},
    'Help File Information'),
   (DsarchTaccfile, 'tfile', 'tid', {'tid': 6, 'tfile': 'tacc.tar', 'dsid': 'd627000', 'status': 'T'},
    'TACC File Information'),
   (DscheckDaemon, 'dsdaemon', 'dindex', {'dindex': 1, 'command': 'ALL', 'hostname': 'casper'},
    'Dscheck Daemon Control Information'),
   (DscheckHistory, 'dschkhist', 'cindex', {'cindex': 9, 'command': 'dsarch', 'ttltime': 3725},
    'Check History'),
   (DscheckHostname, 'hostname', 'hostname', {'hostname': 'casper', 'service': 'B', 'note': 'PBS'},
    'Available Hostname Information'),
]


@pytest.mark.parametrize('cls,table,pkey,row,title', PAGES)
def test_update_html_renders_table(cls, table, pkey, row, title):
   ret, db, _ = run(cls, 'update_html', rows=[row])
   html = layer(ret, 'tableLayer')
   assert 'id="{0}-{1}_table_form"'.format(pkey, table) in html
   assert '>{}</td>'.format(row[pkey]) in html
   assert layer(ret, 'titleLayer') == title
   sql = db.find('limit %s offset %s')[-1][0]
   assert 'from dssdb.' + table in sql


@pytest.mark.parametrize('cls', [DsarchSavedfile, DsarchBackupfile, DsarchHelpfile, DsarchTaccfile])
def test_file_pages_filter_deleted_and_fix_titles(cls):
   ret, db, page = run(cls, 'update_html')
   assert "status <> 'D'" in db.find('limit %s offset %s')[-1][0]
   ed = page.editor
   assert ed.edit_row_title.startswith('Edit A ')
   assert ed.edit_mult_title.startswith('Set Common Values For Multiple ')


@pytest.mark.parametrize('cls,table,pkey,row,title', PAGES)
def test_edit_row_renders_form(cls, table, pkey, row, title):
   ret, db, page = run(cls, 'edit_row', str(row[pkey]), record=row)
   html = layer(ret, 'recordLayer')
   assert '<form id="{}-{}_edit_form"'.format(pkey, table) in html
   assert layer(ret, 'titleLayer') == page.editor.edit_row_title


@pytest.mark.parametrize('cls,table,pkey', [(DscheckDaemon, 'dsdaemon', 'dindex'),
                                            (DscheckHostname, 'hostname', 'hostname')])
def test_add_row_renders_form(cls, table, pkey):
   ret, db, page = run(cls, 'add_row')
   html = layer(ret, 'recordLayer')
   assert '<form id="{}-{}_add_form"'.format(pkey, table) in html
   assert layer(ret, 'titleLayer') == page.editor.add_row_title


@pytest.mark.parametrize('cls', [DsarchSavedfile, DsarchBackupfile, DsarchHelpfile, DsarchTaccfile,
                                 DscheckHistory])
def test_no_add_permission(cls):
   ret, _, _ = run(cls, 'add_row')
   assert layer(ret, 'recordLayer') is None or '_add_form' not in layer(ret, 'recordLayer')


def test_daemon_add_form_defaults_and_selects():
   ret, db, _ = run(DscheckDaemon, 'add_row')
   html = layer(ret, 'recordLayer')
   assert 'value="ALL"' in html
   assert '<option value="G" selected="selected">G - Match Hostname Generally</option>' in html
   assert any("service in ('A','W') ORDER by hostname" in s for s, _ in db.log)
   assert any(s.startswith('select logname') for s, _ in db.log)


def test_hostname_add_form_has_calendars():
   ret, _, _ = run(DscheckHostname, 'add_row')
   html = layer(ret, 'recordLayer')
   assert 'id="downstart"' in html and 'id="downend"' in html
   js = [r['value'] for r in ret if r['where'] == 'javascript']
   assert any('downstart' in s for s in js) and any('downend' in s for s in js)


def test_history_formats_intervals():
   rows = [{'cindex': 9, 'ttltime': 90061, 'quetime': 0}]
   ret, _, _ = run(DscheckHistory, 'update_html', rows=rows)
   assert '1D1H1N1S' in layer(ret, 'tableLayer')
   ret, _, _ = run(DscheckHistory, 'view_row', '9', rows=rows)
   assert '1D1H1N1S' in layer(ret, 'recordLayer')


# ---- lookup callbacks -----------------------------------------------------------

def page(cls, lookups):
   p = cls(FakeDB(lookups=lookups), {}, specialist='zji', page_url='/x.php')
   p.init_editor()
   return p, p.db


@pytest.mark.parametrize('cls', [DsarchSavedfile, DsarchBackupfile, DsarchHelpfile, DsarchTaccfile])
def test_dataset_title_and_specialist(cls):
   p, db = page(cls, {'FROM dataset WHERE': {'title': 'ERA5'},
                      'FROM dssdb.user WHERE': {'logname': 'zji', 'lstname': 'Ji', 'fstname': 'Zaihua'}})
   assert p.get_dataset_title('dsid', 'd627000', {}) == 'd627000 - ERA5'
   assert db.log[-1] == ('SELECT title FROM dataset WHERE dsid = %s', ['d627000'])
   assert p.get_specialist('uid', '12', {}) == '12 - zji (Zaihua Ji)'
   assert db.log[-1] == ('SELECT logname, lstname, fstname FROM dssdb.user WHERE uid = %s', ['12'])
   n = len(db.log)
   assert p.get_dataset_title('dsid', '', {}) == '' and p.get_specialist('uid', '0', {}) == '0'
   assert len(db.log) == n


def test_dataset_title_missing_record():
   p, db = page(DsarchHelpfile, {})
   assert p.get_dataset_title('dsid', "d1' or 1=1", {}) == "d1' or 1=1"
   assert db.log[-1][1] == ["d1' or 1=1"]


def test_savedfile_group_version_backup():
   p, db = page(DsarchSavedfile, {'FROM dsgroup WHERE': {'title': 'Surface'},
                                  'FROM dsvrsn WHERE': {'c': 'A - 10.5065/X'},
                                  'FROM bfile WHERE': {'c': 'd627000_S_4.tar - B'}})
   row = {'dsid': 'd627000', 'gindex': '2'}
   assert p.get_group_title('gindex', '2', row) == '2 - Surface'
   assert db.log[-1] == ('SELECT title FROM dsgroup WHERE gindex = %s AND dsid = %s', ['2', 'd627000'])
   n = len(db.log)
   assert p.get_group_title('tindex', '2', row) == '2'          # top group same as group: no lookup
   assert p.get_group_title('tindex', '1', {'gindex': '2'}) == '1'   # no dataset: no lookup
   assert len(db.log) == n
   assert p.get_group_title('tindex', '1', row) == '1 - Surface'
   assert p.get_version('vindex', '3', row) == '3 - A - 10.5065/X'
   assert db.log[-1] == ("SELECT concat(status, ' - ', doi) FROM dsvrsn WHERE vindex = %s", ['3'])
   assert p.get_back_file('bid', '4', row) == '4 - d627000_S_4.tar - B'
   assert db.log[-1] == ("SELECT concat(bfile, ' - ', type) FROM bfile WHERE bid = %s", ['4'])
   assert p.get_version('vindex', '0', row) == '0' and p.get_back_file('bid', '', row) == ''


def test_view_row_uses_lookups():
   rows = [{'sid': 3, 'dsid': 'd627000', 'uid': 12, 'gindex': 2, 'tindex': 1, 'vindex': 0, 'bid': 4}]
   lookups = {'FROM dataset WHERE': {'title': 'ERA5'}, 'FROM dsgroup WHERE': {'title': 'Surface'},
              'FROM bfile WHERE': {'c': 'x.tar - B'},
              'FROM dssdb.user WHERE': {'logname': 'zji', 'lstname': 'Ji', 'fstname': 'Zaihua'}}
   ret, db, _ = run(DsarchSavedfile, 'view_row', '3', rows=rows, lookups=lookups)
   html = layer(ret, 'recordLayer')
   assert 'd627000 - ERA5' in html and '12 - zji (Zaihua Ji)' in html
   assert '2 - Surface' in html and '1 - Surface' in html and '4 - x.tar - B' in html
