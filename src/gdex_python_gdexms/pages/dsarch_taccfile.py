"""TACC tar files (dssdb.tfile); port of dsarch_taccfile.php."""

from ..editor.page import Page, php_empty


class DsarchTaccfile(Page):
   title = 'TACC Files'

   def init_editor(self):
      dsid, uid = self.get_dataset_title, self.get_specialist
      columns = {
         'tid': {'display_text': 'TACC<br>ID', 'perms': 'EOSTVX', 'description': 'TACC File ID',
                 'valtype': 'integer'},
         'tfile': {'display_text': 'TACC File Name', 'perms': 'EHOSTVX',
                   'description': 'TACC file name, cannot be changed', 'maxlen': 128, 'sub_str': 50,
                   'input_info': 'style="width: 400px" readonly="readonly"', 'textarea': self.text_area},
         'uid': {'display_text': 'Owner<br>ID', 'perms': 'HOSTVX', 'valtype': 'integer',
                 'description': 'Specialist internal ID who owns this file', 'view_fun': uid},
         'dsid': {'display_text': 'Dataset<br>ID', 'perms': 'HOSTVX',
                  'description': 'Dataset Identification Number', 'maxlen': 9, 'view_fun': dsid},
         'data_size': {'display_text': 'Size', 'perms': 'HOSTVX', 'description': 'File size', 'data_precision': 2},
         'date_created': {'display_text': 'Time File Created', 'perms': 'HOSTVX',
                          'description': 'Time file was initially created',
                          'display_mask': "concat(date_created, ' ', time_created)"},
         'date_modified': {'display_text': 'Time File Modified', 'perms': 'HOSTVX',
                           'description': 'Time file was most recently modified',
                           'display_mask': "concat(date_modified, ' ', time_modified)"},
         'data_format': {'display_text': 'Data<br>Format', 'perms': 'EHMOQSTVX',
                         'description': 'Data content format, i.e. NetCDF', 'maxlen': 20},
         'file_format': {'display_text': 'Archive<br>Format', 'perms': 'EHMOQSTVX',
                         'description': 'File archive format, i.e. TAR.GZ', 'maxlen': 20},
         'checksum': {'display_text': 'MD5<br>Checksum', 'perms': 'HOSTVX',
                      'description': 'File md5 checksum', 'sub_str': 10},
         'status': {'display_text': 'Status', 'perms': 'HOSTVX', 'description': 'File status',
                    'select_array': {'T': 'TACC', 'N': 'Not on TACC'}, 'maxlen': 1},
         'disp_order': {'display_text': 'Display<br>Order', 'perms': 'EHOTVX',
                        'description': 'Display order index of the file', 'maxlen': 9, 'valtype': 'integer',
                        'default': 1},
         'wcount': {'display_text': 'File Count', 'perms': 'EHOTVX',
                    'description': 'Number of Web Files included in the TACC tar file', 'maxlen': 9,
                    'valtype': 'integer', 'default': 1},
         'dsids': {'display_text': 'Datasets', 'perms': 'EHOSTVX', 'description': 'Datasets included',
                   'sub_str': 16, 'textarea': self.text_area},
         'note': {'display_text': 'File List', 'perms': 'EHOSTVX', 'description': 'Detail Web File list included',
                  'sub_str': 16, 'textarea': self.text_large},
      }
      ed = self.make_editor('tfile', 'TACC File Information', 'tid', 'EHMOSUVX', columns)
      ed.set_config('tableInfo', 'cellpadding="2" width="1600" class="mateTable"')
      ed.set_config('orderByColumn', 'dsid')
      ed.set_config('editRowTitle', 'Edit A TACC File')
      ed.set_config('viewRowTitle', 'View A TACC File')
      # the PHP set 'editRowTitle' twice, so the edit form showed this multi-edit title
      ed.set_config('editMultTitle', 'Set Common Values For Multiple TACC Files')
      ed.set_config('sqlFilters', "status <> 'D'")

   def get_dataset_title(self, col, val, row):
      if not php_empty(val):
         title = self.first('SELECT title FROM dataset WHERE dsid = %s', [val])
         if title is not None:
            val += ' - ' + title
      return val

   def get_specialist(self, col, val, row):
      if not php_empty(val):
         rec = self.one('SELECT logname, lstname, fstname FROM dssdb.user WHERE uid = %s', [val])
         if rec:
            val += ' - {} ({} {})'.format(rec['logname'], rec['fstname'], rec['lstname'])
      return val
