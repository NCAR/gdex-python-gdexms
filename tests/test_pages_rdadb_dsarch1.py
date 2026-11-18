# test_pages_rdadb_dsarch1.py: rdadb_specialist, rdadb_ncar_user, rdadb_public_user,
# dsarch_dataset, dsarch_group and dsarch_version pages, with fake databases

import pytest

from gdex_python_gdexms.pages.dsarch_dataset import Dataset
from gdex_python_gdexms.pages.dsarch_group import DsarchGroup
from gdex_python_gdexms.pages.dsarch_version import DsarchVersion
from gdex_python_gdexms.pages.rdadb_ncar_user import MSSUser
from gdex_python_gdexms.pages.rdadb_public_user import WebUser
from gdex_python_gdexms.pages.rdadb_specialist import DssSpecialist
from tests.test_edit import WriteDB
from tests.test_engine import FakeDB


def run(cls, action, info='', db=None, session=None):
   db = db if db is not None else FakeDB()
   session = {} if session is None else session
   page = cls(db, session, specialist='zji', page_url='/x.php', cookies={'mate_user_id': 'u1'},
              action=action, info=info)
   page.init_editor()
   ret = page.editor.main(action, info)
   return ret, db, page


def layer(ret, name):
   vals = [r['value'] for r in ret if r.get('layer_id') == name]
   return vals[-1] if vals else None


ROWS = {
   DssSpecialist: [{'logname': 'zji', 'lstname': 'Ji', 'fstname': 'Zaihua', 'stat_flag': 'C', 'role': 'S'}],
   MSSUser: [{'uid': '7', 'logname': 'zji', 'lstname': 'Ji', 'fstname': 'Zaihua', 'stat_flag': 'A'}],
   WebUser: [{'wuid': '11', 'email': 'a@b.edu', 'lstname': 'Doe', 'stat_flag': 'A'}],
   Dataset: [{'dsid': 'd627000', 'specialist': 'zji', 'dstype': 'P', 'webpath': 'd627000'}],
   DsarchGroup: [{'gidx': '3', 'gindex': '1', 'dsid': 'd627000', 'title': 'Group one', 'grptype': 'P'}],
   DsarchVersion: [{'vindex': '5', 'dsid': 'd627000', 'status': 'A', 'doi': '10.5065/X'}],
}
TITLES = {DssSpecialist: 'DSS Specialist Information', MSSUser: 'RDA NCAR User Information',
          WebUser: 'RDA Public User Information', Dataset: 'Dataset Information',
          DsarchGroup: 'Dataset Group Information', DsarchVersion: 'DOI Version Control Information'}
TABLES = {DssSpecialist: 'dssgrp', MSSUser: 'user', WebUser: 'wuser', Dataset: 'dataset',
          DsarchGroup: 'dsgroup', DsarchVersion: 'dsvrsn'}


@pytest.mark.parametrize('cls', list(ROWS))
def test_update_html_renders_table(cls):
   ret, db, _ = run(cls, 'update_html', db=FakeDB(ROWS[cls]))
   table = layer(ret, 'tableLayer')
   assert 'mateTable' in table and '<tr' in table
   assert layer(ret, 'titleLayer') == TITLES[cls]
   sql, _ = db.last('limit %s offset %s')
   assert 'from dssdb.' + TABLES[cls] in sql


@pytest.mark.parametrize('cls', [DssSpecialist, WebUser, DsarchGroup])
def test_add_row_renders_form(cls):
   ret, db, page = run(cls, 'add_row')
   html = layer(ret, 'recordLayer')
   assert '_add_form"' in html
   assert layer(ret, 'titleLayer') == page.editor.add_row_title


@pytest.mark.parametrize('cls', [MSSUser, Dataset, DsarchVersion])
def test_no_add_permission(cls):
   ret, _, _ = run(cls, 'add_row')
   assert not (layer(ret, 'recordLayer') or '').count('_add_form"')


