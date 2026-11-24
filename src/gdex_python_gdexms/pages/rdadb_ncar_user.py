"""RDA NCAR users (dssdb.user); port of rdadb_ncar_user.php."""

from ..editor.page import Page


class MSSUser(Page):
   title = 'GDEX NCAR User'

   def init_editor(self):
      email = self.valid_email
      columns = {
         'uid': {'display_text': 'User<br>Id', 'perms': 'EOSTVX',
                 'description': 'GDEX user ID with NCAR computer account', 'maxlen': 9, 'valtype': 'integer'},
         'upid': {'display_text': 'UCAR<br>DB ID', 'perms': 'EHOSTVX',
                  'description': 'Unique id in UCAR people database if set', 'maxlen': 9, 'valtype': 'integer'},
         'userno': {'display_text': 'System<br>ID', 'perms': 'EHOSTVX',
                    'description': 'NCAR computer system user id', 'maxlen': 9, 'valtype': 'integer'},
         'logname': {'display_text': 'Login<br>Name', 'perms': 'EHOSTVX',
                     'description': 'NCAR computer system login user name', 'maxlen': 20},
         'lstname': {'display_text': 'Last Name', 'perms': 'EHOSTVX', 'req': True,
                     'description': 'User last name', 'maxlen': 30, 'sub_str': 20,
                     'input_info': 'style="width: 200px"'},
         'fstname': {'display_text': 'First Name', 'perms': 'EHOSTVX', 'req': True,
                     'description': 'User first name', 'maxlen': 30, 'sub_str': 20,
                     'input_info': 'style="width: 200px"'},
         'midinit': {'display_text': 'MI', 'perms': 'EHOSTVX',
                     'description': 'User middle name initital', 'maxlen': 1},
         'stat_flag': {'display_text': 'Status', 'perms': 'EHMOSTVX',
                       'description': 'GDEX NCAR User status', 'maxlen': 1, 'req': True,
                       'select_array': {'A': 'Active', 'C': 'Closed', 'I': 'Inactive', 'M': 'Missing Info'}},
         'division': {'display_text': 'Division', 'perms': 'EHMOSTVX',
                      'description': 'NCAR Division/Lab name', 'maxlen': 5},
         'org_type': {'display_text': 'Org.<br>Type', 'perms': 'EHMOSTVX',
                      'description': 'User organization type, i.e. NCAR, UNIV', 'maxlen': 5, 'req': True,
                      'select_query': 'select org_type, description from org_type'},
         'org_name': {'display_text': 'Organization Name', 'perms': 'EHMOSTVX',
                      'description': 'Organization name user belongs to', 'maxlen': 128, 'sub_str': 20,
                      'input_info': 'style="width: 400px"', 'textarea': self.text_area},
         'country': {'display_text': 'Country Code', 'perms': 'EHMOSTVX',
                     'description': 'Country code user is from', 'maxlen': 30, 'sub_str': 20, 'req': True,
                     'select_query': 'select token, description from countries', 'query_column': 'token',
                     'default': 'UNITED.STATES'},
         'email': {'display_text': 'User Email', 'perms': 'EHOSTVX',
                   'description': 'User email to receive notice', 'maxlen': 80, 'sub_str': 20, 'req': True,
                   'input_info': 'style="width: 400px"', 'textarea': self.text_area, 'val_fun': email},
         'ucaremail': {'display_text': 'UCAR Email', 'perms': 'EHOSTVX',
                       'description': 'UCAR email address', 'maxlen': 80, 'sub_str': 20,
                       'input_info': 'style="width: 400px"', 'textarea': self.text_area, 'val_fun': email},
         'phoneno': {'display_text': 'Phone<br>Number', 'perms': 'EHOSTVX',
                     'description': 'User phone number', 'maxlen': 36, 'sub_str': 20,
                     'input_info': 'style="width: 200px"', 'valtype': 'phoneno'},
         'faxno': {'display_text': 'Fax<br>Number', 'perms': 'EHOSTVX',
                   'description': 'User fax number', 'maxlen': 36, 'sub_str': 20,
                   'input_info': 'style="width: 200px"', 'valtype': 'phoneno'},
         'start_date': {'display_text': 'Start Date', 'perms': 'EHMOSTVX',
                        'description': 'Account start date', 'input_info': 'style="width: 200px"',
                        'calendar': {'format': '%Y-%m-%d'}, 'req': True},
         'until_date': {'display_text': 'Close Date', 'perms': 'EHMOSTVX',
                        'description': 'account close date if set', 'input_info': 'style="width: 200px"',
                        'calendar': {'format': '%Y-%m-%d', 'reset': True}},
      }
      ed = self.make_editor('user', 'GDEX NCAR User Information', 'uid', 'EHMOSUVX', columns)
      ed.set_config('tableInfo', 'cellpadding="2" width="1600" class="mateTable"')
      ed.set_config('orderByColumn', 'uid')
      ed.set_config('addRowTitle', 'Add A GDEX NCAR User')
      ed.set_config('editRowTitle', 'Edit A GDEX NCAR User')
      ed.set_config('viewRowTitle', 'View A GDEX NCAR User')
      ed.set_config('editMultTitle', 'Set Common Values for Multiple GDEX NCAR Users')
