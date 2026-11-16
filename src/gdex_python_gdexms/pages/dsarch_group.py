"""Dataset groups (dssdb.dsgroup); port of dsarch_group.php."""

from ..editor.page import Page


class DsarchGroup(Page):
   title = 'Group Information'

   def init_editor(self):
      columns = {
         'gidx': {'display_text': 'gidx', 'perms': '', 'description': 'hidden unique group index'},
         'gindex': {'display_text': 'Group<br>Index', 'perms': 'ACEHOSTVX',
                    'description': 'Group index, unique inside a dataset', 'req': True, 'maxlen': 10,
                    'valtype': 'integer'},
         'grpid': {'display_text': 'Group Id', 'perms': 'ACEHOSTVX', 'req': True,
                   'description': 'Group decriptive Identification', 'maxlen': 40, 'sub_str': 20,
                   'input_info': 'style="width: 200px"'},
         'dsid': {'display_text': 'Dataset<br>ID', 'perms': 'ACOSTVX',
                  'description': 'Dataset Identification Number', 'req': True, 'input_info': "style='width: 400px'",
                  'select_query': self.select_dsid},
         'title': {'display_text': 'Group Title', 'perms': 'ACEHOSTVX',
                   'description': 'Group title for a brief group description', 'maxlen': 255, 'sub_str': 20,
                   'input_info': 'style="width: 400px"', 'textarea': self.text_area, 'req': True},
         'pindex': {'display_text': 'Parent<br>Iindex', 'perms': 'ACEHMOSTVX',
                    'description': 'Parent group index, for subgroup if not 0', 'default': 0, 'maxlen': 10,
                    'valtype': 'integer'},
         'grptype': {'display_text': 'Type', 'perms': 'ACEHMOSTVX',
                     'description': 'Type of group data', 'default': 'P', 'maxlen': 1,
                     'select_array': {'P': 'Public Group', 'I': 'Internal Group'}},
         'level': {'display_text': 'Subgroup<br>Level', 'perms': 'ACEHMOSTVX', 'req': True,
                   'description': 'How many level down for a subgroup', 'default': 1, 'maxlen': 34,
                   'valtype': 'integer'},
         'pattern': {'display_text': 'Match<br>Pattern', 'perms': 'ACEHOSTVX',
                     'description': 'Filename matching pattern ti identify a group for a give file', 'maxlen': 80,
                     'sub_str': 10, 'input_info': 'style="width: 400px"', 'textarea': self.text_area},
         'webpath': {'display_text': 'Disk Path', 'perms': 'ACEHOSTVX',
                     'description': 'Path group data staged on disk', 'maxlen': 80, 'sub_str': 10,
                     'input_info': 'style="width: 400px"', 'textarea': self.text_area},
         'savedpath': {'display_text': 'Saved Path', 'perms': 'ACEHOSTVX',
                       'description': 'Path group data staged at DECS Data Area', 'maxlen': 80, 'sub_str': 10,
                       'input_info': 'style="width: 400px"', 'textarea': self.text_area},
         'dweb_size': {'display_text': 'Web<br>Size', 'perms': 'ACEHMOSTVX', 'data_precision': 2,
                       'description': 'Total data size of all Web files in the group', 'default': 0,
                       'maxlen': 16, 'valtype': 'integer'},
         'nweb_size': {'display_text': 'NCAR<br>Size', 'perms': 'ACEHMOSTVX', 'data_precision': 2,
                       'description': 'Total data size of all NCAR files in the group', 'default': 0,
                       'maxlen': 16, 'valtype': 'integer'},
         'saved_size': {'display_text': 'Saved<br>Size', 'perms': 'ACEHMOSTVX', 'data_precision': 2,
                        'description': 'Total data size of all Saved files in the group', 'default': 0,
                        'maxlen': 16, 'valtype': 'integer'},
         'backflag': {'display_text': 'Backup<br>Flag', 'perms': 'EHMOSTVX', 'description': 'Group File Backup Flag',
                      'select_array': {'P': 'Follow Parent Flag', 'N': 'No Backup', 'B': 'Backup Only',
                                       'D': 'Both Backup&Drdata'}, 'maxlen': 1},
         'accessflag': {'display_text': 'Access<br>Flag', 'perms': 'EHMOSTVX',
                        'description': 'Top Group Data File List Access Flag',
                        'select_array': {'B': 'Access Both', 'C': 'Complete File List', 'F': 'Faceted Browse',
                                         'N': 'No File List'}, 'maxlen': 1},
         'dwebcnt': {'display_text': 'Web Data<br>Count', 'perms': 'ACEHMOSTVX',
                     'description': 'Web data file count in the group', 'default': 0, 'maxlen': 10,
                     'valtype': 'integer'},
         'nwebcnt': {'display_text': 'NCAR<br>Count', 'perms': 'ACEHMOSTVX',
                     'description': 'NCAR data file count in the group', 'default': 0, 'maxlen': 10,
                     'valtype': 'integer'},
         'webcnt': {'display_text': 'Disk File<br>Total', 'perms': 'ACEHMOSTVX',
                    'description': 'Total web/disk file count, including Document and Software files in the group',
                    'default': 0, 'maxlen': 10, 'valtype': 'integer'},
         'savedcnt': {'display_text': 'Saved File<br>Count', 'perms': 'ACEHMOSTVX',
                      'description': 'Saved data file count in the group', 'default': 0, 'maxlen': 10,
                      'valtype': 'integer'},
         'meta_link': {'display_text': 'Meta<br>Link', 'perms': 'ACEHMOSTVX', 'maxlen': 1,
                       'description': 'Flag of content metadata gathering for the group', 'default': 'N',
                       'select_array': {'W': 'Metadata Gathered for Web/Disk data', 'N': 'Metadata Not Gathered'}},
         'wnote': {'display_text': 'Web File<br>Description', 'perms': 'ACEHOSTVX',
                   'description': 'Public group description for web files ', 'sub_str': 10,
                   'textarea': self.text_large},
         'inote': {'display_text': 'Internal<br>Decription', 'perms': 'ACEHOSTVX',
                   'description': 'Group description for internal data files', 'sub_str': 10,
                   'textarea': self.text_large},
      }
      ed = self.make_editor('dsgroup', 'Dataset Group Information', 'gidx', 'ACEHMOSUVX', columns)
      ed.set_config('tableInfo', 'cellpadding="2" width="1600" class="mateTable"')
      ed.set_config('orderByColumn', 'dsid')
      ed.set_config('addRowTitle', 'Add A Group')
      ed.set_config('editRowTitle', 'Edit A Group')
      ed.set_config('viewRowTitle', 'View A Group')
      # the PHP set editRowTitle a second time here, overwriting 'Edit A Group'
      ed.set_config('editMultTitle', 'Set Common Values for Multiple Groups')
