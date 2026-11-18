"""DOI version controls (dssdb.dsvrsn); port of dsarch_version.php."""

from ..editor.page import Page


class DsarchVersion(Page):
   title = 'DOI Version Control'

   def init_editor(self):
      columns = {
         'vindex': {'display_text': 'Version<br>Index', 'perms': 'EOSTVX',
                    'description': 'Version control index, add via MM', 'valtype': 'integer'},
         'dsid': {'display_text': 'Dataset<br>ID', 'perms': 'EOSTVX',
                  'description': 'Dataset Identification Number',
                  'input_info': "style='width: 400px' disabled='disabled'", 'select_query': self.select_dsid},
         'status': {'display_text': 'Status', 'perms': 'HOSTVX', 'maxlen': 1,
                    'description': 'Current version control status',
                    'select_array': {'A': 'Active', 'H': 'Historic', 'P': 'Pending'}},
         'iversion': {'display_text': 'Internal<br>Version', 'perms': 'HOSTVX',
                      'description': 'internal version number, auto generated', 'valtype': 'integer'},
         'eversion': {'display_text': 'Public<br>Version', 'perms': 'EHMOSTVX',
                      'description': 'Public version/release number, i.e. 2.5.1', 'maxlen': 40, 'sub_str': 20,
                      'input_info': 'style="width: 200px"'},
         'doi': {'display_text': 'DOI Number', 'perms': 'HOSTVX',
                 'description': 'DOI number, generated via MM', 'input_info': 'style="width: 200px"'},
         'start_date': {'display_text': 'Start Date', 'perms': 'EHMOSX',
                        'description': 'Date version control starts', 'input_info': 'style="width: 200px"',
                        'calendar': {'format': '%Y-%m-%d'}, 'req': True},
         'start_time': {'display_text': 'Start Time', 'perms': 'EHMOSTVX',
                        'description': 'Time version control starts', 'req': True,
                        'display_mask': "concat(start_date, ' ', start_time)"},
         'end_date': {'display_text': 'End Date', 'perms': 'EHMOSX',
                      'description': 'Date version control ends', 'input_info': 'style="width: 200px"',
                      'calendar': {'format': '%Y-%m-%d', 'reset': True}},
         'end_time': {'display_text': 'End Time', 'perms': 'EHMOSTVX',
                      'description': 'Time version control ends',
                      'display_mask': "concat(end_date, ' ', end_time)"},
         'note': {'display_text': 'Description', 'perms': 'EHMOSTVX',
                  'description': 'Description of version control', 'sub_str': 20, 'textarea': self.text_area},
      }
      ed = self.make_editor('dsvrsn', 'DOI Version Control Information', 'vindex', 'EHMOSUVX', columns)
      ed.set_config('tableInfo', 'cellpadding="2" width="900" class="mateTable"')
      ed.set_config('orderByColumn', 'dsid')
      ed.set_config('addRowTitle', 'Add A DOI Version Control')
      ed.set_config('editRowTitle', 'Edit A DOI Version Control')
      ed.set_config('viewRowTitle', 'View A DOI Version Control')
      ed.set_config('editMultTitle', 'Set Common Values for Multiple DOI Version Controls')
