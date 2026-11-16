"""Request files (dssdb.wfrqst); port of dsrqst_file.php."""

from ..editor.page import Page, php_empty


class DsrqstFile(Page):
   title = 'Request File'

   def init_editor(self):
      dsid_fun = self.get_dataset_title
      columns = {
         'findex': {'display_text': 'File Index', 'perms': '', 'description': 'Requeset file index'},
         'wfile': {'display_text': 'File Name', 'perms': 'EHOSTVX',
                   'description': 'Request ouput file name', 'maxlen': 128, 'sub_str': 50,
                   'input_info': 'style="width: 200px" readonly="readonly"'},
         'rindex': {'display_text': 'Request<br>Index', 'perms': 'EHOSTVX',
                    'description': 'Request index', 'input_info': 'readonly="readonly"', 'valtype': 'integer'},
         'pindex': {'display_text': 'Partition<br>Index', 'perms': 'EHOSTVX',
                    'description': 'Partition index', 'input_info': 'readonly="readonly"', 'valtype': 'integer'},
         'tindex': {'display_text': 'Tar File<br>Index', 'perms': 'EHOSTVX',
                    'description': 'Tar file index', 'input_info': 'readonly="readonly"', 'valtype': 'integer'},
         'dsid': {'display_text': 'DATASET<br>ID', 'perms': 'HOSTVX',
                  'description': 'Dataset Id for the request', 'view_fun': dsid_fun,
                  'join': {'table': 'dsrqst', 'column': 'rindex', 'real_column': 'rindex', 'display_mask': 'dsid'}},
         'gindex': {'display_text': 'gindex', 'perms': 'HOSTVX',
                    'description': 'if > 0, under a subgroup in a dataset', 'valtype': 'integer'},
         'srcid': {'display_text': 'Source<br>File ID', 'perms': 'HOSTVX',
                   'description': 'if > 0, source file id of HPSS/MSS or Web file', 'valtype': 'integer'},
         'srctype': {'display_text': 'Source<br>Type', 'perms': 'HOSTVX',
                     'description': 'Source data type', 'maxlen': 1,
                     'select_array': {'M': 'HPSS/MSS file', 'W': 'Web file', 'O': 'Other Type'}},
         'size': {'display_text': 'Size', 'perms': 'HOSTVX',
                  'description': 'data file size', 'data_precision': 2},
         'date_time': {'display_text': 'Time File Staged', 'perms': 'HOSTVX',
                       'description': 'Time file is staged', 'display_mask': "concat(date, ' ', time)"},
         'type': {'display_text': 'Type', 'perms': 'EHMOSTVX', 'description': 'File type',
                  'select_array': {'D': 'Data File', 'O': 'Document', 'S': 'Software'},
                  'default': 'D', 'maxlen': 1},
         'status': {'display_text': 'Status', 'perms': 'EHMOSTVX', 'description': 'File status',
                    'select_array': {'R': 'Request Initially', 'O': 'Staged Online', 'E': 'Error File Built'},
                    'default': 'R', 'maxlen': 1},
         'disp_order': {'display_text': 'Display<br>Order', 'perms': 'EHOTVX',
                        'description': 'Display order index of the file', 'maxlen': 9, 'valtype': 'integer',
                        'default': 1},
         'data_format': {'display_text': 'Data<br>Format', 'perms': 'EHMOQSTVX',
                         'description': 'Data content format, i.e. NetCDF', 'maxlen': 10},
         'file_format': {'display_text': 'Archive<br>Format', 'perms': 'EHMOQSTVX',
                         'description': 'File archive format, i.e. TAR.GZ', 'maxlen': 10},
         'command': {'display_text': 'Command To Process File', 'perms': 'ACEHMOQSTVX',
                     'description': 'Specify a customized commmand to to process one file',
                     'textarea': self.text_area, 'sub_str': 25, 'maxlen': 128},
         'ofile': {'display_text': 'Original<br>File Name', 'perms': 'HOSTVX',
                   'description': 'Original file name for format conversion', 'maxlen': 128, 'sub_str': 40},
         'note': {'display_text': 'Description', 'perms': 'EHOTVX',
                  'description': 'Description of this file', 'sub_str': 30, 'textarea': self.text_area},
      }
      ed = self.make_editor('wfrqst', 'Requeset File Information', 'findex', 'EHMOSUVX', columns)
      ed.set_config('tableInfo', 'cellpadding="2" width="1400" class="mateTable"')
      ed.set_config('orderByColumn', 'findex')
      ed.set_config('editRowTitle', 'Edit A Requeset File')
      ed.set_config('viewRowTitle', 'View A Requeset File')
      ed.set_config('editMultTitle', 'Set Comman Values for Multiple Request Files')

   def get_dataset_title(self, col, val, row):
      if not php_empty(val):
         title = self.first('SELECT title FROM dataset WHERE dsid = %s', [val])
         if title is not None:
            val += ' - ' + title
      return val
