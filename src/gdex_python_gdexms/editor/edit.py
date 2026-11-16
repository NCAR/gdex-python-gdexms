"""Editing, record locks and column preferences for the table editor engine.

A port of the write half of rda-pg-config's php/AjaxTableEditor.inc: the add,
edit, copy and edit-multiple forms, insert/update/delete, the record locks
(setLockInfo/checkLockInfo/clearLockInfo) and the per-user column show/hide/order
screens (mate_columns). TableEditor (engine.py) mixes this class in.

Differences from the PHP, on purpose:
- Every value is bound; a submitted field is written only when it is a column of
  the page with the right permission (A to insert, E to update, E+M to update
  several rows). The PHP wrote any field name it was sent.
- Each insert/update/delete runs in one transaction together with its after-hook,
  so a failed hook rolls the change back.
- A record lock is kept until the update that follows the edit screen has run;
  the PHP released it at the start of that request. The update is refused when
  the lock was lost in between.
- Reset Column Order resets only the current user's order; the PHP reset it for
  every user of the page.
- psql_add_fun now works on insert (the PHP added it to an unused list).

This file is derived from the PostgreSQL/MySQL Ajax Table Editor,
Copyright (c) 2008 Chris Kitchen <info@mysqlajaxtableeditor.com>, modified for
rda_pg_config by Zaihua Ji, and is distributed under the GNU Lesser General
Public License v3 (see LICENSE-LGPL in this repository).
"""

import time
from urllib.parse import parse_qs

from .db import valid_ident
from .lang import LANG

LOCK_HOST = 'rda_config'       # lock host name the daemons see on a record being edited
UPDATE_ACTIONS = ('update_row', 'update_mult_rows')


def _str(val):
   """A submitted value as the PHP saw it: a trimmed string, '' for null."""
   if val is None:
      return ''
   if isinstance(val, bool):
      return '1' if val else ''
   return str(val).strip()


