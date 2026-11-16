"""Request tar files (dssdb.tfrqst); port of dsrqst_tarfile.php."""

from ..editor.page import Page, php_empty


class DsrqstTarfile(Page):
   title = 'Tar File'

   def init_editor(self):
      dsid_fun = self.get_dataset_title
      columns = {
         'tindex': {'display_text': 'Tar File<br>Index', 'perms': '', 'description': 'Tar file index'},
         'wfile': {'display_text': 'Tarfile Name', 'perms': 'EHOSTVX',
                   'description': 'Tar file name', 'maxlen': 128, 'sub_str': 50,
                   'input_info': 'style="width: 200px" readonly="readonly"'},
         'rindex': {'display_text': 'Request<br>Index', 'perms': 'EHOSTVX',
                    'description': 'Request index', 'input_info': 'readonly="readonly"', 'valtype': 'integer'},
         'pindex': {'display_text': 'Partition<br>Index', 'perms': 'EHOSTVX',
                    'description': 'Partition index', 'input_info': 'readonly="readonly"', 'valtype': 'integer'},
         'dsid': {'display_text': 'DATASET<br>ID', 'perms': 'HOSTVX',
                  'description': 'Dataset Id for the request', 'view_fun': dsid_fun,
                  'join': {'table': 'dsrqst', 'column': 'rindex', 'real_column': 'rindex', 'display_mask': 'dsid'}},
         'gindex': {'display_text': 'gindex', 'perms': 'HOSTVX',
                    'description': 'if > 0, under a subgroup in a dataset', 'valtype': 'integer'},
         'size': {'display_text': 'Size', 'perms': 'HOSTVX',
                  'description': 'data file size', 'data_precision': 2},
         'date_time': {'display_text': 'Time File Staged', 'perms': 'HOSTVX',
                       'description': 'Time file is staged', 'display_mask': "concat(date, ' ', time)"},
         'disp_order': {'display_text': 'Display<br>Order', 'perms': 'EHOTVX',
                        'description': 'Display order index of the tar file', 'maxlen': 9, 'valtype': 'integer',
                        'default': 1},
         'data_format': {'display_text': 'Data<br>Format', 'perms': 'EHMOQSTVX',
                         'description': 'Data content format, i.e. NetCDF', 'maxlen': 10},
         'file_format': {'display_text': 'Archive<br>Format', 'perms': 'EHMOQSTVX',
                         'description': 'File archive format, i.e. GZ.TAR', 'maxlen': 10},
         'note': {'display_text': 'Description', 'perms': 'EHOTVX',
                  'description': 'Description of this tar file', 'sub_str': 30, 'textarea': self.text_area},
      }
      ed = self.make_editor('tfrqst', 'Requeset Tar File Information', 'tindex', 'EHMOSUVX', columns)
      ed.set_config('tableInfo', 'cellpadding="2" width="1400" class="mateTable"')
      ed.set_config('orderByColumn', 'tindex')
      ed.set_config('editRowTitle', 'Edit A Tar File')
      ed.set_config('viewRowTitle', 'View A Tar File')
      ed.set_config('editMultTitle', 'Set Comman Values for Multiple Tar Files')

   def get_dataset_title(self, col, val, row):
      if not php_empty(val):
         title = self.first('SELECT title FROM dataset WHERE dsid = %s', [val])
         if title is not None:
            val += ' - ' + title
      return val
