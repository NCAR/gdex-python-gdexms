"""Quasar backup files (dssdb.bfile); port of dsarch_backupfile.php."""

from ..editor.page import Page, php_empty


class DsarchBackupfile(Page):
   title = 'Backup Files'

   def init_editor(self):
      dsid, uid = self.get_dataset_title, self.get_specialist
      columns = {
         'bid': {'display_text': 'Backup<br>ID', 'perms': 'EOSTVX', 'description': 'Quasar Backup File ID',
                 'valtype': 'integer'},
         'bfile': {'display_text': 'Backup File Name', 'perms': 'EHOSTVX',
                   'description': 'Quasar Backup/Drdata file name', 'maxlen': 128, 'sub_str': 50,
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
                         'description': 'Data content format, i.e. NetCDF', 'maxlen': 10},
         'file_format': {'display_text': 'Archive<br>Format', 'perms': 'EHMOQSTVX',
                         'description': 'File archive format, i.e. TAR.GZ', 'maxlen': 10},
         'checksum': {'display_text': 'MD5<br>Checksum', 'perms': 'HOSTVX',
                      'description': 'File md5 checksum', 'sub_str': 10},
         'type': {'display_text': 'Type', 'perms': 'HOSTVX', 'description': 'Data type',
                  'select_array': {'B': 'Quasar Backup Only', 'D': 'Quasar Backup&Drdata'}, 'maxlen': 1},
         'status': {'display_text': 'Status', 'perms': 'HOSTVX', 'description': 'File status',
                    'select_array': {'A': 'Archived to Quasar Server', 'T': 'RDA Files Tarred',
                                     'N': 'New Records with Input Files'}, 'maxlen': 1},
         'disp_order': {'display_text': 'Display<br>Order', 'perms': 'EHOTVX', 'description': 'Display order index',
                        'maxlen': 9, 'valtype': 'integer', 'default': 1},
         'scount': {'display_text': 'Savedfile<br>Count', 'perms': 'HOSTVX',
                    'description': 'Number of Saved files included', 'valtype': 'integer'},
         'wcount': {'display_text': 'Webfile<br>Count', 'perms': 'HOSTVX',
                    'description': 'Number of Web files included', 'valtype': 'integer'},
         'dsids': {'display_text': 'Datasets', 'perms': 'EHOSTVX', 'description': 'Datasets included',
                   'sub_str': 16, 'textarea': self.text_area},
         'note': {'display_text': 'Description', 'perms': 'EHOSTVX', 'description': 'File decription',
                  'sub_str': 16, 'textarea': self.text_large},
      }
      ed = self.make_editor('bfile', 'Quasar Backup/Drdata File Information', 'bid', 'EHMOSUVX', columns)
      ed.set_config('tableInfo', 'cellpadding="2" width="1600" class="mateTable"')
      ed.set_config('orderByColumn', 'dsid')
      ed.set_config('editRowTitle', 'Edit A Backup File')
      ed.set_config('viewRowTitle', 'View A Backup File')
      # the PHP set 'editRowTitle' twice, so the edit form showed this multi-edit title
      ed.set_config('editMultTitle', 'Set Common Values For Multiple Backup Files')
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
