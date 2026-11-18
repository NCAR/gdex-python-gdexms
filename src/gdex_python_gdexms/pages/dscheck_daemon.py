"""Dscheck daemon controls (dssdb.dsdaemon); port of dscheck_daemon.php."""

from ..editor.page import Page


class DscheckDaemon(Page):
   title = 'Daemon Control'

   def init_editor(self):
      columns = {
         'dindex': {'display_text': 'Daemon<br>Index', 'perms': 'EOSTVX',
                    'description': 'Auto generated daemon control index', 'valtype': 'integer'},
         'command': {'display_text': 'Control<br>Command', 'perms': 'ACEHMOSTVX',
                     'description': 'Application name to be controlled, ALL for any command', 'req': True,
                     'maxlen': 20, 'default': 'ALL'},
         'hostname': {'display_text': 'Host Name', 'perms': 'ACEHMOSTVX',
                      'description': 'Host name the application is controlled on', 'req': True,
                      'input_info': "style='width: 200px'",
                      'select_query': "select hostname, note from hostname where service in ('A','W') "
                                      "ORDER by hostname"},
         'matchhost': {'display_text': 'Match<br>Host', 'perms': 'ACEHMOSTVX', 'maxlen': 1,
                       'description': 'Flag for how to determine if a check command can be run on this host',
                       'req': True,
                       'select_array': {'G': 'Match Hostname Generally', 'I': 'Match Hostname Inclusively',
                                        'M': 'Match Hostname Exactly'}, 'default': 'G'},
         'specialist': {'display_text': 'Specialist', 'perms': 'ACEHMOSTVX',
                        'description': 'Specialist responsible for the command', 'req': True,
                        'select_query': self.select_specialist, 'query_column': 'logname',
                        'default': self.specialist},
         'proclimit': {'display_text': 'Process<br>Limit', 'perms': 'ACEHMOSTVX',
                       'description': 'Maximum number of processes of given command can be run concurrently on a host',
                       'default': 1, 'maxlen': 6, 'valtype': 'integer'},
         'priority': {'display_text': 'Priority', 'perms': 'ACEHMOSTVX',
                      'description': 'Priority on which host to start application, 0 highest & 10 lowest',
                      'default': 0, 'maxlen': 4, 'valtype': 'integer'},
      }
      ed = self.make_editor('dsdaemon', 'Dscheck Daemon Control Information', 'dindex', 'ACDEHMOSUVX', columns)
      ed.set_config('tableInfo', 'cellpadding="2" width="900" class="mateTable"')
      ed.set_config('orderByColumn', 'dindex')
      ed.set_config('addRowTitle', 'Add A Daemon Control')
      ed.set_config('editRowTitle', 'Edit A Daemon Control')
      ed.set_config('editMultTitle', 'Set Common Values for Multiple Daemon Controls')
      ed.set_config('viewRowTitle', 'View A Daemon Control')
