"""Update local files (dssdb.dlupdt); port of dsupdt_localfile.php."""

import re

from ..editor.page import Page, php_empty


class DsupdtLocalfile(Page):
   title = 'Local File'

   def init_editor(self):
      dsp, chk, col_fun = self.html2text, self.check_control_index, self.select_control_index
      run = self.display_running_status
      columns = {
         'lindex': {'display_text': 'Local<br>Index', 'perms': 'EOSTVX',
                    'description': 'Local File Index', 'valtype': 'integer'},
         'locfile': {'display_text': 'Local File Name', 'perms': 'ACEOQSTVX',
                     'description': 'Local file name ready to be archived, may include temporal pattern',
                     'textarea': self.text_area, 'maxlen': 128, 'sub_str': 20, 'req': True,
                     'table_fun': dsp, 'view_fun': dsp},
         'dsid': {'display_text': 'Dataset<br>ID', 'perms': 'ACEMOSTVX',
                  'description': 'Dataset Identification Number', 'req': True, 'input_info': "style='width: 400px'",
                  'select_query': self.select_dsid, 'onchange': True, 'add_fun': chk, 'edit_fun': chk},
         'cindex': {'display_text': 'Control<br>Index', 'perms': 'ACEHMOSTVX',
                    'description': 'Update Control Index', 'default': 0, 'valtype': 'integer',
                    'add_fun': chk, 'edit_fun': chk, 'column_fun': col_fun},
         'archfile': {'display_text': 'Archive<br>File', 'perms': 'ACEHOQSTVX',
                      'description': 'File Name to be archived as',
                      'textarea': self.text_area, 'maxlen': 128, 'sub_str': 15,
                      'table_fun': dsp, 'view_fun': dsp},
         'download': {'display_text': 'Get/Create<br>Remote File', 'perms': 'ACEHOQSTVX',
                      'description': 'Command to download/retrieve files from remote servers or create ones locally',
                      'textarea': self.text_area, 'maxlen': 255, 'sub_str': 20,
                      'table_fun': dsp, 'view_fun': dsp},
         'execorder': {'display_text': 'Execute<br>Order', 'perms': 'ACEHOSTVX', 'valtype': 'integer',
                       'description': 'Execution Order Index for multiple records in same dataset', 'default': 0},
         'specialist': {'display_text': 'Specialist', 'perms': 'ACEHMOSTVX',
                        'description': 'Specialist resposible for the update', 'req': True,
                        'select_query': self.select_specialist, 'query_column': 'logname',
                        'default': self.specialist},
         'missremote': {'display_text': 'Miss<br>Remote', 'perms': 'ACEHMOSTVX',
                        'description': 'Allow missing remote file to build a local File partially', 'maxlen': 1,
                        'select_array': {'Y': 'Allow Missing Remote File', 'N': 'No Missing Remote File'},
                        'default': 'N'},
         'processremote': {'display_text': 'Process<br>Remote', 'perms': 'ACEHMOSTVX',
                           'description': 'Commmand to process remote files after Downloaded/created',
                           'textarea': self.text_area, 'maxlen': 128, 'sub_str': 15,
                           'table_fun': dsp, 'view_fun': dsp},
         'workdir': {'display_text': 'Working<br>Directory', 'perms': 'ACEHMOSTVX',
                     'description': 'Working directory to prepare files for archive',
                     'textarea': self.text_area, 'maxlen': 128, 'sub_str': 15,
                     'table_fun': dsp, 'view_fun': dsp},
         'action': {'display_text': 'DSARCH<br>Action', 'perms': 'ACEHMOSTVX',
                    'description': 'Data archiving action passing to DSARCH', 'req': True,
                    'select_array': {'AM': 'Archive Files to MSS/HPSS', 'AW': 'Archive File for Online Access',
                                     'AB': 'Archive Files to Both HPSS and Online'}},
         'options': {'display_text': 'DSARCH Option', 'perms': 'ACEHMOSTVX',
                     'description': 'Data archive options passing to DSARCH',
                     'textarea': self.text_area, 'maxlen': 255, 'sub_str': 15,
                     'table_fun': dsp, 'view_fun': dsp},
         'frequency': {'display_text': 'Data<br>Frequency', 'perms': 'ACEHMOSTVX',
                       'description': 'Local file frequency, i.e, 1Y, 3D or 6H', 'req': True,
                       'maxlen': 4, 'valtype': 'frequency'},
         'endperiod': {'display_text': 'End<br>Period', 'perms': 'ACEHMOSTVX',
                       'description': 'Offsest for data time Of frequency period if provided',
                       'default': 0, 'valtype': 'integer', 'maxlen': 3},
         'enddate': {'display_text': 'End Data<br>Date', 'perms': 'ACEHMOSTVX',
                     'description': 'Next end data date for update',
                     'calendar': {'format': '%Y-%m-%d', 'reset': True}},
         'endhour': {'display_text': 'End Data<br>Hour', 'perms': 'ACEHMOSTVX',
                     'description': 'Next end data hour for update if hourly local/remote data',
                     'valtype': 'integer', 'maxlen': 2},
         'nextdue': {'display_text': 'Due<br>Interval', 'perms': 'ACEHMOSTVX',
                     'description': 'Time interval for data is due after end data time, i.e. 3D4H', 'maxlen': 20,
                     'valtype': 'interval'},
         'validint': {'display_text': 'Valid<br>Interval', 'perms': 'ACEHMOTVX',
                      'description': 'Time interval data staged for access, i.e. 10D; 0 to use system default',
                      'maxlen': 20, 'valtype': 'interval'},
         'dsupdt': {'display_text': 'Execution<br>Status', 'perms': 'HOSTVX', 'maxlen': 40,
                    'description': 'Display process id and host name if the local file is under processing',
                    'display_mask': "concat(pid, ' ', hostname)", 'table_fun': run, 'view_fun': run},
         'agetime': {'display_text': 'Age', 'perms': 'ACEHMOSTVX', 'maxlen': 20,
                     'description': 'Minimal time for remote file to be ready for download', 'valtype': 'interval'},
         'buildcmd': {'display_text': 'Build<br>Local', 'perms': 'ACEHMOSTVX',
                      'description': 'Command to build local Files if needed', 'textarea': self.text_area,
                      'maxlen': 128, 'sub_str': 10, 'table_fun': dsp, 'view_fun': dsp},
         'cleancmd': {'display_text': 'Clean<br>File', 'perms': 'ACEHMOSTVX',
                      'description': 'Command to clean temporal files after successful update',
                      'textarea': self.text_area, 'maxlen': 128, 'sub_str': 10,
                      'table_fun': dsp, 'view_fun': dsp},
         'note': {'display_text': 'Archive<br>Note', 'perms': 'ACEHOSTVX',
                  'description': 'Note can be passed to archived file records, may include temporal Patterns',
                  'textarea': self.text_area, 'maxlen': 255, 'sub_str': 10,
                  'table_fun': dsp, 'view_fun': dsp},
      }
      ed = self.make_editor('dlupdt', 'DSUPDT Local File Information', 'lindex', 'ACDEHMOSUVX', columns)
      ed.set_config('tableInfo', 'cellpadding="2" width="1900" class="mateTable"')
      ed.set_config('orderByColumn', 'dsid')
      ed.set_config('addRowTitle', 'Add A Local File Record')
      ed.set_config('editRowTitle', 'Edit A Local File Record')
      ed.set_config('editMultTitle', 'Set Common Values for Multiple Local Files')
      ed.set_config('viewRowTitle', 'View A Local File Record')
      ed.set_config('refreshInterval', 60)     # refresh table/view every 60 seconds
      ed.set_lock_info('hostname', 'locktime')

   def check_control_index(self, col, val, row):
      """add_fun/edit_fun: keep dsid and the control index consistent.

      A control index of another dataset is reset to 0; an empty dataset is
      taken from the chosen control.
      """
      cindex = None
      if col == 'cindex':
         if not (php_empty(row.get('dsid')) or php_empty(val)):
            cindex = val
      elif col == 'dsid':
         if php_empty(val) and not php_empty(row.get('cindex')):
            cindex = row['cindex']
      if cindex is not None and re.match(r'^\d+$', str(cindex)):
         dsid = self.first('select dsid from dcupdt where cindex = %s', [cindex])
         if dsid is not None:
            if col == 'cindex':
               if dsid != row.get('dsid'):
                  val = 0
            else:
               val = dsid
      return val

   def select_control_index(self, col, val, row):
      """column_fun: controls of the row's dataset, or all controls when no dataset is chosen."""
      info = dict(self.editor.columns['cindex'])
      dsid = (row or {}).get('dsid')
      if php_empty(dsid):
         info['select_query'] = "select cindex, concat(dsid, ' - ', cntlid) from dcupdt order by dsid, cindex"
         info.pop('select_vals', None)
         info['onchange'] = True
      else:
         info['select_query'] = 'select cindex, cntlid from dcupdt where dsid = %s order by cindex'
         info['select_vals'] = [dsid]
         info['onchange'] = False
      return info