class EditMixin:
   """Write actions of TableEditor; relies on the engine's query building and helpers."""

   # ---- dispatch ------------------------------------------------------------

   def handle_edit_flow(self, action, info):
      """Run a write/column action; returns False when action is not one of them."""
      if action == 'add_row':
         self.add_row()
      elif action == 'copy_row':
         self.add_row()        # the PHP shows the add form filled from the copied row
      elif action == 'insert_row':
         self.insert_row()
         if not self.val_error:
            self.update_html()
      elif action == 'edit_row':
         self.edit_row()
      elif action == 'update_row':
         self.update_row()
         if not self.val_error:
            self.update_html()
      elif action == 'edit_mult_rows':
         self.edit_mult_rows()
      elif action == 'update_mult_rows':
         self.update_mult_rows()
         if not self.val_error:
            self.update_html()
      elif action == 'copy_mult_rows':
         self.copy_mult_rows()
         self.update_html()
      elif action == 'delete_row':
         self.delete_row()
      elif action == 'delete_mult_rows':
         self.delete_mult_rows()
      elif action == 'release_lock':
         if self.lock_info and self.lock_info.get('id') is not None:
            self.clear_lock_info()
      elif action == 'show_hide_columns':
         self.show_hide_columns()
      elif action == 'show_column':
         self.set_column_pref(_str(info), hidden='No')
      elif action == 'hide_column':
         self.hide_column()
      elif action == 'order_columns_screen':
         self.order_columns_screen()
      elif action == 'update_column_order':
         self.update_column_order()
      elif action == 'reset_column_order':
         self.reset_column_order()
      elif action == 'user_icon_clicked':
         self.user_icon_clicked()
      elif action == 'user_button_clicked':
         self.user_button_clicked()
      else:
         return False
      return True

   # ---- helpers -------------------------------------------------------------

   def log_change(self, sqlstr, vals, count):
      """Record a data change in the PgDBI log, with the specialist who made it."""
      pglog = getattr(self.db, 'pglog', None)
      if pglog:
         pglog('gdexms {}: {} {} ({} row(s))'.format(self.user or '?', ' '.join(sqlstr.split()), vals, count),
               getattr(self.db, 'MSGLOG', 0))

   def fetch_record(self, row_id):
      """The table row with primary key row_id (all columns), or None."""
      row = self.db.query_one('select * from ' + self.sc_and_table + ' where ' + self.primary_col + ' = %s',
                              [row_id])
      return {k: _php(v) for k, v in row.items()} if row else None

   def key_cond(self, ids, key=None):
      """'<key> in (%s, ...)' for the given ids, with its values."""
      key = key or self.primary_col
      return key + ' in (' + ', '.join(['%s'] * len(ids)) + ')', list(ids)

   def has_rights_to_rows(self, ids):
      """True when every id is a row the current page would show (filters and search applied)."""
      if not ids:
         return False
      saved = self.columns
      self.unset_hidden_columns()
      self.set_paging_vars()
      self.format_join_clause()
      self.format_where_clause()
      self.columns = saved
      cond, vals = self.key_cond(ids, self.sc_and_table + '.' + self.primary_col)
      where = (self.where_clause + ' and ' if self.where_clause else ' where ') + cond
      sqlstr = ('select count(distinct ' + self.sc_and_table + '.' + self.primary_col + ') as num from '
                + self.sc_and_table + ' ' + self.join_clause + ' ' + where)
      row = self.db.query_one(sqlstr, list(self.where_vals) + vals)
      self.join_clause = self.where_clause = ''
      return bool(row) and int(row['num']) == len(set(ids))

   def handle_hacking(self):
      """The PHP exited silently; tell the specialist instead."""
      self.warnings.append('You do not have rights to change this record.')

   def label_style(self, col, error):
      style = self.val_error_styles if error else self.no_val_error_styles
      self.ret.append({'where': 'javascript', 'value': '$("{}_label_cell").setStyle("{}");'.format(col, style)})

   def call_fun(self, info, name, *args):
      fun = info.get(name)
      return fun(*args) if callable(fun) else None

   # ---- form building -------------------------------------------------------

   def get_default_value(self, col, info, cur):
      self.defined_default = info.get('default')
      val = cur.get(col)
      if val is not None and len(str(val)) > 0:
         if self.defined_default is not None and info.get('calendar') and str(val)[:10] == '0000-00-00':
            return _str(self.defined_default)
         return str(val)
      if self.defined_default is not None:
         return _str(self.defined_default)
      if self.adv_searches and self.search_type == 'advanced' and self.match_all:
         for search in self.adv_searches:
            if search.get('cols') == col and search.get('opts') == '=':
               return search.get('strs', '')
      return ''

   def get_input_info(self, info, action, row_id=None):
      parts = [info['input_info']] if info.get('input_info') else []
      if info.get('onchange'):
         if action == 'add':
            parts.append('onchange="refreshAddPage(\'{}\');"'.format(self.var_prefix))
         elif action == 'edit' and isinstance(row_id, str):
            parts.append('onchange="refreshEditPage(\'{}\', \'{}\');"'.format(_js(row_id), self.var_prefix))
         elif action == 'edit_multi' and isinstance(row_id, list):
            parts.append('onchange="refreshMultEditPage(new Array(\'{}\'),\'{}\');"'.format(
               "','".join(_js(i) for i in row_id), self.var_prefix))
      if info.get('maxlen') and int(info['maxlen']) > 0:
         parts.append('maxlength="{}"'.format(int(info['maxlen'])))
      return ' '.join(parts)

   @staticmethod
   def get_valid_key_press(info):
      return " else {{return validate_keypress(event, '{}');}}".format(info['valtype']) if info.get('valtype') else ''

   def get_cal_js(self, cal, col, hide=0):
      if isinstance(cal, dict):
         fmt = cal.get('format', self.default_js_cal_format)
         reset = 1 if 'reset' in cal else 0
         extra = cal.get('extra_info', '')
      else:
         fmt = cal if isinstance(cal, str) else self.default_js_cal_format
         reset, extra = 0, ''
      return "prepareForCalendar(document.getElementById('{0}'),'{0}','{1}',{2},'{3}',{4});".format(
         col, fmt, reset, extra, hide)

   def get_select(self, query, name, default='', other='', exclusive=False):
      multiple = 'multiple' in (other or '')
      opts = ''
      if exclusive and multiple:
         sel = ' selected="selected"' if default.startswith('!') else ''
         opts = '<option value="!"{}>! - {}</option>'.format(sel, LANG['exclusiveSelect'])
      found_default = found_defined = False
      defined = self.defined_default
      for rec in self.db.query(query):
         raw = list(rec.values())
         value = '' if raw[0] is None else str(_php(raw[0]))
         # the PHP showed "value - text" when a second column is set (isset: not NULL)
         text = value if len(raw) < 2 or raw[1] is None else value + ' - ' + str(_php(raw[1]))
         if (multiple and value in default) or value == default:
            sel, found_default = ' selected="selected"', True
         else:
            sel = ''
         opts += '<option value="{}"{}>{}</option>'.format(_attr(value), sel, _html(text))
         if defined is not None and value == _str(defined):
            found_defined = True
      html = '<select id="{0}" name="{0}" {1}>'.format(name, other)
      if not multiple:
         if defined is not None and not found_defined:
            sel_default = _str(defined)
            sel_text = (sel_default + ' - ' if sel_default else '') + LANG['optionalDefault']
         else:
            sel_default, sel_text = '', LANG['lblSelect']
         sel = '' if found_default else ' selected="selected"'
         html += '<option value="{}"{}>{}</option>'.format(_attr(sel_default), sel, _html(sel_text))
      return html + opts + '</select>'

   def get_select_from_array(self, choices, name, default='', other='', exclusive=False):
      multiple = 'multiple' in (other or '')
      opts = ''
      if exclusive and multiple:
         sel = ' selected="selected"' if default.startswith('!') else ''
         opts = '<option value="!"{}>{}</option>'.format(sel, LANG['exclusiveSelect'])
      found_default = False
      for value, text in choices.items():
         value = str(value)
         if (multiple and value in default) or value == default:
            opts += '<option value="{}" selected="selected">{} - {}</option>'.format(_attr(value), _html(value),
                                                                                   _html(text))
            found_default = True
         else:
            opts += '<option value="{}">{} - {}</option>'.format(_attr(value), _html(value), _html(text))
      html = '<select id="{0}" name="{0}" {1}>'.format(name, other)
      if not multiple:
         sel = '' if found_default else ' selected="selected"'
         html += '<option value="{}"{}>{}</option>'.format(_attr(default), sel, LANG['lblSelect'])
      return html + opts + '</select>'

   def input_html(self, col, info, def_val, input_info, js_fun, mode, row):
      """One form input, chosen the way the PHP add/edit/edit-multiple screens did."""
      exclusive = bool(info.get('exclusive'))
      hidden = info.get('hidden_add' if mode == 'add' else 'hidden_edit')
      if callable(info.get('format_input_fun')):
         if mode == 'add':
            return info['format_input_fun'](col, def_val, input_info)
         return info['format_input_fun'](col, def_val, row, input_info)
      if hidden:
         return '<input type="hidden" id="{}" value="{}" {} />'.format(col, _attr(def_val), input_info)
      if 'select_query' in info:
         return self.get_select(info['select_query'], col, def_val, input_info, exclusive)
      if isinstance(info.get('select_array'), dict):
         return self.get_select_from_array(info['select_array'], col, def_val, input_info, exclusive)
      if 'textarea' in info:
         area = info['textarea'] or {}
         return '<textarea id="{}" rows="{}" cols="{}" {} >{}</textarea>'.format(
            col, area.get('rows', 7), area.get('cols', 25), input_info, _html(def_val))
      if 'checkbox' in info:
         box = info['checkbox'] or {}
         on, off = _js(box.get('checked_value', '')), _js(box.get('un_checked_value', ''))
         checked = 'checked="checked"' if def_val == str(box.get('checked_value', '')) else ''
         return ('<input type="checkbox" id="{}" value="{}" onclick="updateCheckBoxValue(this,\'{}\',\'{}\');" '
                 '{} {} />').format(col, _attr(def_val), on, off, checked, input_info)
      if isinstance(info.get('join'), dict):
         join = info['join']
         table = (join['db'] + '.' + join['table']) if join.get('db') else join['table']
         mask = join.get('display_mask') or table + '.' + join['column']
         query = 'select distinct({}), {} from {} order by {} asc'.format(join['column'], mask, table, mask)
         return self.get_select(query, col, def_val, input_info)
      if 'calendar' in info:
         return '<span><input type="hidden" id="{}" value="{}" /></span>'.format(col, _attr(def_val))
      readonly = 'readonly="readonly" ' if mode == 'edit' and col == self.primary_col else ''
      if mode == 'edit_multi' and info.get('maxlen'):
         input_info = 'maxlength="{}" '.format(int(info['maxlen'])) + input_info
      return ('<input type="text" {}id="{}" value="{}" onKeyPress="if(enterPressed(event)){{{} return false;}}{}" '
              '{} />').format(readonly, col, _attr(def_val), js_fun, self.get_valid_key_press(info), input_info)

   def form_row(self, col, info, input_html, desc=True):
      if info.get('req'):
         input_html += self.req_marker
      text = info['display_text'].replace('<br>', ' ')
      html = ('<tr><td id="{0}_label_cell" class="labelCell"><label for="{0}">{1}:</label></td>'
              '<td id="{0}_input_cell" class="inputCell">{2}</td>').format(col, text, input_html)
      if desc and self.has_description:
         html += '<td><small><i>{}</i></small></td>'.format(info.get('description') or '&nbsp;')
      return html + '</tr>'

   def show_form(self, title, html, cal_js, screen_fun):
      self.ret.append({'layer_id': 'titleLayer', 'where': 'innerHTML', 'value': title})
      self.ret.append({'layer_id': 'recordLayer', 'where': 'innerHTML', 'value': html})
      self.ret.append({'where': 'javascript', 'value': 'showRecordPane();'})
      if cal_js:
         self.ret.append({'where': 'javascript', 'value': '\n'.join(cal_js)})
      if callable(screen_fun):
         screen_fun()

   # ---- add / copy ----------------------------------------------------------

   def add_row(self):
      if 'A' not in self.permissions:
         return
      vp = self.var_prefix
      js_add = "addRow('{}');".format(vp)
      row = {}
      if isinstance(self.info, dict):
         row = {k: _str(v) for k, v in self.info.items()}         # refreshAddPage
      elif isinstance(self.info, (str, int)) and _str(self.info):
         row_id = _str(self.info)                                 # copy_row
         if self.has_rights_to_rows([row_id]):
            row = self.fetch_record(row_id) or {}
            for col, info in self.columns.items():
               if col in row and 'C' not in info.get('perms', ''):
                  del row[col]
      html = '<form id="{0}_add_form" name="{0}_add_form"><table {1}>'.format(vp, self.add_table_info)
      cal_js = []
      for col, info in self.columns.items():
         if callable(info.get('column_fun')):
            info = info['column_fun'](col, '', row)
         if 'A' not in info.get('perms', '') or _join_real(info):
            continue
         def_val = self.get_default_value(col, info, row)
         input_info = self.get_input_info(info, 'add')
         if callable(info.get('add_fun')):
            def_val = _str(info['add_fun'](col, def_val, row))
         if def_val and not row.get(col):
            row[col] = def_val
         inp = self.input_html(col, info, def_val, input_info, js_add, 'add', row)
         html += inp if info.get('hidden_add') else self.form_row(col, info, inp)
         if 'calendar' in info:
            cal_js.append(self.get_cal_js(info['calendar'], col))
      html += ('</table></form><div id="addRowButtons"><button class="ajaxButton" onclick="{}">{}</button>'
               '<button class="ajaxButton" onclick="toAjaxTableEditor(\'update_html\',\'\');">{}</button></div>'
               ).format(js_add, LANG['btnAdd'], LANG['btnCancel'])
      self.show_form(self.add_row_title, html, cal_js, self.add_screen_fun)

   def copy_mult_rows(self):
      ids = [_str(i) for i in _items(self.info)]
      for row_id in ids:
         if not self.has_rights_to_rows([row_id]):
            self.handle_hacking()
            return
         row = self.fetch_record(row_id)
         if not row:
            continue
         record = {}
         for col, info in self.columns.items():
            if 'C' in info.get('perms', '') and not _join_real(info):
               val = row.get(col, '')
               if callable(info.get('on_copy_fun')):
                  val = info['on_copy_fun'](col, val, row)
               record[valid_ident(col)] = _str(val)
         if record:
            with self.db.transaction():
               new_id = self.insert_record(record)
               if callable(self.after_copy_fun):
                  self.after_copy_fun(new_id, record)

   # ---- edit ----------------------------------------------------------------

   def edit_row(self):
      if 'E' not in self.permissions:
         return
      refresh = isinstance(self.info, dict)
      if refresh:
         form = dict(self.info)
         row_id = _str(form.pop('old_primary_key_value', ''))
      else:
         row_id, form = _str(self.info), {}
      row = self.fetch_record(row_id) if row_id else None
      if not row:
         self.ret.append({'where': 'javascript', 'value': "toAjaxTableEditor('update_html','{}');".format(
            _js('Edit screen was closed for the editing record is gone!'))})
         return
      for col, val in form.items():
         row[col] = _str(val)
      vp = self.var_prefix
      js_update = "updateRow('{}','{}');".format(_js(row_id), vp)
      html = '<form id="{0}_edit_form" name="{0}_edit_form"><table {1}>'.format(vp, self.edit_table_info)
      cal_js = []
      for col, info in self.columns.items():
         if callable(info.get('column_fun')):
            info = info['column_fun'](col, '', row)
         if 'E' not in info.get('perms', '') or _join_real(info):
            continue
         def_val = self.get_default_value(col, info, row)
         input_info = self.get_input_info(info, 'edit', row_id)
         if callable(info.get('edit_fun')):
            def_val = _str(info['edit_fun'](col, def_val, row))
         if def_val and not row.get(col):
            row[col] = def_val
         inp = self.input_html(col, info, def_val, input_info, js_update, 'edit', row)
         html += inp if info.get('hidden_edit') else self.form_row(col, info, inp)
         if 'calendar' in info:
            cal_js.append(self.get_cal_js(info['calendar'], col))
      html += self.update_buttons(js_update)
      self.show_form(self.edit_row_title, html, cal_js, self.edit_screen_fun)
      if not self.lock_info or self.check_lock_info('edit', row_id):
         self.ret.append({'where': 'javascript', 'value': 'set_edit_timeout();'})

   def update_buttons(self, js_update):
      return ('</table></form><div id="editRowButtons"><button class="ajaxButton" id="{0}_update" '
              'name="{0}_update" onclick="{1}">{2}</button><button class="ajaxButton" '
              'onclick="toAjaxTableEditor(\'update_html\',\'\');">{3}</button></div>').format(
                 self.var_prefix, js_update, LANG['btnUpdate'], LANG['btnCancel'])

   def edit_mult_rows(self):
      if 'E' not in self.permissions:
         return
      if not self.allow_edit_mult:
         self.warnings.append(LANG['edit1Row'])
         return
      if isinstance(self.info, dict) and 'inputInfo' in self.info:
         ids = [_str(i) for i in _items(self.info.get('idArr'))]
         form = self.info.get('inputInfo') or {}
      else:
         ids, form = [_str(i) for i in _items(self.info)], {}
      ids = [i for i in ids if i]
      row = self.fetch_record(ids[0]) if ids else None
      html = ''
      cal_js = []
      vp = self.var_prefix
      js_update = "updateMultRows(new Array('{}'),'{}');".format("','".join(_js(i) for i in ids), vp)
      if row:
         for col, val in (form.items() if isinstance(form, dict) else []):
            row[col] = _str(val)
         html = '<form id="{0}_edit_form" name="{0}_edit_form"><table {1}>'.format(vp, self.edit_table_info)
         for col, info in self.columns.items():
            if callable(info.get('column_fun')):
               info = info['column_fun'](col, '', row)
            perms = info.get('perms', '')
            if 'E' not in perms or 'M' not in perms or _join_real(info) or col == self.primary_col:
               continue
            def_val = self.get_default_value(col, info, row)
            input_info = self.get_input_info(info, 'edit_multi', ids) + ' disabled="disabled"'
            if callable(info.get('edit_fun')):
               def_val = _str(info['edit_fun'](col, def_val, row))
            inp = self.input_html(col, info, def_val, input_info, js_update, 'edit_multi', row)
            if info.get('hidden_edit'):
               html += inp
            else:
               if info.get('req'):
                  inp += '<span id="{}_req_mark" style="display: none;">{}</span>'.format(col, self.req_marker)
               html += ('<tr><td id="{0}_label_cell" class="labelCell"><label for="{0}">{1}:</label></td>'
                        '<td id="{0}_input_cell" class="inputCell">{2}</td><td><input type="checkbox" '
                        'id="{0}_em_cb" onchange="disableEnableInput(\'{0}\',this);" /></td></tr>').format(
                           col, info['display_text'], inp)
            if 'calendar' in info:
               cal_js.append(self.get_cal_js(info['calendar'], col, 1))
         html += self.update_buttons(js_update)
      title = self.edit_mult_title.replace('Multiple', str(len(ids)))
      self.show_form(title, html, cal_js, self.edit_screen_fun)
      if ids and (not self.lock_info or self.check_lock_info('edit', ids)):
         self.ret.append({'where': 'javascript', 'value': 'set_edit_timeout();'})

   # ---- submitted values ----------------------------------------------------

   def collect_values(self, form, mode):
      """Validate submitted fields; returns ({sql column: (template, value)}, {col: value}).

      mode is 'add', 'edit' or 'mult'. A field that is not a writable column of
      the page is ignored (the PHP wrote it anyway).
      """
      flag = 'A' if mode == 'add' else 'E'
      sets, after = {}, {}
      for col, raw in form.items():
         col = str(col)
         info = self.columns.get(col)
         if info is None:
            continue
         if callable(info.get('column_fun')):
            info = info['column_fun'](col, '', form)
         perms = info.get('perms', '')
         if flag not in perms or (mode == 'mult' and 'M' not in perms) or _join_real(info):
            continue
         val = _str(raw)
         hook = 'on_add_fun' if mode == 'add' else 'on_edit_fun'
         if callable(info.get(hook)):
            val = _str(info[hook](col, val, form))
         if info.get('calendar') and val[:10] == '0000-00-00':
            val = ''
         hidden = info.get('hidden_add' if mode == 'add' else 'hidden_edit')
         if callable(info.get('val_fun')) and not info['val_fun'](col, val, form):
            self.val_error = True
            self.label_style(col, True)
         elif info.get('req') and len(val) == 0:
            self.val_error = True
            self.label_style(col, True)
         elif not hidden:
            self.label_style(col, False)
         if mode == 'add' and len(val) == 0 and info.get('default') is not None:
            val = _str(info['default'])
         sql_fun = info.get('psql_add_fun' if mode == 'add' else 'psql_edit_fun')
         if sql_fun:
            sets[valid_ident(col)] = (valid_ident(sql_fun) + '(%s)', val)
            after[col] = val
         elif callable(info.get('psql_fun')):
            values = info['psql_fun'](col, val, form)
            if values:
               for field, value in values.items():
                  sets[valid_ident(field)] = ('%s', _str(value))
               after[col] = val
         else:
            sets[valid_ident(col)] = ('%s', val if len(val) > 0 else None)
            after[col] = val
      return sets, after

   def insert_record(self, record):
      """Insert {column: value or (template, value)}; returns the new primary key value."""
      cols, temps, vals = [], [], []
      for col, val in record.items():
         temp, val = val if isinstance(val, tuple) else ('%s', val if val != '' else None)
         cols.append(col)
         temps.append(temp)
         vals.append(val)
      sqlstr = 'insert into {}({}) values({}) returning {}'.format(
         self.sc_and_table, ', '.join(cols), ', '.join(temps), self.primary_col)
      row = self.db.query_one(sqlstr, vals)
      self.log_change(sqlstr, vals, 1)
      return _php(next(iter(row.values()))) if row else None

   def insert_row(self):
      self.val_error = False
      form = self.info if isinstance(self.info, dict) else {}
      sets, after = self.collect_values(form, 'add')
      if self.val_error:
         self.ret.append({'layer_id': 'titleLayer', 'where': 'innerHTML',
                          'value': self.add_row_title + '<div style="color: #f90d0d;">' + LANG['errVal'] + '</div>'})
         return
      if not sets:
         return
      with self.db.transaction():
         new_id = self.insert_record(sets)
         if callable(self.after_add_fun):
            self.after_add_fun(new_id, self.primary_col, after)

   def run_update(self, sets, ids):
      """UPDATE the rows ids with sets; returns the row count."""
      assigns = ', '.join('{} = {}'.format(col, temp) for col, (temp, _) in sets.items())
      cond, cvals = self.key_cond(ids)
      sqlstr = 'update {} set {} where {}'.format(self.sc_and_table, assigns, cond)
      vals = [val for _, val in sets.values()] + cvals
      count = self.db.execute(sqlstr, vals)
      self.log_change(sqlstr, vals, count)
      return count

   def lock_still_held(self, ids):
      """When the page locks records, check this request still holds the lock on ids."""
      lock = self.lock_info
      if not lock:
         return True
      if lock.get('id') is None or sorted(_items(lock['id'])) != sorted(ids):
         return False
      cond, vals = self.key_cond(ids)
      sqlstr = 'select count(*) as num from {} where {} and pid = %s and {} = %s'.format(
         lock['table'], cond, lock['host'])
      row = self.db.query_one(sqlstr, vals + [lock['pid'], LOCK_HOST])
      return bool(row) and int(row['num']) == len(ids)

   def update_row(self):
      self.val_error = False
      form = dict(self.info) if isinstance(self.info, dict) else {}
      row_id = _str(form.pop('old_primary_key_value', ''))
      if not row_id or not self.has_rights_to_rows([row_id]):
         self.handle_hacking()
         self.val_error = True
         return
      sets, after = self.collect_values(form, 'edit')
      if self.val_error:
         self.ret.append({'layer_id': 'titleLayer', 'where': 'innerHTML',
                          'value': self.edit_row_title + '<div style="color: #f90d0d;">' + LANG['errVal'] + '</div>'})
         return
      if not self.lock_still_held([row_id]):
         self.warnings.append(LANG['errLockLost'])
         return
      if not sets:
         return
      with self.db.transaction():
         if self.run_update(sets, [row_id]) > 0 and callable(self.after_edit_fun):
            self.after_edit_fun(row_id, self.primary_col, after)

   def update_mult_rows(self):
      self.val_error = False
      info = self.info if isinstance(self.info, dict) else {}
      ids = [i for i in (_str(x) for x in _items(info.get('idArr'))) if i]
      form = info.get('inputInfo') if isinstance(info.get('inputInfo'), dict) else {}
      if not form or not ids:
         return
      sets, after = self.collect_values(form, 'mult')
      if self.val_error:
         self.ret.append({'layer_id': 'titleLayer', 'where': 'innerHTML',
                          'value': self.edit_row_title + '<div style="color: #f90d0d;">' + LANG['errVal'] + '</div>'})
         return
      if not sets:
         return
      if not self.has_rights_to_rows(ids):
         self.handle_hacking()
         return
      if not self.lock_still_held(ids):
         self.warnings.append(LANG['errLockLost'])
         return
      with self.db.transaction():
         if self.run_update(sets, ids) > 0 and callable(self.after_edit_fun):
            self.after_edit_fun(ids, self.primary_col, after)

   # ---- delete --------------------------------------------------------------

   def delete_row(self):
      if 'D' not in self.permissions:
         return
      row_id = _str(self.info)
      if self.delete_rows([row_id]):
         self.update_html()

   def delete_mult_rows(self):
      if 'D' not in self.permissions:
         return
      self.delete_rows([i for i in (_str(x) for x in _items(self.info)) if i])
      self.update_html()

   def delete_rows(self, ids):
      if not ids:
         return False
      if self.lock_info and not self.check_lock_info('delete', ids if len(ids) > 1 else ids[0]):
         return False
      if callable(self.check_delete_fun) and not self.check_delete_fun(ids if len(ids) > 1 else ids[0],
                                                                      self.primary_col):
         return False
      if not self.has_rights_to_rows(ids):
         self.handle_hacking()
         return False
      deleted = 0
      with self.db.transaction():
         for row_id in ids:
            sqlstr = 'delete from {} where {} = %s'.format(self.sc_and_table, self.primary_col)
            count = self.db.execute(sqlstr, [row_id])
            self.log_change(sqlstr, [row_id], count)
            if count > 0:
               deleted += count
               if callable(self.after_delete_fun):
                  self.after_delete_fun(row_id, self.primary_col)
      if self.lock_info:
         self.lock_info['id'] = None       # the locked rows are gone
         self.sset('lockInfo', None)
      return deleted > 0

   # ---- record locks --------------------------------------------------------

   def set_lock_info(self, host_field, time_field):
      """AjaxTableEditor::setLockInfo: start a lock context for this request.

      A lock left by an earlier request is released, except for the update that
      follows the edit screen: it keeps the lock until the update has run.
      """
      old = self.lock_info
      if old and old.get('id') is not None:
         if getattr(self, 'request_action', '') in UPDATE_ACTIONS and old.get('table') == self.sc_and_table:
            return
         self.clear_lock_info()
      self.lock_info = {'pid': int(time.time()), 'table': self.sc_and_table, 'id': None,
                        'key': self.primary_col, 'host': valid_ident(host_field),
                        'time': valid_ident(time_field)}

   def clear_lock_info(self):
      lock = self.lock_info
      ids = [_str(i) for i in _items(lock['id'])] if isinstance(lock.get('id'), list) else [_str(lock['id'])]
      cond, vals = self.key_cond(ids, valid_ident(lock['key']))
      sqlstr = "update {} set {} = '', pid = 0 where {} and pid = %s and {} = %s".format(
         lock['table'], lock['host'], cond, lock['host'])
      self.db.execute(sqlstr, vals + [lock['pid'], LOCK_HOST])
      self.sset('lockInfo', None)
      lock['id'] = None

   def check_lock_info(self, action, row_id):
      """Lock the record(s) for editing or deleting; False (and a message) when they are locked."""
      lock = self.lock_info
      ids = [_str(i) for i in row_id] if isinstance(row_id, list) else [_str(row_id)]
      count, s = len(ids), 's' if isinstance(row_id, list) else ''
      key, host = lock['key'], lock['host']
      cond, vals = self.key_cond(ids, key)
      locked = self.db.query_one('select {0}, {1}, pid from {2} where {3} and pid > 0 and {1} > %s limit 1'.format(
         key, host, lock['table'], cond), vals + [' '])
      disp = self.columns.get(key, {}).get('display_text', key).replace('<br>', ' ')
      if locked:
         by = '{} {} is locked by {}({})!'.format(disp, _php(locked[key]), _php(locked[host]), _php(locked['pid']))
         if action == 'edit':
            self.ret.append({'where': 'javascript', 'value': 'disableEditPage("{}", "{}");'.format(
               self.var_prefix, _js('Cannot edit {} record{}, for {}'.format(count, s, by)))})
         else:
            self.warnings.append('Cannot delete {} record{}! {}'.format(count, s, by))
         return False
      sqlstr = ('update {0} set {1} = %s, pid = %s, {2} = %s where {3} and (pid = 0 or pid = %s and {1} = %s)'
                .format(lock['table'], host, lock['time'], cond))
      ucount = self.db.execute(sqlstr, [LOCK_HOST, lock['pid'], int(time.time())] + vals + [lock['pid'], LOCK_HOST])
      if ucount == count:
         lock['id'] = ids if isinstance(row_id, list) else ids[0]
         self.sset('lockInfo', dict(lock))
         return True
      if ucount > 0:
         self.db.execute("update {0} set {1} = '', pid = 0 where {2} and pid = %s and {1} = %s".format(
            lock['table'], host, cond), vals + [lock['pid'], LOCK_HOST])
      msg = 'Cannot {} for FAIL to lock {} record{}'.format(action, count, s)
      if action == 'edit':
         self.ret.append({'where': 'javascript', 'value': 'disableEditPage("{}", "{}");'.format(
            self.var_prefix, _js(msg))})
      else:
         self.warnings.append(msg)
      return False

   # ---- column show/hide and order (mate_columns) ---------------------------

   def set_column_pref(self, col, hidden=None, order_num=None):
      """Insert or update this user's mate_columns row for col."""
      uid = self.mate_user_id()
      rec = self.db.query_one('select id from mate_columns where mate_user_id = %s and mate_var_prefix = %s '
                              'and mate_column = %s', [uid, self.var_prefix, col])
      if rec:
         sets, vals = [], []
         if hidden is not None:
            sets.append('hidden = %s')
            vals.append(hidden)
         if order_num is not None:
            sets.append('order_num = %s')
            vals.append(order_num)
         self.db.execute('update mate_columns set ' + ', '.join(sets) + ' where id = %s', vals + [rec['id']])
      else:
         self.db.execute('insert into mate_columns(mate_user_id, mate_var_prefix, mate_column, order_num, hidden, '
                         'date_updated) values(%s, %s, %s, %s, %s, now())',
                         [uid, self.var_prefix, col, order_num or 0, hidden or 'No'])

   def hide_column(self):
      col = _str(self.info)
      if 'H' in self.columns.get(col, {}).get('perms', ''):
         self.set_column_pref(col, hidden='Yes')
         if self.search_type == 'advanced':
            searches = [s if s.get('cols') != col else {} for s in (self.sget('advSearches') or [])]
            self.sset('advSearches', searches)
         if self.sget('obc') == col:
            self.session.pop(self.var_prefix + 'obc', None)

   def show_hide_columns(self):
      if 'H' not in self.permissions:
         return
      uid = self.mate_user_id()
      prefs = {r['mate_column']: r['hidden'] for r in self.db.query(
         'select mate_column, hidden from mate_columns where mate_user_id = %s and mate_var_prefix = %s',
         [uid, self.var_prefix])}
      html = '<table {}><tr style="font-weight: bold;"><td>{}</td><td>{}</td></tr>'.format(
         self.show_hide_table_info, LANG['ttlColumn'], LANG['ttlCheckBox'])
      for col, info in self.columns.items():
         if 'H' in info.get('perms', '') and col != self.primary_col:
            hidden = prefs[col] == 'Yes' if col in prefs else bool(info.get('hidden'))
            checked = '' if hidden else 'checked="checked"'
            html += ('<tr><td><label for="{0}_hide_cb">{1}</label>:</td><td><input type="checkbox" id="{0}_hide_cb" '
                     'onchange="showHideColumn(this,\'{0}\');" {2} /></tr>').format(col, info['display_text'], checked)
      html += '</table>'
      self.column_screen(self.show_hide_title, html, '<button onclick="toAjaxTableEditor(\'update_html\',\'\');">'
                         + LANG['btnBack'] + '</button>')

   def column_screen(self, title, html, buttons):
      self.ret.append({'layer_id': 'titleLayer', 'where': 'innerHTML', 'value': title})
      self.ret.append({'layer_id': 'recordLayer', 'where': 'innerHTML', 'value': ''})
      self.ret.append({'where': 'javascript', 'value': 'hideRecordPane();'})
      self.ret.append({'layer_id': 'searchButtonsLayer', 'where': 'innerHTML', 'value': buttons})
      self.ret.append({'layer_id': 'tableLayer', 'where': 'innerHTML', 'value': html})

   def order_columns_screen(self):
      if 'O' not in self.permissions:
         return
      self.unset_hidden_columns()
      self.set_column_order()
      html = '<ul id="columnOrderList">'
      for col, info in self.columns.items():
         if 'O' in info.get('perms', ''):
            html += '<li id="columnOrderList_{}" class="orderColumnClass">{}</li>'.format(
               col.replace('_', '-.-UNDERSCORE-.-'), info['display_text'])
      html += '</ul>'
      self.column_screen(self.order_col_title, html,
                         '<button onclick="toAjaxTableEditor(\'reset_column_order\',\'\');">' + LANG['btnReset']
                         + '</button> <button onclick="toAjaxTableEditor(\'update_html\',\'\');">' + LANG['btnBack']
                         + '</button>')
      self.ret.append({'where': 'javascript', 'value': (
         'Sortable.create("columnOrderList",{dropOnEmpty:false,constraint:false,onUpdate:function(element)'
         '{var info = Sortable.serialize(element.id); toAjaxTableEditor("update_column_order",info); } });')})

   def update_column_order(self):
      if 'O' not in self.permissions:
         return
      cols = parse_qs(_str(self.info)).get('columnOrderList[]', [])
      num = 1
      for col in cols:
         col = col.replace('-.-UNDERSCORE-.-', '_')
         if 'O' in self.columns.get(col, {}).get('perms', ''):
            self.set_column_pref(col, order_num=num)
            num += 1

   def reset_column_order(self):
      self.db.execute("update mate_columns set order_num = 0 where mate_user_id = %s and mate_var_prefix = %s",
                      [self.mate_user_id(), self.var_prefix])
      self.order_columns_screen()

   # ---- user icons and buttons ----------------------------------------------

   def user_icon_clicked(self):
      info = list(_items(self.info)) + ['', '']
      row_id, key = _str(info[0]), _str(info[1])
      icon = self.user_icons.get(key, {})
      row = self.fetch_record(row_id)
      if row and callable(icon.get('call_back_fun')):
         icon['call_back_fun'](row)
      if not icon.get('no_update'):
         self.update_html()

   def user_button_clicked(self):
      info = self.info if isinstance(self.info, dict) else {}
      button = self.user_buttons.get(_str(info.get('buttonKey')), {})
      boxes = info.get('checkboxes') or {}
      params = button.get('params', [])
      if button.get('pass_id_array'):
         if callable(button.get('call_back_fun')):
            button['call_back_fun'](boxes, params)
      else:
         for row_id in _items(boxes):
            row = self.fetch_record(_str(row_id))
            if row and callable(button.get('call_back_fun')):
               button['call_back_fun'](row, params)
      if not button.get('no_update'):
         self.update_html()


def _items(info):
   if isinstance(info, dict):
      return list(info.values())
   if isinstance(info, (list, tuple)):
      return list(info)
   return [] if info in (None, '') else [info]


def _join_real(info):
   return isinstance(info.get('join'), dict) and 'real_column' in info['join']


def _php(val):
   from .engine import php_str
   return php_str(val)


def _js(text):
   from .engine import js_str
   return js_str(text)


def _html(text):
   from .engine import html_esc
   return html_esc(text)


def _attr(text):
   from .engine import html_esc
   return html_esc(text)
