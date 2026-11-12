"""Web files of one dataset (dssdb.wfile_<dsid>); port of dsarch_webfile.php."""

import re

from ..editor.db import DSID_RE
from ..editor.engine import html_esc
from ..editor.page import Page, php_empty


class DsarchWebfile(Page):
   title = 'Web Files'

   def init_editor(self):
      grp, vrsn, back, tacc, uid = (self.get_group_title, self.get_version, self.get_back_file,
                                    self.get_tacc_file, self.get_specialist)
      columns = {
         'wid': {'display_text': 'Web<br>ID', 'perms': 'EOSTVX', 'description': 'Web File ID', 'valtype': 'integer'},
         'wfile': {'display_text': 'Web File Name', 'perms': 'EHOSTVX',
                   'description': 'Web file name, change via dsarch', 'maxlen': 128, 'sub_str': 50,
                   'input_info': 'style="width: 400px" readonly="readonly"', 'textarea': self.text_area},
         'uid': {'display_text': 'Owner<br>ID', 'perms': 'HOSTVX', 'valtype': 'integer',
                 'description': 'Specialist internal ID who owns this file', 'view_fun': uid},
         'gindex': {'display_text': 'Group<br>Index', 'perms': 'HOSTVX',
                    'description': 'Group index in a dataset if > 0', 'view_fun': grp, 'valtype': 'integer'},
         'tindex': {'display_text': 'Top<br>Group', 'perms': 'EHMOQSTVX',
                    'description': 'Top group index in a dataset if > 0', 'view_fun': grp, 'valtype': 'integer'},
         'data_size': {'display_text': 'Size', 'perms': 'HOSTVX', 'description': 'File size', 'data_precision': 2},
         'date_created': {'display_text': 'Time File Created', 'perms': 'HOSTVX',
                          'description': 'Time file was initially created',
                          'display_mask': "concat(date_created, ' ', time_created)"},
         'date_modified': {'display_text': 'Time File Modified', 'perms': 'HOSTVX',
                           'description': 'Time file was most recently modified',
                           'display_mask': "concat(date_modified, ' ', time_modified)"},
         'data_format': {'display_text': 'Data<br>Format', 'perms': 'EHMOQSTVX',
                         'description': 'Data content format, i.e. NetCDF', 'maxlen': 10},
         'file_format': {'display_text': 'Archive<br>Format', 'perms': 'EHMOQSTVX',
                         'description': 'File archive format, i.e. TAR.GZ', 'maxlen': 10},
         'checksum': {'display_text': 'MD5<br>Checksum', 'perms': 'HOSTVX',
                      'description': 'File md5 checksum', 'sub_str': 10},
         'locflag': {'display_text': 'Location<br>Flag', 'perms': 'EHMOSTVX', 'description': 'Storage Location Flag',
                     'select_array': {'C': 'CGD Data', 'G': 'Glade Disk', 'O': 'Object Store',
                                      'B': 'Both Storage Systems'}, 'maxlen': 1},
         'type': {'display_text': 'Type', 'perms': 'HOSTVX', 'description': 'Data type',
                  'select_array': {'D': 'Data', 'O': 'Document', 'S': 'Software', 'N': 'NCAR Data',
                                   'U': 'Unknown Type'}, 'maxlen': 1},
         'status': {'display_text': 'Status', 'perms': 'HOSTVX', 'description': 'File status',
                    'select_array': {'P': 'Public', 'I': 'Internal'}, 'maxlen': 1},
         'disp_order': {'display_text': 'Display<br>Order', 'perms': 'EHOTVX',
                        'description': 'Display order index of the file', 'maxlen': 9, 'valtype': 'integer',
                        'default': 1},
         'vindex': {'display_text': 'Version', 'perms': 'HOSTVX',
                    'description': 'Version Index links to DOI if > 0', 'view_fun': vrsn, 'valtype': 'integer'},
         'bid': {'display_text': 'Backup<br>ID', 'perms': 'HOSTVX',
                 'description': 'Links to Quasar Backup file if > 0', 'view_fun': back, 'valtype': 'integer'},
         'tid': {'display_text': 'TACC<br>ID', 'perms': 'HOSTVX',
                 'description': 'Links to TACC tar file if > 0', 'view_fun': tacc, 'valtype': 'integer'},
         'thredd_link': {'display_text': 'Thredd', 'perms': 'EHMOSTVX', 'description': 'Thredd catalog flag',
                         'maxlen': 1, 'default': 'N',
                         'select_array': {'Y': 'Thredd Catalog Built', 'N': 'No Thredd Catalog'}},
         'meta_link': {'display_text': 'Meta<br>Type', 'perms': 'EHMOSTVX',
                       'description': "Content metadata type if set and not 'N'", 'default': 'N', 'maxlen': 3},
         'note': {'display_text': 'Description', 'perms': 'EHOSTVX', 'description': 'File decription',
                  'sub_str': 16, 'textarea': self.text_large},
      }

      # the dataset comes from a set_dsid action, else from the session
      dsid = self.session.get('wfile_dsid', '')
      bad_dsid = None
      if self.action == 'set_dsid':
         dsid = re.sub(r'[^a-zA-Z0-9_-]', '', str(self.info or '').strip()).lower()
         if dsid and not DSID_RE.match(dsid):
            bad_dsid, dsid = dsid, ''
         self.session['wfile_dsid'] = dsid
      self.dsid = dsid

      table = 'wfile_' + dsid if dsid else 'wfile'
      title = ('Web File Information for {} (wfile_{})'.format(dsid, dsid) if dsid
               else 'Web Glade-Disk/Object-Store File Information')
      ed = self.make_editor(table, title, 'wid', 'EHMOSUVX', columns)
      ed.set_config('tableInfo', 'cellpadding="2" width="1600" class="mateTable"')
      ed.set_config('orderByColumn', 'wid')
      ed.set_config('editRowTitle', 'Edit A Web File')
      ed.set_config('viewRowTitle', 'View A Web File')
      ed.set_config('editMultTitle', 'Set Common Values For Multiple Web Files')
      if dsid:
         ed.set_config('sqlFilters', "status <> 'D'")
      else:
         ed.require_dsid = True
      if bad_dsid:
         ed.warnings.append('Invalid dataset id: {}'.format(bad_dsid))
      ed.user_actions['set_dsid'] = lambda info: ed.update_html()

   def pre_html(self):
      dsid = html_esc(self.session.get('wfile_dsid', ''))
      loaded = '&nbsp;<span style="font-style: italic;">Loaded: wfile_{}</span>'.format(dsid) if dsid else ''
      return '''   <div style="padding: 5px 0 10px 0;">
      Dataset ID: <input type="text" id="wfile_dsid_input" value="{}" size="15"
         onKeyPress="if(event.keyCode==13){{setWfileDsid(); return false;}}" />
      <button onclick="setWfileDsid();">Load Table</button>
      {}
   </div>
   <script type="text/javascript">
   function setWfileDsid() {{
      var dsid = $F('wfile_dsid_input');
      if (dsid) toAjaxTableEditor('set_dsid', dsid);
   }}
   </script>
'''.format(dsid, loaded)

   def get_group_title(self, col, val, row):
      if not php_empty(val) and (col == 'gindex' or val != row.get('gindex')):
         dsid = row.get('dsid') or self.session.get('wfile_dsid')
         if dsid:
            title = self.first('SELECT title FROM dsgroup WHERE gindex = %s AND dsid = %s', [val, dsid])
            if title is not None:
               val += ' - ' + title
      return val

   def get_version(self, col, val, row):
      if not php_empty(val):
         rec = self.first("SELECT concat(status, ' - ', doi) FROM dsvrsn WHERE vindex = %s", [val])
         if rec is not None:
            val += ' - ' + rec
      return val

   def get_back_file(self, col, val, row):
      if not php_empty(val):
         rec = self.first("SELECT concat(bfile, ' - ', type) FROM bfile WHERE bid = %s", [val])
         if rec is not None:
            val += ' - ' + rec
      return val

   def get_tacc_file(self, col, val, row):
      if not php_empty(val):
         rec = self.first('SELECT tfile FROM tfile WHERE tid = %s', [val])
         if rec is not None:
            val += ' - ' + rec
      return val

   def get_specialist(self, col, val, row):
      if not php_empty(val):
         rec = self.one('SELECT logname, lstname, fstname FROM dssdb.user WHERE uid = %s', [val])
         if rec:
            val += ' - {} ({} {})'.format(rec['logname'], rec['fstname'], rec['lstname'])
      return val
