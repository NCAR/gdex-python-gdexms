"""Help files (dssdb.hfile); port of dsarch_helpfile.php."""

from ..editor.page import Page, php_empty


class DsarchHelpfile(Page):
   title = 'Help Files'

   def init_editor(self):
      dsid, uid = self.get_dataset_title, self.get_specialist
      columns = {
         'hid': {'display_text': 'Help<br>ID', 'perms': 'EOSTVX', 'description': 'Help File ID',
                 'valtype': 'integer'},
         'hfile': {'display_text': 'Help File Name', 'perms': 'EHOSTVX',
                   'description': 'Help file name, change via dsarch', 'maxlen': 128, 'sub_str': 50,
                   'input_info': 'style="width: 400px" readonly="readonly"', 'textarea': self.text_area},
         'uid': {'display_text': 'Owner<br>ID', 'perms': 'HOSTVX', 'valtype': 'integer',
                 'description': 'Specialist internal ID who owns this file', 'view_fun': uid},
         'dsid': {'display_text': 'Dataset<br>ID', 'perms': 'HOSTVX',
                  'description': 'Dataset Identification Number', 'maxlen': 9, 'view_fun': dsid},
         'data_size': {'display_text': 'Size', 'perms': 'HOSTVX', 'description': 'File size', 'data_precision': 2},
         'source': {'display_text': 'Source', 'perms': 'EHMOQSTVX', 'description': 'Help File Contribution Source',
                    'maxlen': 80, 'sub_str': 10, 'input_info': 'style="width: 400px"', 'textarea': self.text_area},
         'init_date': {'display_text': 'Initial Date', 'perms': 'HOSTVX',
                       'description': 'Document/Software initially Published/Released',
                       'input_info': 'style="width: 200px"', 'calendar': {'format': '%Y-%m-%d'}},
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
         'type': {'display_text': 'Type', 'perms': 'HOSTVX', 'description': 'Data type',
                  'select_array': {'D': 'Document', 'S': 'Software', 'N': 'NCAR Data', 'U': 'Unknown Type'},
                  'maxlen': 1},
         'status': {'display_text': 'Status', 'perms': 'HOSTVX', 'description': 'File status',
                    'select_array': {'P': 'Public', 'I': 'Internal'}, 'maxlen': 1},
         'url': {'display_text': 'Web URL', 'perms': 'HOSTVX',
                 'description': 'Web URL with full paths for a remote Help file', 'sub_str': 10},
         'disp_order': {'display_text': 'Display<br>Order', 'perms': 'EHOTVX',
                        'description': 'Display order index of the file', 'maxlen': 9, 'valtype': 'integer',
                        'default': 1},
         'note': {'display_text': 'Description', 'perms': 'EHOSTVX', 'description': 'File decription',
                  'sub_str': 16, 'textarea': self.text_large},
      }
      ed = self.make_editor('hfile', 'Help File Information', 'hid', 'EHMOSUVX', columns)
      ed.set_config('tableInfo', 'cellpadding="2" width="1600" class="mateTable"')
      ed.set_config('orderByColumn', 'dsid')
      ed.set_config('editRowTitle', 'Edit A Help File')
      ed.set_config('viewRowTitle', 'View A Help File')
      # the PHP set 'editRowTitle' twice, so the edit form showed this multi-edit title
      ed.set_config('editMultTitle', 'Set Common Values For Multiple Help Files')
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
