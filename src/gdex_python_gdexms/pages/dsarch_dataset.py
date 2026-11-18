"""Datasets (dssdb.dataset); port of dsarch_dataset.php."""

from ..editor.page import Page


class Dataset(Page):
   title = 'Dataset Information'

   def init_editor(self):
      int_cnt = {'default': 0, 'maxlen': 10, 'valtype': 'integer'}
      columns = {
         'dsid': {'display_text': 'Dataset<br>ID', 'perms': 'EOSTVX',
                  'description': 'Dataset Identification Number', 'req': True, 'maxlen': 9},
         'specialist': {'display_text': 'Specialist', 'perms': 'OSTVX',
                        'description': 'The primary specialist resposible for maintaining the dataset; change via MM',
                        'join': {'table': 'dsowner', 'column': 'dsid', 'real_column': 'dsid',
                                 'display_mask': 'specialist'}},
         'date_create': {'display_text': 'Date Created', 'perms': 'HOSTVX',
                         'description': 'Date dataset initially created', 'input_info': 'style="width: 200px"',
                         'calendar': {'format': '%Y-%m-%d'}},
         'title': {'display_text': 'Dataset Title', 'perms': 'HOSTVX',
                   'description': 'Dataset Title, defined in MM', 'maxlen': 255,
                   'sub_str': 20, 'input_info': 'style="width: 400px"', 'textarea': self.text_area},
         'webhome': {'display_text': 'Web Date<br>Home Path', 'perms': 'EHOSTVX',
                     'description': 'Path dataset data staged on disk other than the default location',
                     'maxlen': 80, 'sub_str': 20, 'input_info': 'style="width: 400px"', 'textarea': self.text_area},
         'webpath': {'display_text': 'Web<br>Path', 'perms': 'EHOSTVX',
                     'description': 'Relative path dataset data staged on disk', 'maxlen': 80, 'sub_str': 20,
                     'input_info': 'style="width: 400px"', 'textarea': self.text_area},
         'savedpath': {'display_text': 'Saved<br>Path', 'perms': 'EHOSTVX',
                       'description': 'Relative path dataset data staged at DECS data area', 'maxlen': 80,
                       'sub_str': 20, 'input_info': 'style="width: 400px"', 'textarea': self.text_area},
         'data_format': {'display_text': 'Data<br>Format', 'perms': 'EHMOSTVX',
                         'description': 'Default dataset data format', 'maxlen': 10},
         'dweb_size': {'display_text': 'Web<br>Size', 'perms': 'EHOSTVX', 'data_precision': 2,
                       'description': 'Total data size of all Web files in the dataset', 'default': 0,
                       'maxlen': 16, 'valtype': 'integer'},
         'nweb_size': {'display_text': 'NCAR<br>Size', 'perms': 'EHOSTVX', 'data_precision': 2,
                       'description': 'Total data size of all NCAR files in the dataset', 'default': 0,
                       'maxlen': 16, 'valtype': 'integer'},
         'saved_size': {'display_text': 'Saved<br>Size', 'perms': 'EHOSTVX', 'data_precision': 2,
                        'description': 'Total data size of all Saved files in the dataset', 'default': 0,
                        'maxlen': 16, 'valtype': 'integer'},
         'grouplevel': {'display_text': 'Group<br>Level', 'perms': 'EHMOSTVX',
                        'description': 'Maximum levels of groups to be displayed on one page', 'default': 2,
                        'maxlen': 2, 'valtype': 'integer'},
         'filelimit': {'display_text': 'File<br>Limit', 'perms': 'EHMOSTVX',
                       'description': 'Maximum number of files to be displayed on one page', 'default': 2000,
                       'maxlen': 5, 'valtype': 'integer'},
         'buttonlimit': {'display_text': 'Show<br>Button', 'perms': 'EHMOSTVX',
                         'description': 'Minimum number of files to show buttons on web pages', 'default': 2,
                         'maxlen': 2, 'valtype': 'integer'},
         # the PHP joined on substring(dsid, 3), left from the old dsNNN.N ids; dsids now match as is
         'dstype': {'display_text': 'Dataset<br>Type', 'perms': 'HOSTVX',
                    'description': 'Dataset control type, change via MM', 'view_fun': self.get_dataset_type,
                    'maxlen': 1,
                    'join': {'db': 'search', 'table': 'datasets', 'column': 'dsid', 'real_column': 'dsid',
                             'display_mask': 'type'}},
         'locflag': {'display_text': 'Location<br>Flag', 'perms': 'EHMOSTVX',
                     'description': 'Onine Web File Access Location Flag',
                     'select_array': {'C': 'CGD Data', 'G': 'Glade Disk', 'O': 'Object Store'}, 'maxlen': 1},
         'backflag': {'display_text': 'Backup<br>Flag', 'perms': 'EHMOSTVX', 'description': 'Dataset File Backup Flag',
                      'select_array': {'N': 'No Backup', 'B': 'Backup Only', 'D': 'Both Backup&Drdata'},
                      'maxlen': 1},
         'taccflag': {'display_text': 'TACC<br>Flag', 'perms': 'EHMOSTVX',
                      'description': 'Dataset TACC Transfer Flag',
                      'select_array': {'N': 'Not Transfer', 'T': 'Transfer to TACC', 'W': 'Wait to Transfer'},
                      'maxlen': 1},
         'accessflag': {'display_text': 'Access<br>Flag', 'perms': 'EHMOSTVX',
                        'description': 'Dataset Data File List Access Flag',
                        'select_array': {'B': 'Access Both', 'C': 'Complete File List', 'F': 'Faceted Browse',
                                         'N': 'No File List'}, 'maxlen': 1},
         'dwebcnt': dict(int_cnt, display_text='Web Data<br>Count', perms='EHMOSTVX',
                         description='Web data file count in the dataset'),
         'nwebcnt': dict(int_cnt, display_text='NCAR<br>Count', perms='EHMOSTVX',
                         description='NCAR data file count in the dataset'),
         'webcnt': dict(int_cnt, display_text='Disk File<br>Total', perms='EHMOSTVX',
                        description='Total web/disk file count, including Document and Software files in the dataset'),
         'savedcnt': dict(int_cnt, display_text='Saved File<br>Total', perms='EHMOSTVX',
                          description='Total Saved/Decsdata file count in the dataset'),
         'meta_link': {'display_text': 'Meta<br>Link', 'perms': 'EHMOSTVX', 'maxlen': 1,
                       'description': 'Flag of content metadata gathering for the dataset', 'default': 'N',
                       'select_array': {'Y': 'Metadata Gathered', 'N': 'Metadata Not Gathered'}},
         'wnote': {'display_text': 'Web File<br>Description', 'perms': 'EHOSTVX',
                   'description': 'Public dataset description for web files ', 'sub_str': 10,
                   'textarea': self.text_large},
         'dnote': {'display_text': 'Document<br>Description', 'perms': 'EHOSTVX',
                   'description': 'Description for Document files', 'sub_str': 10, 'textarea': self.text_large},
         'snote': {'display_text': 'Software<br>Description', 'perms': 'EHOSTVX',
                   'description': 'Description for Software files', 'sub_str': 10, 'textarea': self.text_large},
         'inote': {'display_text': 'Internal<br>Decription', 'perms': 'EHOSTVX',
                   'description': 'Dataset description for internal files', 'sub_str': 10,
                   'textarea': self.text_large},
      }
      ed = self.make_editor('dataset', 'Dataset Information', 'dsid', 'EHMOSUVX', columns)
      ed.set_config('tableInfo', 'cellpadding="2" width="1700" class="mateTable"')
      ed.set_config('orderByColumn', 'dsid')
      ed.set_config('addRowTitle', 'Add A Dataset')
      ed.set_config('editRowTitle', 'Edit A Dataset')
      ed.set_config('viewRowTitle', 'View A Dataset')
      ed.set_config('sqlFilters', 'priority = 1')
      ed.set_config('afterEditFun', self.update_dataset_version)

   @staticmethod
   def get_dataset_type(col, val, row):
      names = {'P': 'Public Dataset', 'H': 'Historic Dataset', 'I': 'Internal Dataset'}
      if val in names:
         val += ' - ' + names[val]
      return val
