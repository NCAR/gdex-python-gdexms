"""DSS specialists (dssdb.dssgrp); port of rdadb_specialist.php."""

from ..editor.page import Page


class DssSpecialist(Page):
   title = 'Specialist'

   def init_editor(self):
      columns = {
         'logname': {'display_text': 'Specialist<br>Login Name', 'perms': 'AEOSTVX',
                     'description': 'Specialist login name on NCAR computer sysetem', 'req': True, 'maxlen': 20},
         'userno': {'display_text': 'User<br>ID', 'perms': 'AEOQSTVX',
                    'description': 'User ID on NCAR computer sysetem', 'valtype': 'integer', 'maxlen': 6},
         'lstname': {'display_text': 'Last<br>Name', 'perms': 'ACEHOQSTVX',
                     'description': 'Specialist last name', 'req': True, 'maxlen': 20},
         'fstname': {'display_text': 'First<br>Name', 'perms': 'ACEHOQSTVX',
                     'description': 'Specialist first name', 'req': True, 'maxlen': 20},
         'midinit': {'display_text': 'MI', 'perms': 'ACEHOQSTVX',
                     'description': 'Middle name initial', 'maxlen': 1},
         'stat_flag': {'display_text': 'Status', 'perms': 'ACEHMOSTVX',
                       'description': 'Employment Status', 'default': 'C', 'req': True, 'maxlen': 1,
                       'select_array': {'C': 'Currently Active DSS Specialist', 'A': 'Active but not Not in DSS',
                                        'I': 'Inactive Specialist'}},
         'email_flag': {'display_text': 'Email<br>Flag', 'perms': 'ACEHMOSTVX',
                        'description': 'Send email notice for weekly data usage update',
                        'default': 'N', 'req': True, 'maxlen': 1,
                        'select_array': {'N': 'No Weekly Email Notice', 'Y': 'Receive Weekly Email Notice'}},
         'role': {'display_text': 'Role', 'perms': 'ACEHMOSTVX', 'maxlen': 1,
                  'description': 'Role specialist plays', 'default': 'S', 'req': True,
                  'select_array': {'M': 'Manager', 'A': 'Assitant', 'S': 'Specialist',
                                   'R': 'Retired', 'T': 'Temporary', 'O': ' Other'}},
         'shell_flag': {'display_text': 'Shell<br>Flag', 'perms': 'ACEHOSTVX',
                        'description': 'Login Shell Name', 'maxlen': 1, 'default': 'T',
                        'select_array': {'T': 'Tcsh Shell', 'B': 'Bash Shell'}},
         'officeno': {'display_text': 'Office No.', 'perms': 'ACEHOSTVX',
                      'description': 'office Number', 'maxlen': 6},
         'phoneno': {'display_text': 'Phone Number', 'perms': 'ACEHOSTVX',
                     'description': 'Office Phone Number', 'maxlen': 36, 'valtype': 'phoneno'},
         'workstation': {'display_text': 'Laptop Name', 'perms': 'ACEHOSTVX',
                         'description': 'working laptop name', 'maxlen': 20},
      }
      ed = self.make_editor('dssgrp', 'DSS Specialist Information', 'logname', 'ACEHMOSUVX', columns)
      ed.set_config('tableInfo', 'cellpadding="2" width="1000" class="mateTable"')
      ed.set_config('orderByColumn', 'logname')
      ed.set_config('addRowTitle', 'Add A Specialist')
      ed.set_config('editRowTitle', 'Edit A Specialist')
      ed.set_config('editMultTitle', 'Set Comman Values for Multiple Specialists')
      ed.set_config('viewRowTitle', 'View A Specialist')
