"""Request information (dssdb.dsrqst); port of dsrqst_request.php."""

import re

from ..editor.page import Page


class DsrqstRequest(Page):
   title = 'Request Information'

   def init_editor(self):
      run = self.display_running_status
      columns = {
         'rindex': {'display_text': 'Request<br>Index', 'perms': 'EOSTVX',
                    'description': 'Auto generated request index'},
         'rqstid': {'display_text': 'Request Id', 'perms': 'EHOSTVX',
                    'description': 'request id; directory name', 'maxlen': 40, 'sub_str': 20,
                    'input_info': 'style="width: 200px"', 'req': True},
         'email': {'display_text': 'User Email', 'perms': 'ACEHMOSTVX',
                   'description': 'Email address of request email', 'maxlen': 80, 'sub_str': 20,
                   'input_info': 'style="width: 400px"', 'textarea': self.text_area,
                   'val_fun': self.valid_email},
         'dsid': {'display_text': 'Dataset<br>ID', 'perms': 'ACHOSTVX',
                  'description': 'Dataset Identification Number', 'req': True, 'input_info': "style='width: 400px'",
                  'select_query': self.select_dsid, 'onchange': True},
         'gindex': {'display_text': 'Group<br>Index', 'perms': 'ACHOSTVX',
                    'description': 'Group Index for given dataset', 'default': 0, 'valtype': 'integer',
                    'val_fun': self.valid_group_index, 'column_fun': self.select_group_index},
         'rqsttype': {'display_text': 'Type', 'perms': 'AEHMOQSTVX',
                      'description': 'Request Type', 'default': 'C', 'req': True, 'maxlen': 1,
                      'select_array': {'M': 'Stage Data from HPSS', 'S': 'Subset Request',
                                       'F': 'Data Format Conversion', 'H': 'Format Conversion for Data on HPSS',
                                       'C': 'Customized Data Request', 'T': ' Subset With/Without Format Conversion',
                                       'N': 'NCARDAP(THREDDS) Data Server', 'Q': 'Database Query Request',
                                       'R': 'Realtime Data Request'}},
         'status': {'display_text': 'Status', 'perms': 'AEHMOSTVX',
                    'description': 'Requst status', 'default': 'W', 'req': True, 'maxlen': 1,
                    'select_array': {'W': 'Wait to be Granted', 'Q': 'Queued to be procssed or In Process',
                                     'O': 'Process is Done and Data Ready Online', 'P': 'Ready to be Purged'}},
         'tarflag': {'display_text': 'Tar<br>Flag', 'perms': 'ACEHMOQSTVX',
                     'description': 'Reduce file count by tarring small request files', 'default': 'Y',
                     'maxlen': 1, 'select_array': {'Y': 'To Tar small files', 'N': 'Do not tar files'}},
         'dsrqst': {'display_text': 'Execution Status', 'perms': 'HOTVX',
                    'description': 'Display process id and host name if the request is under processing',
                    'sub_str': 40, 'display_mask': "concat(pid, ' ', lockhost)", 'table_fun': run, 'view_fun': run},
         'size_request': {'display_text': 'Data Size<br>Requested', 'perms': 'AEHMOSTVX',
                          'description': 'Amount of Data requested', 'default': 0, 'maxlen': 20,
                          'valtype': 'integer', 'data_precision': 2},
         'size_input': {'display_text': 'Data Size<br>To Process', 'perms': 'AEHMOSTVX',
                        'description': 'Amount of data processed as input', 'default': 0, 'maxlen': 20,
                        'valtype': 'integer', 'data_precision': 2},
         'fcount': {'display_text': 'File<br>Count', 'perms': 'AEHOSTVX',
                    'description': 'Number of files requested', 'default': 0, 'maxlen': 11, 'valtype': 'integer'},
         'tarcount': {'display_text': 'Tar File<br>Count', 'perms': 'AEHOSTVX',
                      'description': 'Number of Tar files', 'default': 0, 'maxlen': 11, 'valtype': 'integer'},
         'ptcount': {'display_text': 'Partition<br>Count', 'perms': 'HOSTVX',
                     'description': 'Number of partitions in the request', 'maxlen': 6, 'valtype': 'integer'},
         'time_request': {'display_text': 'Time Requested', 'display_mask': "concat(date_rqst, ' ', time_rqst)",
                          'perms': 'HOSTVX', 'description': 'Time request is submitted',
                          'input_info': 'style="width: 200px"', 'sub_str': 20},
         'time_ready': {'display_text': 'Time Ready', 'display_mask': "concat(date_ready, ' ', time_ready)",
                        'perms': 'HOSTVX', 'description': 'Time requested data are ready',
                        'input_info': 'style="width: 200px"'},
         'date_purge': {'display_text': 'Date To Purge', 'perms': 'EM',
                        'description': 'Date request is due to be purged', 'input_info': 'style="width: 200px"',
                        'calendar': {'format': '%Y-%m-%d', 'reset': True}},
         'time_purge': {'display_text': 'Time To Purge', 'display_mask': "concat(date_purge, ' ', time_purge)",
                        'perms': 'EHMOSTVX', 'description': 'Time request is due to be purged',
                        'default': '00:00:00'},
         'specialist': {'display_text': 'Specialist', 'perms': 'ACEHMOSTVX',
                        'description': 'Specialist responsible for the request', 'req': True,
                        'select_query': self.select_specialist, 'query_column': 'logname',
                        'default': self.specialist},
         'fromflag': {'display_text': 'From', 'perms': 'HOSTVX',
                      'description': 'From where request is submitted', 'maxlen': 1,
                      'select_array': {'A': 'From RDA APPS_API', 'C': 'From Commandline',
                                       'M': 'Submitted Manually By Specialist',
                                       'S': 'From a Script via Wget/curl/Python', 'W': 'From Web Interface'}},
         'priority': {'display_text': 'Priority', 'perms': 'ACEHOSTVX', 'default': 5,
                      'description': 'process priority other than request date/time', 'maxlen': 6,
                      'valtype': 'integer'},
         'data_format': {'display_text': 'Data<br>Format', 'perms': 'ACEHMOQSTVX',
                         'description': 'Data content format, i.e. NetCDF', 'maxlen': 10},
         'file_format': {'display_text': 'Archive<br>Format', 'perms': 'ACEHMOQSTVX',
                         'description': 'File archive format, i.e. TAR.GZ', 'maxlen': 10},
         'location': {'display_text': 'Location', 'perms': 'AEHOSTVX',
                      'description': 'Path to stage request data if different from the default location',
                      'maxlen': 128, 'sub_str': 12, 'input_info': 'style="width: 400px"',
                      'textarea': self.text_area},
         'ptlimit': {'display_text': 'Partition<br>Limit', 'perms': 'EHMOQSTVX',
                     'description': 'Up Limit of file count for each partition', 'default': 0, 'valtype': 'integer'},
         'ptsize': {'display_text': 'Partition<br>Size', 'perms': 'EHMOQSTVX',
                    'description': 'Up Limit of data size for each partition', 'default': 0, 'valtype': 'integer'},
         'command': {'display_text': 'Command To<br>Build Request', 'perms': 'ACEHMOQSTVX',
                     'description': 'Specify a customized commmand to build this request',
                     'textarea': self.text_area, 'sub_str': 25, 'maxlen': 128},
         'hostname': {'display_text': 'Host<br>Name', 'perms': 'ACEHMOQSTVX',
                      'description': 'Hostname(s), separated by :, to build requests on; leading by ! for not on',
                      'select_query': "select hostname, note from hostname where service in ('A', 'W')",
                      'exclusive': True, 'input_info': 'multiple="true" separator=":"', 'maxlen': 80, 'su_str': 20},
         'enotice': {'display_text': 'Email<br>Template', 'perms': 'ACEHOSTVX',
                     'description': 'Path to a customized email template if differ from the default one',
                     'maxlen': 128, 'sub_str': 20, 'input_info': 'style="width: 400px"',
                     'textarea': self.text_area},
         'note': {'display_text': 'Note', 'perms': 'ACEHMOTVX',
                  'description': 'Additional request information, in readable format', 'sub_str': 10,
                  'textarea': self.text_area, 'view_fun': self.preserve_text},
         'rinfo': {'display_text': 'Request<br>Info', 'perms': 'ACEHOTVX',
                   'description': 'Additional request information, mainly for subsetting',
                   'sub_str': 10, 'textarea': self.text_area},
         'globus_rid': {'display_text': 'Globus rule ID', 'perms': 'EOSTVX',
                        'description': 'Rule ID assigned to the Globus data share permission'},
         'globus_url': {'display_text': 'Globus share URL', 'perms': 'EOSTVX',
                        'description': 'URL to Globus data sharing endpoint', 'maxlen': 128},
         'session_id': {'display_text': 'Session ID', 'perms': 'OSTVX',
                        'description': 'User session ID (needed for Globus push transfers)', 'maxlen': 32},
         'globus_transfer': {'display_text': 'Globus push transfer', 'perms': 'EOSTVX',
                             'description': 'Flag indicating Globus push transfer (Y/N)', 'maxlen': 1},
         'endpoint_id': {'display_text': 'Destination endpoint ID', 'perms': 'OSTVX',
                         'description': 'Destination endpoint ID for Globus push transfers', 'maxlen': 36},
         'dest_path': {'display_text': 'Globus destination path', 'perms': 'EOSTVX',
                       'description': 'Destination path for Globus push transfers', 'maxlen': 256},
         'task_id': {'display_text': 'Globus task ID', 'perms': 'OSTVX',
                     'description': 'Transfer task ID for Globus push transfers', 'maxlen': 36},
      }
      ed = self.make_editor('dsrqst', 'Request Information', 'rindex', 'ACEHMOSUVX', columns)
      ed.set_config('tableInfo', 'cellpadding="2" width="2000" class="mateTable"')
      ed.set_config('orderByColumn', 'rindex')
      ed.set_config('addRowTitle', 'Add A Request')
      ed.set_config('editRowTitle', 'Edit A Request')
      ed.set_config('viewRowTitle', 'View A Request')
      ed.set_config('editMultTitle', 'Set Comman Values for Multiple Requests')
      ed.set_config('refreshInterval', 60)     # refresh table/view every 60 seconds
      ed.set_config('afterAddFun', self.set_default_values)
      ed.set_config('beforeEditArray', ['status'])
      # the PHP registered this as 'AfterEditFun', so check_status never ran there
      ed.set_config('afterEditFun', self.check_status)
      ed.set_lock_info('lockhost', 'locktime')

   def set_default_values(self, row_id, pkey, values):
      """After adding a request: mark it manual, stamp the request time and build rqstid from the user name."""
      date, time = self.get_date_time().split(' ')
      sets = ["fromflag = 'M'", 'date_rqst = %s', 'time_rqst = %s']
      vals = [date, time]
      email = values.get('email')
      if email:
         lstname = self.first('select lname lstname from ruser where email = %s AND end_date IS NULL', [email])
         if lstname is None:
            lstname = self.first('select lstname from wuser where email = %s AND until_date IS NULL', [email])
         if lstname is None:
            m = re.match(r'^(.+)@', email)
            lstname = m.group(1) if m else ''
         sets.append('rqstid = %s')
         vals.append(self.convert_chars(lstname, 'RQST').upper() + str(row_id))
      self.db.execute('UPDATE dsrqst SET {} WHERE {} = %s'.format(', '.join(sets), pkey), vals + [row_id])

   def check_status(self, row_id, pkey, values):
      """After editing, requeue the errored partitions of each request moved from E to Q."""
      if values.get('status') != 'Q':
         return
      ids = row_id if isinstance(row_id, list) else [row_id]
      before = self.editor.before_edit or {}
      for rindex in ids:
         if (before.get(str(rindex)) or {}).get('status') == 'E':
            self.db.execute("UPDATE dssdb.ptrqst SET status = 'Q' WHERE rindex = %s AND status = 'E'", [rindex])