@pytest.mark.parametrize('cls,rec', [
   (DssSpecialist, {'logname': 'zji', 'lstname': 'Ji'}),
   (MSSUser, {'uid': 7, 'email': 'zji@ucar.edu'}),
   (WebUser, {'wuid': 11, 'email': 'a@b.edu'}),
   (Dataset, {'dsid': 'd627000', 'webpath': 'd627000'}),
   (DsarchGroup, {'gidx': 3, 'dsid': 'd627000', 'gindex': 1}),
   (DsarchVersion, {'vindex': 5, 'dsid': 'd627000'}),
])
def test_edit_row_renders_form(cls, rec):
   pkey = list(rec)[0]
   ret, _, page = run(cls, 'edit_row', str(rec[pkey]), db=WriteDB(record=rec))
   html = layer(ret, 'recordLayer')
   assert '_edit_form"' in html
   assert layer(ret, 'titleLayer') == page.editor.edit_row_title


def test_specialist_select_arrays_and_titles():
   ret, _, page = run(DssSpecialist, 'add_row')
   html = layer(ret, 'recordLayer')
   assert '<option value="M">M - Manager</option>' in html
   assert page.editor.edit_mult_title == 'Set Comman Values for Multiple Specialists'


def test_ncar_user_email_validation_refuses_bad_address():
   db = WriteDB(record={'uid': 7})
   info = {'old_primary_key_value': '7', 'email': 'not-an-address', 'lstname': 'Ji', 'fstname': 'Z',
           'stat_flag': 'A', 'org_type': 'NCAR', 'country': 'UNITED.STATES', 'start_date': '2020-01-01'}
   ret, db, _ = run(MSSUser, 'update_row', info, db=db)
   assert not db.writes()
   assert 'Please correct the fields in red' in layer(ret, 'titleLayer')


def test_public_user_email_ok_and_insert():
   info = {'email': 'jane@univ.edu', 'lstname': 'Doe', 'stat_flag': 'A', 'org_type': 'UNIV',
           'country': 'UNITED.STATES', 'start_date': '2020-01-01'}
   _, db, page = run(WebUser, 'insert_row', info, db=WriteDB())
   ins = [w for w in db.writes() if w[0].startswith('insert into dssdb.wuser')]
   assert ins and 'jane@univ.edu' in ins[0][1]
   assert page.editor.columns['wuid']['valtype'] == 'integer'


def test_dataset_join_and_type_view():
   _, db, page = run(Dataset, 'update_html', db=FakeDB(ROWS[Dataset]))
   sql, _ = db.last('limit %s offset %s')
   assert 'left join search.datasets as datasets_j1 on dssdb.dataset.dsid = datasets_j1.dsid' in sql
   assert 'left join dsowner as dsowner_j0 on dssdb.dataset.dsid = dsowner_j0.dsid' in sql
   assert 'type as dstype' in sql
   assert 'substring' not in sql
   assert 'priority = 1' in sql
   fun = page.editor.columns['dstype']['view_fun']
   assert fun('dstype', 'P', {}) == 'P - Public Dataset'
   assert fun('dstype', 'H', {}) == 'H - Historic Dataset'
   assert fun('dstype', 'I', {}) == 'I - Internal Dataset'
   assert fun('dstype', 'X', {}) == 'X'


def test_dataset_update_bumps_version():
   db = WriteDB(record={'dsid': 'd627000'})
   info = {'old_primary_key_value': 'd627000', 'dsid': 'd627000', 'webpath': 'new/path'}
   run(Dataset, 'update_row', info, db=db)
   writes = db.writes()
   assert writes[0] == ('update dssdb.dataset set dsid = %s, webpath = %s where dsid in (%s)',
                        ['d627000', 'new/path', 'd627000'])
   assert writes[1] == ('UPDATE dssdb.dataset SET version = version + 1 WHERE dsid = %s', ['d627000'])


def test_group_titles_and_dsid_select():
   ret, db, page = run(DsarchGroup, 'add_row')
   assert page.editor.edit_row_title == 'Edit A Group'
   assert page.editor.edit_mult_title == 'Set Common Values for Multiple Groups'
   assert any(sql.startswith('select dsid, title from search.datasets') for sql, _ in db.log)
   assert 'id="gidx"' not in layer(ret, 'recordLayer')


def test_version_display_masks():
   _, db, _ = run(DsarchVersion, 'update_html', db=FakeDB(ROWS[DsarchVersion]))
   sql, _ = db.last('limit %s offset %s')
   assert "concat(start_date, ' ', start_time)" in sql and "concat(end_date, ' ', end_time)" in sql
