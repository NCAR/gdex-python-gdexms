"""Update controls (dssdb.dcupdt); port of dsupdt_control.php."""

from ..editor.page import Page, php_empty


class DsupdtControl(Page):
   title = 'Update Control'

   def init_editor(self):
      dsp, col_fun, run = self.html2text, self.select_parent_index, self.display_running_status
      columns = {
         'cindex': {'display_text': 'Control<br>Index', 'perms': 'EOSTVX',
                    'description': 'Update Control Index', 'valtype': 'integer'},
         'cntlid': {'display_text': 'Control ID', 'perms': 'ACEHOTVX', 'description': 'Update Control ID',
                    'input_info': 'style="width: 240px"', 'maxlen': 40, 'sub_str': 20},
         'dsid': {'display_text': 'Dataset<br>ID', 'perms': 'ACEMOSTVX',
                  'description': 'Dataset Identification Number', 'req': True, 'input_info': "style='width: 400px'",
                  'select_query': self.select_dsid},
         'specialist': {'display_text': 'Specialist', 'perms': 'ACEHMOSTVX',
                        'description': 'Specialist responsible for the updates', 'req': True,
                        'select_query': self.select_specialist, 'query_column': 'logname',
                        'default': self.specialist},
         'pindex': {'display_text': 'Parent<br>Index', 'perms': 'ACEHMOSTVX',
                    'description': 'Parent Control Index to wait on', 'default': 0,
                    'column_fun': col_fun, 'valtype': 'integer'},
         'action': {'display_text': 'Update<br>Action', 'perms': 'ACEHMOSTVX',
                    'description': 'Update Action to control', 'req': True,
                    'select_array': {'UF': 'Complete Update Cycle', 'DR': 'Download Remote File',
                                     'BL': 'Build Local File', 'PB': 'Process Both (Remote and Local files)',
                                     'AF': 'Archive File'}, 'default': 'UF'},
         'frequency': {'display_text': 'Update<br>Frequency', 'perms': 'ACEHMOSTVX',
                       'description': 'Frequency to do update, i.e, 1Y, 3D or 6H', 'req': True,
                       'maxlen': 4, 'valtype': 'frequency'},
         'cntloffset': {'display_text': 'Time<br>Offset', 'perms': 'ACEHMOTVX',
                        'description': 'Time Offset to start for update frequency, i.e. 2D10H',
                        'maxlen': 20, 'valtype': 'interval'},
         'cntltime': {'display_text': 'Time of Next Update', 'perms': 'ACEHMOSTVX',
                      'description': 'Time to start next update', 'input_info': 'style="width: 200px"',
                      'calendar': {'format': '%Y-%m-%d %H:%M:00', 'reset': True}},
         'datatime': {'display_text': 'Time Data Updated to', 'perms': 'ACEHMOTVX',
                      'description': 'Time the most recent data updated to', 'input_info': "style='width: 200px'",
                      'calendar': {'format': '%Y-%m-%d %H:59:59', 'reset': True}},
         'retryint': {'display_text': 'Retry<br>Interval', 'perms': 'ACEHMOTVX',
                      'description': 'Retry interval for failed updates', 'maxlen': 20, 'valtype': 'interval'},
         'validint': {'display_text': 'Valid<br>Interval', 'perms': 'ACEHMOTVX',
                      'description': 'Time interval data staged for access, i.e. 10D; 0 to use system default',
                      'maxlen': 20, 'valtype': 'interval'},
         'updtcntl': {'display_text': 'Update<br>Options', 'perms': 'ACEHMOTVX',
                      'description': 'Update Control Options; allow uultiple selections',
                      'select_array': {'B': 'Begin Time for temporal pattern',
                                       'C': 'Force Update for Current Period',
                                       'F': 'Force Update for Future Period', 'G': 'Use GMT Time For Time Control',
                                       'M': 'Multiple Update Periods', 'N': 'Update New/Changed Data Files Only',
                                       'O': 'Update Mised Data Files Only', 'Y': 'Skip February 29 in Leap Years',
                                       'Z': 'Consider Empty File as Valid'},
                      'input_info': 'multiple="true"'},
         'emailcntl': {'display_text': 'Email<br>Option', 'perms': 'ACEHMOTVX',
                       'description': 'Email Control Option', 'default': 'A', 'req': True, 'maxlen': 1,
                       'select_array': {'A': 'All Detail Emails', 'E': 'Error Emails Only', 'N': 'No Emails Sent',
                                        'S': 'Email Summary Only', 'B': 'Summary&Error Email When Error Happens'}},
         'errorcntl': {'display_text': 'Error<br>Option', 'perms': 'ACEHMOTVX',
                       'description': 'Error Control Option', 'default': 'N', 'req': True, 'maxlen': 1,
                       'select_array': {'I': 'Ignore Errors and Continue', 'Q': 'Quit on Error',
                                        'N': 'Handle Error Normally'}},
         'keepfile': {'display_text': 'Keep<br>Option', 'perms': 'ACEHMOTVX',
                      'description': 'Keep File Option', 'default': 'N', 'req': True, 'maxlen': 1,
                      'select_array': {'N': 'Donot Keep Any File', 'R': 'Keep Remote File',
                                       'S': 'Keep Server File', 'B': 'Keep both Remote&Server Files'}},
         'houroffset': {'display_text': 'Time Zone<br>Offset', 'perms': 'ACEHMOTVX',
                        'description': 'Time Zone Offset In hours for remote server comparing to local time',
                        'maxlen': 2, 'valtype': 'integer'},
         'dsupdt': {'display_text': 'Execution Status', 'perms': 'HOSTVX', 'maxlen': 40,
                    'description': 'Display process id and host name if the update control is under processing',
                    'display_mask': "concat(pid, ' ', lockhost)", 'table_fun': run, 'view_fun': run},
         'hostname': {'display_text': 'Hostname', 'perms': 'ACEHMOSTVX',
                      'description': 'Hostname(s), separated by :, to do update on; leading by ! for not on',
                      'select_query': "select hostname, note from hostname where service in ('A', 'W')",
                      'exclusive': True, 'input_info': 'multiple="true" separator=":"', 'maxlen': 80, 'su_str': 20},
         'modules': {'display_text': 'Modules', 'perms': 'ACEHMOQSTVX',
                     'description': 'Additional modules passing to Batch command',
                     'textarea': self.text_area, 'sub_str': 25, 'maxlen': 128},
         'environments': {'display_text': 'Environment<br>Variables', 'perms': 'ACEHMOQSTVX',
                          'description': 'Additional environment variables passing to batch command',
                          'textarea': self.text_area, 'sub_str': 25, 'maxlen': 128},
         'qoptions': {'display_text': 'QSUB Options', 'perms': 'ACEHMOQSTVX',
                      'description': "Additional options passing to PBS command 'qsub'",
                      'textarea': self.text_area, 'sub_str': 25, 'maxlen': 128},
         'execcmd': {'display_text': 'Update Command', 'perms': 'ACEHMOSTVX',
                     'description': 'Specify a command to run after each successful update',
                     'textarea': self.text_area, 'input_info': 'maxlength="128"', 'sub_str': 16,
                     'table_fun': dsp, 'view_fun': dsp},
         'emails': {'display_text': 'Carbon<br>Copy', 'perms': 'ACEHMOTVX',
                    'description': 'Carbon copy email addresses',
                    'textarea': self.text_area, 'maxlen': 250, 'sub_str': 20},
      }
      ed = self.make_editor('dcupdt', 'Update Control Information', 'cindex', 'ACDEHMOSUVX', columns)
      ed.set_config('tableInfo', 'cellpadding="2" width="1700" class="mateTable"')
      ed.set_config('orderByColumn', 'dsid')
      ed.set_config('addRowTitle', 'Add An Update Control')
      ed.set_config('editRowTitle', 'Edit An Update Control')
      ed.set_config('editMultTitle', 'Set Common Values for Multiple Update Controls')
      ed.set_config('viewRowTitle', 'View An Update Control')
      ed.set_config('refreshInterval', 60)     # refresh table/view every 60 seconds
      ed.set_lock_info('lockhost', 'chktime')

   def select_parent_index(self, col, val, row):
      """column_fun: parent controls to choose from, excluding the row's own control."""
      info = dict(self.editor.columns['pindex'])
      cindex = (row or {}).get('cindex')
      if php_empty(cindex):
         info['select_query'] = "select cindex, concat(dsid, ' - ', cntlid) from dcupdt order by dsid, cindex"
         info.pop('select_vals', None)
      else:
         info['select_query'] = ("select cindex, concat(dsid, ' - ', cntlid) from dcupdt where cindex <> %s "
                                 "order by dsid, cindex")
         info['select_vals'] = [cindex]
      return info
