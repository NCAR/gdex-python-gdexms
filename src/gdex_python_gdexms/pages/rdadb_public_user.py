"""RDA public users (dssdb.wuser); port of rdadb_public_user.php."""

from ..editor.page import Page


class WebUser(Page):
   title = 'GDEX Public User'

   def init_editor(self):
      email = self.valid_email
      columns = {
         # the PHP misspelled the valtype 'interger', so its keypress check never ran
         'wuid': {'display_text': 'User Id', 'perms': 'EOSTVX',
                  'description': 'GDEX public user id, auto generated', 'valtype': 'integer'},
         'ruid': {'display_text': 'Registered<br>User ID', 'perms': 'HOSTVX',
                  'description': 'User id registered online at rda.ucar.edu if > 0', 'maxlen': 9,
                  'valtype': 'integer'},
         'email': {'display_text': 'Email Address', 'perms': 'ACEHOSTVX',
                   'description': 'User email address', 'maxlen': 80, 'sub_str': 40,
                   'input_info': 'style="width: 400px"', 'textarea': self.text_area, 'val_fun': email},
         'cdpname': {'display_text': 'CDP<br>Name', 'perms': 'HOSTVX',
                     'description': 'User name reqistered via CDP', 'maxlen': 64, 'sub_str': 20,
                     'input_info': 'style="width: 400px"'},
         'cdpid': {'display_text': 'CDP<br>ID', 'perms': 'HOSTVX',
                   'description': 'CDP user id', 'default': 0, 'maxlen': 9, 'valtype': 'integer'},
         'utitle': {'display_text': 'Name<br>Title', 'perms': 'ACEHMOSTVX',
                    'description': 'User name title, i.e. Dr.', 'maxlen': 4},
         'lstname': {'display_text': 'Last<br>Name', 'perms': 'ACEHOSTVX',
                     'description': 'User last name', 'maxlen': 30, 'sub_str': 20,
                     'input_info': 'style="width: 200px"'},
         'fstname': {'display_text': 'First<br>Name', 'perms': 'ACEHOSTVX',
                     'description': 'User first name', 'maxlen': 30, 'sub_str': 20,
                     'input_info': 'style="width: 200px"'},
         'midinit': {'display_text': 'MI', 'perms': 'ACEHMOSTVX',
                     'description': 'Middle name initial', 'maxlen': 1},
         'stat_flag': {'display_text': 'Status', 'perms': 'ACEHMOSTVX',
                       'description': 'Public User status', 'maxlen': 1, 'req': True,
                       'select_array': {'A': 'Active', 'C': 'Closed', 'I': 'Inactive', 'M': 'Missing Info'}},
         'org_type': {'display_text': 'Org.<br>Type', 'perms': 'ACEHMOSTVX',
                      'description': 'User organization type, i.e. UNIV', 'maxlen': 5, 'req': True,
                      'select_query': 'select org_type, description from org_type'},
         'org_name': {'display_text': 'Organization Name', 'perms': 'ACEHMOSTVX',
                      'description': 'Organization name user belongs to', 'maxlen': 128, 'sub_str': 20,
                      'input_info': 'style="width: 400px"', 'textarea': self.text_area},
         'country': {'display_text': 'Country Code', 'perms': 'ACEHMOSTVX',
                     'description': 'Country code user is from', 'maxlen': 30, 'sub_str': 20, 'req': True,
                     'select_query': 'select token, description from countries', 'query_column': 'token',
                     'default': 'UNITED.STATES'},
         'phoneno': {'display_text': 'Phone<br>Number', 'perms': 'ACEHOSTVX',
                     'description': 'User phone number', 'maxlen': 36, 'sub_str': 20,
                     'input_info': 'style="width: 200px"', 'valtype': 'phoneno'},
         'faxno': {'display_text': 'Fax<br>Number', 'perms': 'ACEHOSTVX',
                   'description': 'User fax number', 'maxlen': 36, 'sub_str': 20,
                   'input_info': 'style="width: 200px"', 'valtype': 'phoneno'},
         'start_date': {'display_text': 'Start Date', 'perms': 'ACEHMOSTVX',
                        'description': 'Account start date', 'input_info': 'style="width: 200px"',
                        'calendar': {'format': '%Y-%m-%d'}, 'req': True},
         'until_date': {'display_text': 'Close Date', 'perms': 'ACEHMOSTVX',
                        'description': 'account close date if set', 'input_info': 'style="width: 200px"',
                        'calendar': {'format': '%Y-%m-%d', 'reset': True}},
      }
      ed = self.make_editor('wuser', 'GDEX Public User Information', 'wuid', 'ACDEHMOSUVX', columns)
      ed.set_config('tableInfo', 'cellpadding="1" width="1600" class="mateTable"')
      ed.set_config('orderByColumn', 'wuid')
      ed.set_config('addRowTitle', 'Add A GDEX Public User')
      ed.set_config('editRowTitle', 'Edit A GDEX Public User')
      ed.set_config('viewRowTitle', 'View A GDEX Public User')
      ed.set_config('editMultTitle', 'Set Common Values for Multiple GDEX Public Users')
