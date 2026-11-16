"""Available hostnames (dssdb.hostname); port of dscheck_hostname.php."""

from ..editor.page import Page


class DscheckHostname(Page):
   title = 'Available Hostnames'

   def init_editor(self):
      columns = {
         'hostname': {'display_text': 'Host Name', 'perms': 'ACEOSTVX', 'description': 'avaible host names',
                      'maxlen': 20},
         'service': {'display_text': 'Service', 'perms': 'ACEHMOSTVX', 'description': 'Service the host is providing',
                     'req': True, 'default': 'A',
                     'select_array': {'A': 'Application Server', 'B': 'Batch Server', 'D': 'Database Server',
                                      'S': 'Data Storage Server', 'W': 'Web Server', 'N': 'Not In Service'},
                     'maxlen': 1},
         'downstart': {'display_text': 'System Down<br>Start Time', 'perms': 'ACEHMOSTVX',
                       'description': 'Time the system is down', 'input_info': 'style="width: 200px"',
                       'calendar': {'format': '%Y-%m-%d %H:%M:%S', 'reset': True}},
         'downend': {'display_text': 'System Down<br>End time', 'perms': 'ACEHMOSTVX',
                     'description': 'Time the system is up', 'input_info': 'style="width: 200px"',
                     'calendar': {'format': '%Y-%m-%d %H:%M:%S', 'reset': True}},
         'domain': {'display_text': 'Domain/Path', 'perms': 'ACEHOSTVX',
                    'description': 'Full host domain, i.e., rda-work.ucar.edu, or paths under service, '
                                   'i.e., /gpfs/fs1/collections/rda',
                    'maxlen': 80, 'sub_str': 30, 'input_info': 'style="width: 400px"', 'textarea': self.text_area},
         'note': {'display_text': 'Description', 'perms': 'ACEHOSTVX', 'description': 'Description for the host name',
                  'sub_str': 40, 'input_info': 'style="width: 400px"', 'textarea': self.text_area},
      }
      ed = self.make_editor('hostname', 'Available Hostname Information', 'hostname', 'ACDEHMOSUVX', columns)
      ed.set_config('tableInfo', 'cellpadding="2" width="1200" class="mateTable"')
      ed.set_config('orderByColumn', 'hostname')
      ed.set_config('addRowTitle', 'Add A Hostname')
      ed.set_config('editRowTitle', 'Edit A Hostname')
      ed.set_config('editMultTitle', 'Set Common Values for Multiple Hostnames')
      ed.set_config('viewRowTitle', 'View A Hostname')
