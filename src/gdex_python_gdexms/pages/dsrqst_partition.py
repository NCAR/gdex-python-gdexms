"""Request partitions (dssdb.ptrqst); port of dsrqst_partition.php."""

from ..editor.page import Page


class DsrqstPartition(Page):
   title = 'Request Partition'

   def init_editor(self):
      run = self.display_running_status
      columns = {
         'pindex': {'display_text': 'Partition<br>Index', 'perms': 'EOSTVX',
                    'description': 'Auto generated request partition index', 'valtype': 'integer'},
         'rindex': {'display_text': 'Request<br>Index', 'req': True, 'perms': 'EHMOSTVX',
                    'description': 'Request index', 'maxlen': 9, 'input_info': 'readonly="readonly"',
                    'valtype': 'integer'},
         'ptorder': {'display_text': 'Partition<br>Order', 'req': True, 'perms': 'EHMOSTVX',
                     'description': 'partition order, 1 2 3 ...', 'maxlen': 6, 'valtype': 'integer'},
         'dsid': {'display_text': 'Dataset<br>ID', 'perms': 'ACHOSTVX',
                  'description': 'Dataset Identification Number', 'req': True, 'input_info': "style='width: 400px'",
                  'select_query': self.select_dsid},
         'specialist': {'display_text': 'Specialist', 'perms': 'ACEHMOSTVX',
                        'description': 'Specialist responsible for the partition', 'req': True,
                        'select_query': self.select_specialist, 'query_column': 'logname',
                        'default': self.specialist},
         'fcount': {'display_text': 'File<br>Count', 'perms': 'AEHOSTVX',
                    'description': 'Number of files in the partition', 'default': 0, 'maxlen': 11,
                    'valtype': 'integer'},
         'tarcount': {'display_text': 'Tar File<br>Count', 'perms': 'AEHOSTVX',
                      'description': 'Number of Tar files in the partition', 'default': 0, 'maxlen': 11,
                      'valtype': 'integer'},
         'status': {'display_text': 'Status', 'perms': 'AEHMOSTVX',
                    'description': 'Requst partition status', 'default': 'Q', 'req': True, 'maxlen': 1,
                    'select_array': {'Q': 'Queued to be procssed or In Process',
                                     'O': 'Process is Done and Data Ready Online'}},
         'partition': {'display_text': 'Execution Status', 'perms': 'HOTVX',
                       'description': 'Display process id and host name if the partition is under processing',
                       'sub_str': 40, 'display_mask': "concat(pid, ' ', lockhost)",
                       'table_fun': run, 'view_fun': run},
      }
      ed = self.make_editor('ptrqst', 'Request Partition Information', 'pindex', 'ACEHMOSUVX', columns)
      ed.set_config('tableInfo', 'cellpadding="1" width="1000" class="mateTable"')
      ed.set_config('orderByColumn', 'pindex')
      ed.set_config('addRowTitle', 'Add A Request Partition')
      ed.set_config('editRowTitle', 'Edit A Request Partition')
      ed.set_config('viewRowTitle', 'View A Request Partition')
      ed.set_config('editMultTitle', 'Set Comman Values for Multiple Request Partitions')
