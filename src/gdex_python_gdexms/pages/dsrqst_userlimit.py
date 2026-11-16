"""User request limits (dssdb.userlimit); port of dsrqst_userlimit.php."""

from ..editor.page import Page, php_empty


class DsrqstUserlimit(Page):
   title = 'User Request Limit'

   def init_editor(self):
      columns = {
         'email': {'display_text': 'Email Address', 'perms': 'AEHOSTVX',
                   'description': 'User email address, all for all users', 'sub_str': 40,
                   'input_info': 'style="width: 400px"', 'textarea': self.text_area,
                   'val_fun': self.valid_user_email},
         'maxrqstcheck': {'display_text': 'Request<br>Checks', 'perms': 'ACEHMOQSTVX',
                          'description': 'Maximum request checks from one user; defaults to 10', 'default': 10,
                          'valtype': 'integer'},
         'maxpartcheck': {'display_text': 'Partition<br>Checks', 'perms': 'ACEHMOQSTVX',
                          'description': 'Maximum request partition checks from one user; defaults to 36',
                          'default': 36, 'valtype': 'integer'},
         'note': {'display_text': 'Description', 'perms': 'ACEHOQSTVX',
                  'description': 'Description for the user request limit record', 'textarea': self.text_area,
                  'sub_str': 25},
      }
      ed = self.make_editor('userlimit', 'User Request Limit Information', 'email', 'ACDEHMOSUVX', columns)
      ed.set_config('tableInfo', 'cellpadding="2" width="1500" class="mateTable"')
      ed.set_config('orderByColumn', 'email')
      ed.set_config('addRowTitle', 'Add A User Request Limit')
      ed.set_config('editRowTitle', 'Edit A User Request Limit')
      ed.set_config('editMultTitle', 'Set Comman Values for Multiple User Request Limits')
      ed.set_config('viewRowTitle', 'View A User Request Limit')

   def valid_user_email(self, col, val, row):
      """val_fun: empty, 'all', or a plausible email address."""
      if php_empty(val) or val == 'all':
         return True
      return self.valid_email(col, val, row)
