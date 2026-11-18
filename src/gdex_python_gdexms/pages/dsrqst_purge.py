"""Request history (dssdb.dspurge); port of dsrqst_purge.php."""

from ..editor.page import Page, php_empty


class DsrqstPurge(Page):
   title = 'Request History'

   def init_editor(self):
      exe = self.format_interval
      columns = {
         'rindex': {'display_text': 'Request<br>Index', 'perms': 'EOSTVX',
                    'description': 'Request index, auto generated', 'maxlen': 9, 'valtype': 'integer'},
         'wuid_request': {'display_text': 'Public<br>User ID', 'perms': 'HOSTVX',
                          'description': 'Public user identification number', 'default': 0, 'maxlen': 9,
                          'valtype': 'integer'},
         'email': {'display_text': 'User Email', 'perms': 'HOSTVX',
                   'description': 'Email address of request email', 'maxlen': 80, 'sub_str': 20,
                   'input_info': 'style="width: 400px"', 'textarea': self.text_area},
         'dsid': {'display_text': 'Dataset<br>ID', 'perms': 'HOSTVX',
                  'description': 'Dataset Identification Number', 'input_info': "style='width: 400px'",
                  'select_query': self.select_dsid},
         'gindex': {'display_text': 'Group<br>Index', 'perms': 'HOSTVX',
                    'description': 'Group Index for given dataset', 'default': 0, 'valtype': 'integer',
                    'view_fun': self.get_group_title},
         'rqsttype': {'display_text': 'Type', 'perms': 'HOSTVX',
                      'description': 'Request Type', 'default': 'C', 'req': True, 'maxlen': 1,
                      'select_array': {'M': 'Stage Data from HPSS', 'S': 'Subset Request',
                                       'F': 'Data Format Conversion', 'H': 'Format Conversion for Data on HPSS',
                                       'C': 'Customized Data Request', 'T': ' Subset With/Without Format Conversion',
                                       'N': 'NCARDAP(THREDDS) Data Server', 'R': 'Realtime Data Request'}},
         'size_request': {'display_text': 'Data Size<br>Requested', 'perms': 'EHOSTVX',
                          'description': 'Amount of Data requested', 'default': 0, 'maxlen': 20,
                          'valtype': 'integer', 'data_precision': 2},
         'size_input': {'display_text': 'Data Size<br>To Process', 'perms': 'EHOSTVX',
                        'description': 'Amount of data processed as input', 'default': 0, 'maxlen': 20,
                        'valtype': 'integer', 'data_precision': 2},
         'fcount': {'display_text': 'File<br>Count', 'perms': 'HOSTVX',
                    'description': 'Number of files requested', 'default': 0, 'maxlen': 11, 'valtype': 'integer'},
         'ptcount': {'display_text': 'Partition<br>Count', 'perms': 'HOSTVX',
                     'description': 'Number of partitions in the request', 'maxlen': 6, 'valtype': 'integer'},
         'time_request': {'display_text': 'Time Requested', 'display_mask': "concat(date_rqst, ' ', time_rqst)",
                          'perms': 'HOSTVX', 'description': 'Time request is submitted',
                          'input_info': 'style="width: 200px"', 'sub_str': 20},
         'time_ready': {'display_text': 'Time Ready', 'display_mask': "concat(date_ready, ' ', time_ready)",
                        'perms': 'HOSTVX', 'description': 'Time requested data are ready',
                        'input_info': 'style="width: 200px"'},
         'time_purge': {'display_text': 'Time Purged', 'display_mask': "concat(date_purge, ' ', time_purge)",
                        'perms': 'HOSTVX', 'description': 'Time requested data are purged',
                        'input_info': 'style="width: 200px"'},
         'specialist': {'display_text': 'Specialist', 'perms': 'HOSTVX',
                        'description': 'Specialist responsible for the request', 'req': True,
                        'select_query': self.select_specialist, 'query_column': 'logname',
                        'default': self.specialist},
         'fromflag': {'display_text': 'From', 'perms': 'HOSTVX',
                      'description': 'From where request is submitted', 'maxlen': 1,
                      'select_array': {'A': 'From RDA APPS_API', 'C': 'From Commandline',
                                       'M': 'Submitted Manually By Specialist',
                                       'S': 'From a Script via Wget/curl/Python', 'W': 'From Web Interface'}},
         'subflag': {'display_text': 'Subset<br>Flag', 'perms': 'EHMOSTVX',
                     'description': 'Subset bit flag, 1 - Variable, 2 - Temporal, 4 - Spatial',
                     'default': 7, 'maxlen': 1, 'valtype': 'integer',
                     'select_array': {'1': 'Variable Subset Only', '2': 'Temporal Subset Only',
                                      '3': 'Variable & Temporal Subset', '4': 'Spacial Subset Only',
                                      '5': 'Variable & Spacial Subset', '7': 'Variable, Temporal & Spacial Subset'}},
         'data_format': {'display_text': 'Data<br>Format', 'perms': 'EHMOSTVX',
                         'description': 'Data content format, i.e. NetCDF', 'maxlen': 10},
         'file_format': {'display_text': 'Archive<br>Format', 'perms': 'EHMOSTVX',
                         'description': 'File archive format, i.e. TAR.GZ', 'maxlen': 10},
         'location': {'display_text': 'Location', 'perms': 'HOSTVX',
                      'description': 'Path to stage request data if differ from the default location',
                      'maxlen': 128, 'sub_str': 12, 'input_info': 'style="width: 400px"',
                      'textarea': self.text_area},
         'note': {'display_text': 'Note', 'perms': 'EHOSTVX',
                  'description': 'Addtional request information, in readable format', 'sub_str': 10,
                  'textarea': self.text_area, 'view_fun': self.preserve_text},
         'rinfo': {'display_text': 'Request<br>Info', 'perms': 'EHOSTVX',
                   'description': 'Additional request information, mainly for subsetting',
                   'sub_str': 10, 'textarea': self.text_area},
         'exectime': {'display_text': 'Execution<br>Time', 'perms': 'EHMOSTVX',
                      'description': 'Execution time to build request', 'maxlen': 9,
                      'valtype': 'integer', 'table_fun': exe, 'view_fun': exe},
         'globus_rid': {'display_text': 'Globus rule ID', 'perms': 'OSTVX',
                        'description': 'Rule ID assigned to the Globus data share permission'},
         'globus_url': {'display_text': 'Globus share URL', 'perms': 'OSTVX',
                        'description': 'URL to Globus data sharing endpoint', 'maxlen': 128},
         'task_id': {'display_text': 'Globus task ID', 'perms': 'OSTVX',
                     'description': 'Transfer task ID for Globus push transfers', 'maxlen': 36},
      }
      ed = self.make_editor('dspurge', 'Request History', 'rindex', 'EHMOSUVX', columns)
      ed.set_config('tableInfo', 'cellpadding="2" width="1800" class="mateTable"')
      ed.set_config('orderByColumn', 'rindex')
      ed.set_config('addRowTitle', 'Add A Request History Record')
      ed.set_config('editRowTitle', 'Edit A Request History Record')
      ed.set_config('viewRowTitle', 'View A Request History Record')
      ed.set_config('editMultTitle', 'Set Comman Values for Multiple Request History Records')

   def get_group_title(self, col, val, row):
      if not php_empty(val) and (col == 'gindex' or val != row.get('gindex')):
         title = self.first('SELECT title FROM dsgroup WHERE gindex = %s AND dsid = %s', [val, row.get('dsid')])
         if title is not None:
            val += ' - ' + title
      return val
