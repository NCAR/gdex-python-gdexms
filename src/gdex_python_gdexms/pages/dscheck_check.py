"""Current checks (dssdb.dscheck); port of dscheck_check.php."""

from ..editor.page import Page


class DscheckCheck(Page):
   title = 'Check Information'

   def init_editor(self):
      run = self.display_running_status
      columns = {
         'cindex': {'display_text': 'Check<br>Index', 'perms': 'EOSTVX',
                    'description': 'Auto generated check index', 'valtype': 'integer'},
         'command': {'display_text': 'Command', 'perms': 'ACHOSTVX',
                     'description': 'Command name to be controlled, i.e. dsarch', 'maxlen': 128, 'sub_str': 20,
                     'input_info': 'style="width: 400px"', 'req': True},
         'argv': {'display_text': 'Command Argument Options', 'perms': 'ACHOSTVX',
                  'description': 'Command argument options up to 100 characters', 'maxlen': 100, 'sub_str': 30,
                  'input_info': 'style="width: 400px"', 'textarea': self.text_area},
         'specialist': {'display_text': 'Specialist', 'perms': 'ACHOSTVX',
                        'description': 'Specialist responsible for the command', 'req': True,
                        'select_query': self.select_specialist, 'query_column': 'logname',
                        'default': self.specialist},
         'dsid': {'display_text': 'Dataset<br>ID', 'perms': 'ACEHMOSTVX',
                  'description': 'Dataset Identification Number', 'input_info': "style='width: 400px'",
                  'select_query': self.select_dsid},
         'action': {'display_text': 'Action', 'perms': 'ACEHMOSTVX',
                    'description': 'Optional short action name for the command, i.e. BR for dsrqst', 'maxlen': 2},
         'oindex': {'display_text': 'Original<br>Index', 'perms': 'ACMHMOSTVX',
                    'description': 'Original command index if set', 'maxlen': 9, 'valtype': 'integer', 'default': 0},
         'otype': {'display_text': 'Original<br>Type', 'perms': 'ACMHMOSTVX',
                   'description': 'Original command index type', 'default': '', 'maxlen': 1,
                   'select_array': {'R': 'Request Index', 'P': 'Request Partition Index',
                                    'C': 'Update Control Index', 'L': 'Update Local File Index'}},
         'date_time': {'display_text': 'Check Time', 'display_mask': "concat(date, ' ', time)",
                       'perms': 'HOSTVX', 'description': 'Time the check is initially added',
                       'input_info': 'style="width: 200px"'},
         'status': {'display_text': 'Check<br>Status', 'perms': 'HOSTVX',
                    'description': 'Current status of the check command', 'default': 'C', 'maxlen': 1,
                    'select_array': {'C': 'Created', 'D': 'Done', 'E': 'Exit Abnormally',
                                     'F': 'Finished but Unsuccessful', 'I': 'Interrupted', 'P': 'Pending',
                                     'R': 'Running', 'S': 'Suspended', 'U': 'Unkown'}},
         'dflags': {'display_text': 'Storage<br>Down Status', 'perms': 'ACEHMOTVX',
                    'description': 'Current status of storage system down', 'default': '', 'maxlen': 5,
                    'select_array': {'G': 'GLADE Storage System', 'H': 'HPSS Tape System',
                                     'D': 'Disaster Recoverage Tape System'}, 'input_info': 'multiple="true"'},
         'dscheck': {'display_text': 'Execution Status', 'perms': 'HOSTVX',
                     'description': 'Display process id and host name if the check is under processing',
                     'sub_str': 40, 'display_mask': "concat(pid, ' ', lockhost)", 'table_fun': run, 'view_fun': run},
         'fcount': {'display_text': 'File<br>Count', 'perms': 'ACEHMOSTVX',
                    'description': 'Number of files to be processed', 'default': 0, 'maxlen': 9, 'valtype': 'integer'},
         'dcount': {'display_text': 'Done<br>Count', 'perms': 'HOSTVX',
                    'description': 'Number of files processed already', 'default': 0, 'maxlen': 9,
                    'valtype': 'integer'},
         'mcount': {'display_text': 'Max<br>Count', 'perms': 'ACEHMOSTVX',
                    'description': 'Maximum number of times the command can be tried', 'default': 1, 'maxlen': 2,
                    'valtype': 'integer'},
         'tcount': {'display_text': 'Try<br>Count', 'perms': 'HOSTVX',
                    'description': 'Number of times the command has been tried', 'default': 0, 'maxlen': 2,
                    'valtype': 'integer'},
         'size': {'display_text': 'Data<br>Size', 'perms': 'AEHOSTVX', 'data_precision': 1,
                  'description': 'Size of data being processed in Bytes', 'default': 0, 'maxlen': 20,
                  'valtype': 'integer'},
         'hostname': {'display_text': 'Hostname', 'perms': 'ACEHMOSTVX',
                      'description': 'Hostname(s), separated by :, to run the check command on; leading by ! for not on',
                      'select_query': "select hostname, note from hostname where service in ('A', 'W')",
                      'exclusive': True, 'input_info': 'multiple="true" separator=":"', 'maxlen': 80, 'su_str': 20},
         'workdir': {'display_text': 'Working Directory', 'perms': 'ACEHMOSTVX',
                     'description': 'Working directory to start the check command',
                     'textarea': self.text_area, 'maxlen': 128, 'sub_str': 20},
         'pindex': {'display_text': 'Parent<br>Index', 'perms': 'ACMHMOSTVX',
                    'description': 'Parent check index for this check to wait on', 'maxlen': 9, 'valtype': 'integer'},
         'modules': {'display_text': 'Modules', 'perms': 'ACEHMOQSTVX',
                     'description': 'Addtional modules passing to Batch command',
                     'textarea': self.text_area, 'sub_str': 25, 'maxlen': 128},
         'environments': {'display_text': 'Environment<br>Variables', 'perms': 'ACEHMOQSTVX',
                          'description': 'Addtional environment variables passing to batch command',
                          'textarea': self.text_area, 'sub_str': 25, 'maxlen': 128},
         'qoptions': {'display_text': 'QSUB Options', 'perms': 'ACEHMOQSTVX',
                      'description': "Addtional options passing to PBS command 'qsub'",
                      'textarea': self.text_area, 'sub_str': 25, 'maxlen': 128},
         'argextra': {'display_text': 'Extra<br>Options', 'perms': 'ACHOSTVX',
                      'description': 'Additional command argument options beyond 100 characters', 'sub_str': 10,
                      'textarea': self.text_area},
         'errmsg': {'display_text': 'Error<br>Message', 'perms': 'HOSTVX',
                    'description': 'Accumulated error message during coomand execution', 'sub_str': 20,
                    'textarea': self.text_area},
      }
      ed = self.make_editor('dscheck', 'Current Check Information', 'cindex', 'ADCEHMOSUVX', columns)
      ed.set_config('tableInfo', 'cellpadding="2" width="1800" class="mateTable"')
      ed.set_config('orderByColumn', 'cindex')
      ed.set_config('addRowTitle', 'Add A Check Record')
      ed.set_config('viewRowTitle', 'View A Check Record')
      ed.set_config('refreshInterval', 30)     # refresh table/view every 30 seconds
      ed.set_lock_info('lockhost', 'chktime')
