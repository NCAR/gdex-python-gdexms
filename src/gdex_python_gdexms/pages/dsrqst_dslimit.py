"""Dataset request limits (dssdb.dslimit); port of dsrqst_dslimit.php."""

from ..editor.page import Page, php_empty


class DsrqstDslimit(Page):
   title = 'Dataset Request Limit'

   def init_editor(self):
      columns = {
         'dsid': {'display_text': 'Dataset<br>ID', 'perms': 'AEOQSTVX',
                  'description': 'Dataset Identification Number, all for all datasets',
                  'input_info': "style='width: 400px'", 'val_fun': self.valid_dataset_id},
         'processlimit': {'display_text': 'Process<br>Limit', 'perms': 'ACEHMOQSTVX',
                          'description': 'Up Limit of requests can be processd for a given datasest', 'default': 45,
                          'valtype': 'integer'},
         'note': {'display_text': 'Description', 'perms': 'ACEHOQSTVX',
                  'description': 'Description for the dataset request limit record', 'textarea': self.text_area,
                  'sub_str': 25},
      }
      ed = self.make_editor('dslimit', 'Dataset Limit Information', 'dsid', 'ACDEHMOSUVX', columns)
      ed.set_config('tableInfo', 'cellpadding="2" width="1500" class="mateTable"')
      ed.set_config('orderByColumn', 'dsid')
      ed.set_config('addRowTitle', 'Add A Dataset Limit')
      ed.set_config('editRowTitle', 'Edit A Dataset Limit')
      ed.set_config('editMultTitle', 'Set Comman Values for Multiple Dataset Limits')
      ed.set_config('viewRowTitle', 'View A Dataset Limit')

   def valid_dataset_id(self, col, val, row):
      """val_fun: empty, 'all', or an existing dataset id."""
      if php_empty(val) or val == 'all':
         return True
      return self.first('select dsid from dataset where dsid = %s', [val]) is not None
