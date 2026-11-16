"""Update remote files (dssdb.drupdt); port of dsupdt_remotefile.php."""

import re

from ..editor.page import Page, php_empty


class DsupdtRemotefile(Page):
   title = 'Remote File'

   def init_editor(self):
      dsp, chk, col_fun = self.html2text, self.check_local_index, self.select_local_index
      columns = {
         'rindex': {'display_text': 'Remote File Index', 'perms': ''},
         'remotefile': {'display_text': 'Remote File Name', 'perms': 'ACEHOQSTVX',
                        'description': 'Remote File Name to be Downloaded/Created', 'table_fun': dsp,
                        'view_fun': dsp, 'textarea': self.text_area, 'maxlen': 128, 'sub_str': 50, 'req': True},
         'dsid': {'display_text': 'Dataset<br>ID', 'perms': 'ACEMOSTVX',
                  'description': 'Dataset Identification Number', 'req': True, 'input_info': "style='width: 400px'",
                  'select_query': self.select_dsid, 'onchange': True, 'add_fun': chk, 'edit_fun': chk},
         'lindex': {'display_text': 'Local<br>Index', 'perms': 'ACEMOSTVX',
                    'description': 'Local File Index', 'req': True, 'add_fun': chk, 'edit_fun': chk,
                    'column_fun': col_fun, 'input_info': "style='width: 400px'", 'valtype': 'integer'},
         'dindex': {'display_text': 'Order', 'perms': 'ACEHOSTVX', 'default': 0,
                    'valtype': 'integer', 'maxlen': 3,
                    'description': ('Order Index if there are multiple remote files for one local file, '
                                    'or a single remote file can be retrieved from multiple servers')},
         'serverfile': {'display_text': 'Server File', 'perms': 'ACEHOSTVX',
                        'description': 'Set this if file name on remote server is different from the remote file name',
                        'textarea': self.text_area, 'maxlen': 80, 'sub_str': 50, 'table_fun': dsp, 'view_fun': dsp},
         'download': {'display_text': 'Get/Create Remote File', 'perms': 'ACEHMOSTVX',
                      'description': ('Set this only if a specify command is needed to retireve/creaete '
                                      'an individual remote file'),
                      'textarea': self.text_area, 'maxlen': 255, 'sub_str': 40, 'table_fun': dsp, 'view_fun': dsp},
         'begintime': {'display_text': 'Begin Time', 'perms': 'ACEHMOSTVX',
                       'description': 'Beginning day(s) and/or hour(s) in update periods',
                       'input_info': "style='width: 200px'", 'maxlen': 40},
         'tinterval': {'display_text': 'Time<br>Internval', 'perms': 'ACEHMOSTVX',
                       'description': 'Time Interval for remote files, i.e, 5D, 6H', 'maxlen': 4,
                       'valtype': 'interval'},
      }
      ed = self.make_editor('drupdt', 'DSUPDT Remote File Information', 'rindex', 'ACDEHMOSUVX', columns)
      ed.set_config('tableInfo', 'cellpadding="2" width="1400" class="mateTable"')
      ed.set_config('orderByColumn', 'dsid')
      ed.set_config('addRowTitle', 'Add A Remote File Record')
      ed.set_config('editRowTitle', 'Edit A Remote File Record')
      ed.set_config('viewRowTitle', 'View A Remote File Record')
      ed.set_config('editMultTitle', 'Set Common Values for Multiple Remote Files')

   def check_local_index(self, col, val, row):
      """add_fun/edit_fun: keep dsid and the local file index consistent.

      A local file index of another dataset is reset to 0; an empty dataset is
      taken from the chosen local file.
      """
      lindex = None
      if col == 'lindex':
         if not (php_empty(row.get('dsid')) or php_empty(val)):
            lindex = val
      elif col == 'dsid':
         if php_empty(val) and not php_empty(row.get('lindex')):
            lindex = row['lindex']
      if lindex is not None and re.match(r'^\d+$', str(lindex)):
         dsid = self.first('select dsid from dlupdt where lindex = %s', [lindex])
         if dsid is not None:
            if col == 'lindex':
               if dsid != row.get('dsid'):
                  val = 0
            else:
               val = dsid
      return val

   def select_local_index(self, col, val, row):
      """column_fun: local files of the row's dataset, or all local files when no dataset is chosen."""
      info = dict(self.editor.columns['lindex'])
      dsid = (row or {}).get('dsid')
      if php_empty(dsid):
         info['select_query'] = "select lindex, concat(dsid, ' - ', locfile) from dlupdt order by dsid, lindex"
         info.pop('select_vals', None)
         info['onchange'] = True
      else:
         info['select_query'] = 'select lindex, locfile from dlupdt where dsid = %s order by lindex'
         info['select_vals'] = [dsid]
         info['onchange'] = False
      return info
