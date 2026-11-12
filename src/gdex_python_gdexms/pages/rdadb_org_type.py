"""Organization types (dssdb.org_type); port of rdadb_org_type.php."""

from ..editor.page import Page


class OrgType(Page):
   title = 'Organization Types'

   def init_editor(self):
      columns = {
         'org_type': {'display_text': 'Organization<br> Type', 'perms': 'AEOSTVX',
                      'description': 'Organization type short name', 'maxlen': 5},
         'description': {'display_text': 'Description', 'perms': 'ACEHOSTVX',
                         'description': 'Organization type description', 'maxlen': 255,
                         'input_info': 'style="width: 400px"', 'textarea': self.text_area},
      }
      ed = self.make_editor('org_type', 'Organization Type Information', 'org_type', 'ADEHMOSUVX', columns)
      ed.set_config('tableInfo', 'cellpadding="1" width="800" class="mateTable"')
      ed.set_config('orderByColumn', 'org_type')
      ed.set_config('addRowTitle', 'Add A Organization Type')
      ed.set_config('editRowTitle', 'Edit A Organization Type')
      ed.set_config('viewRowTitle', 'View A Organization Type')
