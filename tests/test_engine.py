# test_engine.py: table editor engine, pilot pages and Flask routes, with a fake database

import json
import re

import pytest

from gdex_python_gdexms.app import create_app
from gdex_python_gdexms.editor.engine import TableEditor, format_data_size, format_size
from gdex_python_gdexms.pages import PAGES


class FakeDB:
   """Answers the engine's queries from canned rows and records every (sql, vals)."""

   def __init__(self, rows=None, lookups=None):
      self.rows = rows or []
      self.lookups = lookups or {}     # substring of SQL -> row dict
      self.log = []

   def begin_request(self):
      pass

   def query(self, sql, vals=None):
      self.log.append((sql, list(vals or [])))
      if 'mate_columns' in sql:
         return []
      if 'count(*) as num_results' in sql:
         return [{'num_results': len(self.rows)}]
      if 'as total_' in sql:
         return [{'total_count': 7, 'total_size': 3 * 1048576}]
      for key, row in self.lookups.items():
         if key in sql:
            return [row]
      if sql.lstrip().startswith('select') and '\nfrom dssdb.' in sql:
         return [dict(r) for r in self.rows]
      return []

   def query_one(self, sql, vals=None):
      rows = self.query(sql, vals)
      return rows[0] if rows else None

   def last(self, needle):
      return [entry for entry in self.log if needle in entry[0]][-1]


ORG_ROWS = [{'org_type': 'NCAR', 'description': 'NCAR staff'}, {'org_type': 'UNIV', 'description': 'University'}]


def run(page_name, action, info='', rows=None, session=None, lookups=None, user='zji'):
   db = FakeDB(rows, lookups)
   session = {} if session is None else session
   page = PAGES[page_name](db, session, specialist=user, page_url='/' + page_name + '.php',
                           action=action, info=info)
   page.init_editor()
   ret = page.editor.main(action, info)
   return ret, db, session, page


def layer(ret, name):
   return [r['value'] for r in ret if r.get('layer_id') == name][-1]


def scripts(ret):
   return [r['value'] for r in ret if r['where'] == 'javascript']


def test_update_html_lists_rows_and_controls():
   ret, db, _, _ = run('rdadb_org_type', 'update_html', rows=ORG_ROWS)
   table = layer(ret, 'tableLayer')
   assert 'id="org_type-org_type_table_form"' in table and '>NCAR</td>' in table and '>University</td>' in table
   assert 'order_by_changed' in table and '&uarr;' in table
   assert layer(ret, 'recordLayer') == ''          # cleared after the record count is shown
   assert 'Displaying 1 - 2 of 2 Records' in [r['value'] for r in ret if r.get('layer_id') == 'recordLayer'][0]
   assert 'Page #:' in layer(ret, 'searchButtonsLayer') and 'Summary' in layer(ret, 'searchButtonsLayer')
   assert layer(ret, 'titleLayer') == 'Organization Type Information'
   assert "set_view_interval('update_html', 'org_type-org_type', 0);" in scripts(ret)
   sql, vals = db.last('limit %s offset %s')
   assert 'order by org_type asc' in sql and vals == [20, 0]


def test_quick_search_binds_value():
   session = {}
   ret, db, session, _ = run('dsarch_webfile', 'set_dsid', "d627000", session=session)
   ret, db, session, _ = run('dsarch_webfile', 'handle_search', "nc'; drop", session=session,
                             rows=[{'wid': 1, 'data_format': 'NetCDF', 'file_format': None}])
   sql, vals = db.last('limit %s offset %s')
   assert 'from dssdb.wfile_d627000' in sql
   assert '"' not in sql and "drop" not in sql
   assert sql.count('like %s') == 3 and ' or\n' in sql            # tindex, data_format, file_format
   assert vals[:3] == ["%nc'; drop%"] * 3
   assert "status <> 'D'" in sql


def test_advanced_search_ops_and_rejects_unknown():
   info = {'0': {'cols': 'description', 'opts': 'like', 'strs': ' staff '},
           '1': {'cols': 'org_type', 'opts': 'between', 'strs': "'A' and 'N'"},
           '2': {'cols': 'org_type', 'opts': '=; drop table x', 'strs': 'x'},
           '3': {'cols': 'nosuch', 'opts': '=', 'strs': 'x'}}
   ret, db, session, _ = run('rdadb_org_type', 'advanced_search', info, rows=ORG_ROWS)
   sql, vals = db.last('limit %s offset %s')
   assert '"dssdb.org_type.description" like %s' not in sql
   assert 'dssdb.org_type.description like %s and\ndssdb.org_type.org_type between %s and %s' in sql
   assert vals == ['%staff%', 'A', 'N', 20, 0]
   assert 'drop' not in sql and 'nosuch' not in sql
   assert len(session['org_type-org_typeadvSearches']) == 4


def test_order_by_rejects_unknown_column():
   session = {}
   run('rdadb_org_type', 'order_by_changed', ['description', 'desc'], rows=ORG_ROWS, session=session)
   assert session['org_type-org_typeobc'] == 'description' and session['org_type-org_typeaod'] == 'desc'
   _, db, _, _ = run('rdadb_org_type', 'order_by_changed', ['1; drop table x', 'asc'], rows=ORG_ROWS, session=session)
   assert 'order by description desc' in db.last('limit %s offset %s')[0]


