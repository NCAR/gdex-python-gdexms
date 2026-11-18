"""Request controls (dssdb.rcrqst); port of dsrqst_control.php."""

from ..editor.page import Page, php_empty


class DsrqstControl(Page):
   title = 'Request Control'

   def init_editor(self):
      col_fun, val_fun, fmt = self.select_group_index, self.valid_group_index, self.format_link
      columns = {
         'cindex': {'display_text': 'Control<br>Index', 'perms': 'EOQSTVX',
                    'description': 'Request Control Index', 'valtype': 'integer'},
         'dsid': {'display_text': 'Dataset<br>ID', 'perms': 'ACEMOSTVX',
                  'description': 'Dataset Identification Number', 'req': True, 'input_info': "style='width: 400px'",
                  'select_query': self.select_dsid, 'onchange': True},
         'gindex': {'display_text': 'Group<br>Index', 'perms': 'ACEHMOSTVX',
                    'description': 'Group Index for given dataset', 'default': 0, 'valtype': 'integer',
                    'maxlen': 9, 'val_fun': val_fun, 'column_fun': col_fun},
         'rqsttype': {'display_text': 'Type', 'perms': 'ACEHMOQSTVX',
                      'description': 'Request Type', 'default': 'S', 'maxlen': 1,
                      'select_array': {'M': 'Stage Data from HPSS', 'S': 'Subset Request',
                                       'F': 'Data Format Conversion', 'H': 'Format Conversion for Data on HPSS',
                                       'C': 'Customized Data Request',
                                       'T': ' Subset With/Without Format Conversion',
                                       'N': 'NCARDAP(THREDDS) Data Server', 'Q': 'Database Query Request',
                                       'R': 'Realtime Data Request'}},
         'validperiod': {'display_text': 'Valid<br>Period', 'perms': 'ACEHMOQSTVX',
                         'description': 'Number of days for data staging; 0 using system default (5 days)',
                         'valtype': 'integer', 'default': 0},
         'control': {'display_text': 'Control<br>Mode', 'perms': 'ACEHMOQSTVX',
                     'description': 'Request Control Mode', 'default': 'S', 'maxlen': 1,
                     'select_array': {'S': 'By Specialist', 'A': 'Automatic Processing'}},
         'specialist': {'display_text': 'Specialist', 'perms': 'ACEHMOQSTVX',
                        'description': 'Specialist Reponsible for the Requests', 'req': True,
                        'query_column': 'logname', 'select_query': self.select_specialist,
                        'default': self.specialist},
         'data_format': {'display_text': 'Data<br>Format', 'perms': 'ACEHMOQSTVX',
                         'description': 'Data content format, i.e. NetCDF', 'maxlen': 10},
         'file_format': {'display_text': 'Archive<br>Format', 'perms': 'ACEHMOQSTVX',
                         'description': 'File archive format, i.e. TAR.GZ', 'maxlen': 10},
         'to_format': {'display_text': 'Output<br>Format', 'perms': 'ACEHMOQSTVX',
                       'description': 'Output Data content format, i.e. NetCDF:GRIB', 'maxlen': 80},
         'tarflag': {'display_text': 'Tar<br>Flag', 'perms': 'ACEHMOQSTVX',
                     'description': 'Reduce file count by tarring small request files', 'default': 'Y',
                     'maxlen': 1, 'select_array': {'Y': 'To Tar small files', 'N': 'Do not tar files'}},
         'empty_out': {'display_text': 'Empty<br>Output', 'perms': 'ACEHMOQSTVX',
                       'description': 'Allow Empty Output File or Not', 'default': 'N', 'maxlen': 1,
                       'select_array': {'Y': 'Empty Output Allowed', 'N': 'Empty Output Not Allowed'}},
         'hostname': {'display_text': 'Host<br>Name', 'perms': 'ACEHMOQSTVX',
                      'description': 'Hostname(s), separated by :, to build requests on; leading by ! for not on',
                      'select_query': "select hostname, note from hostname where service in ('A', 'W')",
                      'exclusive': True, 'input_info': 'multiple="true" separator=":"', 'maxlen': 80, 'su_str': 20},
         'command': {'display_text': 'Command To Build Request', 'perms': 'ACEHMOQSTVX',
                     'description': 'Specify a customized command to build requests',
                     'textarea': self.text_area, 'sub_str': 25, 'maxlen': 128},
         'validsubset': {'display_text': 'Validate<br>Subset Request', 'perms': 'ACEHMOQSTVX',
                         'description': 'Specify a customized command to validate the subset request information',
                         'textarea': self.text_area, 'sub_str': 25, 'maxlen': 128},
         'rqstlimit': {'display_text': 'Size<br>Limit', 'perms': 'ACEHMOQSTVX',
                       'description': 'Up Limit(GB) of data for each request', 'default': 0, 'valtype': 'integer'},
         'maxperiod': {'display_text': 'Max<br>Period', 'perms': 'ACEHMOQSTVX',
                       'description': 'Set Maximum Default Request Period, i.e, 1Y or 10M',
                       'maxlen': 4, 'valtype': 'frequency'},
         'ptlimit': {'display_text': 'Partition<br>Limit', 'perms': 'ACEHMOQSTVX',
                     'description': 'Up Limit of file count for each partition', 'default': 0, 'valtype': 'integer'},
         'ptsize': {'display_text': 'Partition<br>Size', 'perms': 'ACEHMOQSTVX',
                    'description': 'Up Limit of data size for each partition', 'default': 0, 'valtype': 'integer'},
         'ptflag': {'display_text': 'Partition<br>Flag', 'perms': 'ACEHMOQSTVX',
                    'description': 'Partition command call flag', 'default': 'N', 'maxlen': 1,
                    'select_array': {'N': 'Call to add partition only',
                                     'P': 'Call to add and process partition',
                                     'F': 'Call to add partition and build the reuqest',
                                     'B': 'Call command to do all'}},
         'maxrqst': {'display_text': 'Count<br>Limit', 'perms': 'ACEHMOQSTVX',
                     'description': 'Maximum count of outstanding requests from one user; 0 for no limit',
                     'default': 0, 'valtype': 'integer'},
         'modules': {'display_text': 'Modules', 'perms': 'ACEHMOQSTVX',
                     'description': 'Additional modules passing to Batch command',
                     'textarea': self.text_area, 'sub_str': 25, 'maxlen': 128},
         'environments': {'display_text': 'Environment<br>Variables', 'perms': 'ACEHMOQSTVX',
                          'description': 'Additional environment variables passing to batch command',
                          'textarea': self.text_area, 'sub_str': 25, 'maxlen': 128},
         'priority': {'display_text': 'Priority', 'perms': 'ACEHOSTVX', 'default': 5,
                      'description': 'process priority other than request date/time', 'maxlen': 6,
                      'valtype': 'integer'},
         'qoptions': {'display_text': 'QSUB Options', 'perms': 'ACEHMOQSTVX',
                      'description': "Additional options passing to PBS command 'qsub'",
                      'textarea': self.text_area, 'sub_str': 25, 'maxlen': 128},
         'url': {'display_text': 'URL to Submit Request', 'perms': 'ACEHMOQSTVX',
                 'description': 'Specify a URL link to accept requests', 'table_fun': fmt, 'view_fun': fmt,
                 'textarea': self.text_area, 'maxlen': 255},
         'enotice': {'display_text': 'Email<br>File', 'perms': 'ACEHMOQSTVX',
                     'description': 'A filename with full path for customized email notice',
                     'textarea': self.text_area, 'sub_str': 25, 'maxlen': 128},
         'ccemail': {'display_text': 'Carbon<br>Copy', 'perms': 'ACEHMOQSTVX',
                     'default': 'S', 'description': 'Carbon copy emails; S for the specialist and N for no carbon copy',
                     'textarea': self.text_area, 'maxlen': 255, 'sub_str': 25, 'edit_fun': self.set_carbon_copy},
         'note': {'display_text': 'Description', 'perms': 'ACEHOQSTVX',
                  'description': 'Description for update control record', 'textarea': self.text_area, 'sub_str': 25},
      }
      ed = self.make_editor('rcrqst', 'Request Control Information', 'cindex', 'ACDEHMOSUVX', columns)
      ed.set_config('tableInfo', 'cellpadding="2" width="1500" class="mateTable"')
      ed.set_config('orderByColumn', 'cindex')
      ed.set_config('addRowTitle', 'Add A Request Control')
      ed.set_config('editRowTitle', 'Edit A Request Control')
      ed.set_config('editMultTitle', 'Set Comman Values for Multiple Request Controls')
      ed.set_config('viewRowTitle', 'View A Request Control')

   @staticmethod
   def set_carbon_copy(col, val, row):
      """edit_fun: an empty carbon copy field means no carbon copy ('N')."""
      if php_empty(row.get(col)):
         val = 'N'
      return val
