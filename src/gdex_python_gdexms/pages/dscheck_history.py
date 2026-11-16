"""Closed checks (dssdb.dschkhist); port of dscheck_history.php."""

from ..editor.page import Page


class DscheckHistory(Page):
   title = 'Check History'

   def init_editor(self):
      exe = self.format_interval
      columns = {
         'cindex': {'display_text': 'Check<br>Index', 'perms': 'EOSTVX',
                    'description': 'Auto generated check index', 'valtype': 'integer'},
         'command': {'display_text': 'Command', 'perms': 'HOSTVX',
                     'description': 'Command name to be executed, i.e. dsarch', 'maxlen': 128, 'sub_str': 20},
         'specialist': {'display_text': 'Specialist', 'perms': 'HOSTVX',
                        'description': 'Specialist responsible for the command',
                        'select_query': self.select_specialist, 'query_column': 'logname',
                        'default': self.specialist},
         'dsid': {'display_text': 'Dataset<br>ID', 'perms': 'EHMOSTVX',
                  'description': 'Dataset Identification Number', 'input_info': "style='width: 400px'",
                  'select_query': self.select_dsid},
         'action': {'display_text': 'Action', 'perms': 'EHMOSTVX',
                    'description': 'Optional short action name for the command, i.e. BR for dsrqst', 'maxlen': 2},
         'status': {'display_text': 'Check<br>Status', 'perms': 'HOSTVX',
                    'description': 'Current status of the check command', 'default': 'C', 'maxlen': 1,
                    'select_array': {'C': 'Created', 'D': 'Done/Finished', 'E': 'Exit Abnormally',
                                     'I': 'Interrupted', 'R': 'Currently Running'}},
         'dcount': {'display_text': 'File<br>Count', 'perms': 'EHMOSTVX',
                    'description': 'Number of files processed', 'default': 0, 'maxlen': 9, 'valtype': 'integer'},
         'tcount': {'display_text': 'Try<br>Count', 'perms': 'HOSTVX',
                    'description': 'Number of times the command was tried', 'default': 0, 'maxlen': 2,
                    'valtype': 'integer'},
         'size': {'display_text': 'Data<br>Size', 'perms': 'EHOSTVX', 'data_precision': 1,
                  'description': 'Size of data was processed in Bytes', 'default': 0, 'maxlen': 20,
                  'valtype': 'integer'},
         'date_time': {'display_text': 'Check Time', 'display_mask': "concat(date, ' ', time)",
                       'perms': 'HOSTVX', 'description': 'Time the check was initially added'},
         'closetime': {'display_text': 'Close Time', 'perms': 'HOSTVX', 'description': 'Time the check was closed'},
         'ttltime': {'display_text': 'Total<br>Time', 'perms': 'HOSTVX',
                     'description': 'Total accumulated time the check command execution', 'default': 0,
                     'maxlen': 11, 'valtype': 'integer', 'table_fun': exe, 'view_fun': exe},
         'quetime': {'display_text': 'Queue<br>Time', 'perms': 'HOSTVX',
                     'description': 'Accumulated queueing time for the check command under LSF batch system',
                     'default': 0, 'maxlen': 11, 'valtype': 'integer', 'table_fun': exe, 'view_fun': exe},
         'hostname': {'display_text': 'Run<br>Host', 'perms': 'HOSTVX',
                      'description': 'Hostname the check command was executed on'},
         'argv': {'display_text': 'Command Argument Options', 'perms': 'HOSTVX',
                  'description': 'Command argument options', 'maxlen': 100, 'sub_str': 30},
         'errmsg': {'display_text': 'Error<br>Message', 'perms': 'HOSTVX',
                    'description': 'Accumulated error message during command execution', 'sub_str': 20,
                    'textarea': self.text_area},
      }
      ed = self.make_editor('dschkhist', 'Check History', 'cindex', 'EHMOSUVX', columns)
      ed.set_config('tableInfo', 'cellpadding="2" width="1400" class="mateTable"')
      ed.set_config('orderByColumn', 'cindex')
      ed.set_config('addRowTitle', 'Add A Check History Record')
      ed.set_config('editRowTitle', 'Edit A Check History Record')
      ed.set_config('viewRowTitle', 'View A Check History Record')
      ed.set_config('editMultTitle', 'Set Comman Values for Multiple Check History Records')
