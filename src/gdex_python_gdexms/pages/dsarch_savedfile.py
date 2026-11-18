"""Saved files (dssdb.sfile); port of dsarch_savedfile.php."""

from ..editor.page import Page, php_empty


class DsarchSavedfile(Page):
   title = 'Saved Files'

   def init_editor(self):
      dsid, grp, vrsn, back, uid = (self.get_dataset_title, self.get_group_title, self.get_version,
                                    self.get_back_file, self.get_specialist)
      columns = {
         'sid': {'display_text': 'Saved<br>ID', 'perms': 'EOSTVX', 'description': 'Saved file id',
                 'valtype': 'integer'},
         'sfile': {'display_text': 'Saved File Name', 'perms': 'EHOSTVX',
                   'description': 'Saved file name, change via dsarch', 'maxlen': 128, 'sub_str': 50,
                   'input_info': 'style="width: 400px" readonly="readonly"', 'textarea': self.text_area},
         'uid': {'display_text': 'Owner<br>ID', 'perms': 'HOSTVX', 'valtype': 'integer',
                 'description': 'Specialist internal ID who owns this file', 'view_fun': uid},
         'dsid': {'display_text': 'Dataset<br>ID', 'perms': 'HOSTVX',
                  'description': 'Dataset Identification Number', 'maxlen': 9, 'view_fun': dsid},
         'gindex': {'display_text': 'Group<br>Index', 'perms': 'HOSTVX',
                    'description': 'Group index in a dataset if > 0', 'view_fun': grp, 'valtype': 'integer'},
         'tindex': {'display_text': 'Top<br>Group', 'perms': 'EHMOQSTVX',
                    'description': 'Top group index in a dataset if > 0', 'view_fun': grp, 'valtype': 'integer'},
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
         'locflag': {'display_text': 'Location<br>Flag', 'perms': 'EHMOSTVX', 'description': 'Storage Location Flag',
                     'select_array': {'C': 'CGD Data', 'G': 'Glade Disk', 'O': 'Object Store',
                                      'B': 'Both Storage Systems'}, 'maxlen': 1},
         'type': {'display_text': 'Type', 'perms': 'HOSTVX', 'description': 'Data type',
                  'select_array': {'D': 'Data', 'O': 'Document', 'S': 'Software', 'N': 'NCAR Data',
                                   'U': 'Unknown Type'}, 'maxlen': 1},
         'status': {'display_text': 'Status', 'perms': 'HOSTVX', 'description': 'File status',
                    'select_array': {'P': 'Public', 'I': 'Internal'}, 'maxlen': 1},
         'disp_order': {'display_text': 'Display<br>Order', 'perms': 'EHOTVX',
                        'description': 'Display order index of the file', 'maxlen': 9, 'valtype': 'integer',
                        'default': 1},
         'vindex': {'display_text': 'Version', 'perms': 'HOSTVX',
                    'description': 'Version Index links to DOI if > 0', 'view_fun': vrsn, 'valtype': 'integer'},
         'bid': {'display_text': 'Backup<br>ID', 'perms': 'HOSTVX',
                 'description': 'Links to Quasar Backup file if > 0', 'view_fun': back, 'valtype': 'integer'},
         'note': {'display_text': 'Description', 'perms': 'EHOSTVX', 'description': 'File decription',
                  'sub_str': 16, 'textarea': self.text_large},
      }
      ed = self.make_editor('sfile', 'Saved Glade-Disk/Object-Store File Information', 'sid', 'EHMOSUVX', columns)
      ed.set_config('tableInfo', 'cellpadding="2" width="1600" class="mateTable"')
      ed.set_config('orderByColumn', 'dsid')
      ed.set_config('editRowTitle', 'Edit A Saved File')
      ed.set_config('viewRowTitle', 'View A Saved File')
      # the PHP set 'editRowTitle' twice, so the edit form showed this multi-edit title
      ed.set_config('editMultTitle', 'Set Common Values For Multiple Saved Files')
      ed.set_config('sqlFilters', "status <> 'D'")

   def get_dataset_title(self, col, val, row):
      if not php_empty(val):
         title = self.first('SELECT title FROM dataset WHERE dsid = %s', [val])
         if title is not None:
            val += ' - ' + title
      return val

   def get_group_title(self, col, val, row):
      if not php_empty(val) and (col == 'gindex' or val != row.get('gindex')):
         dsid = row.get('dsid')
         if dsid:
            title = self.first('SELECT title FROM dsgroup WHERE gindex = %s AND dsid = %s', [val, dsid])
            if title is not None:
               val += ' - ' + title
      return val

   def get_version(self, col, val, row):
      if not php_empty(val):
         rec = self.first("SELECT concat(status, ' - ', doi) FROM dsvrsn WHERE vindex = %s", [val])
         if rec is not None:
            val += ' - ' + rec
      return val

   def get_back_file(self, col, val, row):
      if not php_empty(val):
         rec = self.first("SELECT concat(bfile, ' - ', type) FROM bfile WHERE bid = %s", [val])
         if rec is not None:
            val += ' - ' + rec
      return val

   def get_specialist(self, col, val, row):
      if not php_empty(val):
         rec = self.one('SELECT logname, lstname, fstname FROM dssdb.user WHERE uid = %s', [val])
         if rec:
            val += ' - {} ({} {})'.format(rec['logname'], rec['fstname'], rec['lstname'])
      return val