def test_paging_and_display_number():
   session = {}
   rows = [{'org_type': 'T%d' % i, 'description': 'd'} for i in range(45)]
   ret, db, session, _ = run('rdadb_org_type', 'display_num_changed', '10', rows=rows, session=session)
   assert session['org_type-org_typedisplayNum'] == 10
   ret, db, session, _ = run('rdadb_org_type', 'page_num_changed', '30', rows=rows, session=session)
   assert db.last('limit %s offset %s')[1] == [10, 30]
   buttons = layer(ret, 'searchButtonsLayer')
   assert '<option value="30" selected="selected" style="font-weight: bold">4</option>' in buttons
   assert '<option value="10" selected="selected">10</option>' in buttons


def test_view_row_formats_values():
   rows = [{'cindex': 5, 'status': 'R', 'size': 2500000, 'dscheck': '123 PBS', 'pindex': 0, 'dsid': 'd627000'}]
   lookups = {'from dscheck where cindex': {'subtime': 0, 'stttime': 0, 'runhost': 'casper',
                                            'dcount': 5, 'fcount': 10, 'command': 'dsarch', 'oindex': 0,
                                            'otype': None}}
   ret, db, _, _ = run('dscheck_check', 'view_row', '5', rows=rows, lookups=lookups)
   html = layer(ret, 'recordLayer')
   assert db.last('dssdb.dscheck.cindex = %s')[1] == ['5']
   assert 'R - Running' in html and '2.5MB' in html
   assert 'PBS(123/casper), 50% done' in html
   assert "set_view_interval('view_row', '5', 30);" in scripts(ret)


def test_view_row_gone_record():
   ret, _, _, _ = run('rdadb_org_type', 'view_row', 'NOPE', rows=[])
   assert scripts(ret)[0].startswith("toAjaxTableEditor('update_html','View screen was closed")


def test_summary_and_export():
   rows = [{'cindex': 1, 'command': 'dsarch', 'argv': 'a "q"\nb', 'size': 10}]
   ret, _, _, _ = run('dscheck_check', 'show_summary', rows=rows)
   html = layer(ret, 'recordLayer')
   assert 'Total Records:</b></td><td>1</td>' in html
   assert 'Total FileCount:</b></td><td>7</td>' in html and 'Total DataSize:</b></td><td>3.00 MB</td>' in html
   db = FakeDB(rows)
   page = PAGES['dscheck_check'](db, {}, specialist='zji', page_url='/dscheck_check.php')
   page.init_editor()
   csv = page.editor.export_info()
   assert csv.startswith('"Check<br>Index","Command","Command Argument Options"')
   assert '"1","dsarch","a ""q""b"' in csv and csv.endswith('\r\n')


def test_webfile_requires_valid_dsid():
   ret, _, session, _ = run('dsarch_webfile', 'update_html')
   assert layer(ret, 'tableLayer') == '<b>Please enter a Dataset ID to view records.</b>'
   ret, _, session, _ = run('dsarch_webfile', 'set_dsid', 'ds083.2', session={})
   assert session['wfile_dsid'] == '' and any('Invalid dataset id' in s for s in scripts(ret))


def test_write_actions_answer_not_yet():
   ret, db, _, _ = run('rdadb_org_type', 'delete_row', 'NCAR', rows=ORG_ROWS)
   assert any('not available yet' in s for s in scripts(ret))
   assert not any(sql.lstrip().lower().startswith(('update', 'delete', 'insert')) for sql, _ in db.log)


def test_format_helpers():
   assert format_data_size('2500000', 1) == '2.5MB' and format_data_size('', 1) == '0.0B'
   assert format_size(None) == 'N/A' and format_size(1536) == '1,536 B'


# ---- Flask routes ---------------------------------------------------------------

@pytest.fixture
def client():
   db = FakeDB(ORG_ROWS)
   app = create_app({'TESTING': True, 'SECRET_KEY': 'test', 'DEV_USER': 'zji', 'GET_DB': lambda: db})
   return app.test_client()


def test_routes(client):
   page = client.get('/rdadb_org_type.php')
   assert page.status_code == 200 and b'var ajaxUrl = "/rdadb_org_type.php";' in page.data
   resp = client.post('/rdadb_org_type.php', data={'json': json.dumps({'action': 'update_html', 'info': ''})})
   assert resp.status_code == 200 and any(r.get('layer_id') == 'tableLayer' for r in resp.get_json())
   assert 'mate_user_id=' in resp.headers.get('Set-Cookie', '')
   csv = client.get('/rdadb_org_type.php?export=1')
   assert csv.mimetype == 'text/csv' and b'"NCAR","NCAR staff"' in csv.data
   assert client.get('/js/ajax_table_editor.js').status_code == 200
   assert client.get('/css/table_styles.css').status_code == 200
   assert client.get('/nosuch.php').status_code == 404
   menu = client.get('/')
   assert b'href="rdadb_org_type.php"' in menu.data and b'Not ported yet' in menu.data


def test_requires_user():
   app = create_app({'TESTING': True, 'SECRET_KEY': 'test', 'DEV_USER': None})
   c = app.test_client()
   assert c.get('/rdadb_org_type.php').status_code == 401
   assert c.get('/healthz').status_code == 200
