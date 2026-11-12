"""Table editor engine: a Python port of rda-pg-config's php/AjaxTableEditor.inc.

The browser code (js/ajax_table_editor.js) is unchanged, so this engine answers
the same protocol: a POST with form field json={"action": ..., "info": ...}
returns a JSON list of {"layer_id", "where", "value"} entries that the browser
applies (innerHTML assignments and JavaScript to eval). The HTML fragments are
built here, as in the PHP.

Differences from the PHP, on purpose:
- Every value from the browser is bound as a query parameter (cndvals); column
  names, sort columns and search operators are checked against the page config.
- Join aliases are deterministic (<table>_j<n>) instead of random.

Phase 1 covers the read-only actions. Writes, record locks and column
show/hide/order changes come in phase 2 and answer with a warning until then.

This file is derived from the PostgreSQL/MySQL Ajax Table Editor,
Copyright (c) 2008 Chris Kitchen <info@mysqlajaxtableeditor.com>, modified for
rda_pg_config by Zaihua Ji, and is distributed under the GNU Lesser General
Public License v3 (see LICENSE-LGPL in this repository).
"""

import datetime
import decimal
import json
import math
import re
import secrets

from .db import valid_ident
from .lang import LANG

SEARCH_OPTS = {
   '=': LANG['optEq'], 'like': LANG['optLike'], 'not like': LANG['optNotLike'],
   '<>': LANG['optNotEq'], '>': LANG['optGreat'], '<': LANG['optLess'],
   '>=': LANG['optGreatEq'], '<=': LANG['optLessEq'], 'between': LANG['optBetween'],
}

# actions that change data or column preferences; ported in phase 2
PHASE2_ACTIONS = {
   'edit_row', 'update_row', 'add_row', 'insert_row', 'copy_row', 'delete_row',
   'edit_mult_rows', 'update_mult_rows', 'copy_mult_rows', 'delete_mult_rows',
   'show_column', 'hide_column', 'show_hide_columns', 'order_columns_screen',
   'update_column_order', 'reset_column_order', 'user_icon_clicked', 'user_button_clicked',
}


def has(perms, flag):
   """PHP stristr($perms, $flag): case-insensitive flag test."""
   return bool(perms) and flag.lower() in perms.lower()


def php_str(val):
   """Render a database value the way PHP's pg_fetch_assoc returns it (as text)."""
   if val is None:
      return ''
   if isinstance(val, bool):
      return 't' if val else 'f'
   if isinstance(val, datetime.datetime):
      return val.isoformat(sep=' ')
   if isinstance(val, (datetime.date, datetime.time)):
      return val.isoformat()
   if isinstance(val, decimal.Decimal):
      return str(val)
   if isinstance(val, (list, tuple)):
      return '{' + ','.join(php_str(v) for v in val) + '}'
   return str(val)


def php_round(num):
   """PHP round(): halves away from zero."""
   return math.floor(num + 0.5) if num >= 0 else -math.floor(-num + 0.5)


def number_format(num, decimals=0):
   """PHP number_format($num[, $decimals]) with ',' thousands and '.' decimal point."""
   try:
      num = float(num or 0)
   except (TypeError, ValueError):
      num = 0.0
   return '{:,.{}f}'.format(num, decimals)


def to_number(val):
   """PHP numeric conversion of a string ('' or junk -> 0)."""
   try:
      return float(val)
   except (TypeError, ValueError):
      m = re.match(r'^\s*[-+]?\d*\.?\d+', str(val or ''))
      return float(m.group(0)) if m else 0.0


def format_data_size(val, precision=2):
   """AjaxTableEditor::formatDataSize: 1000-based units with a B..PB suffix."""
   units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
   val = to_number(val)
   idx = 0
   while val > 1000 and idx < 5:
      idx += 1
      val /= 1000.
   return '{:.{}f}{}'.format(val, int(precision), units[idx])


def format_size(num_bytes):
   """AjaxTableEditor::formatSize: 1024-based units for the summary screen."""
   if num_bytes is None or num_bytes == '':
      return 'N/A'
   num_bytes = float(num_bytes)
   for limit, unit in ((1125899906842624, 'PB'), (1099511627776, 'TB'), (1073741824, 'GB'), (1048576, 'MB')):
      if num_bytes >= limit:
         return number_format(num_bytes / limit, 2) + ' ' + unit
   return number_format(num_bytes, 0) + ' B'


def pg_double_quotes(name):
   """AjaxTableEditor::pgDoubleQuotes (no-sign form): quote only names that hold a double quote."""
   name = (name or '').strip()
   if name and '"' in name and not re.match(r'^[a-z_][a-z0-9_]*$', name):
      name = '"' + name + '"'
   return name


def sql_lit(text):
   """Escape % in a config-supplied SQL fragment, since the statement is run with bound values."""
   return (text or '').replace('%', '%%')


def js_str(text):
   """Quote text for a single-quoted JavaScript string literal."""
   return (str(text).replace('\\', '\\\\').replace("'", "\\'")
           .replace('\n', '\\n').replace('\r', '\\r').replace('</', '<\\/'))


def html_esc(text):
   """PHP htmlspecialchars($text, ENT_QUOTES)."""
   return (str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
           .replace('"', '&quot;').replace("'", '&#039;'))


def strip_tags(text):
   return re.sub(r'<[^>]*>', '', text or '')


def unquote_value(val):
   """Drop one pair of surrounding quotes a user typed around a search value."""
   if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
      return val[1:-1]
   return val


class EditorError(Exception):
   """A condition the PHP reported through errorFun (it died with a message)."""


class TableEditor:
   """One table page's editor state for a single request."""

   def __init__(self, table_name, table_title, primary_col, permissions, columns,
                session, db, sc_name='dssdb', page_url='', cookies=None):
      self.table_name = valid_ident(table_name)
      self.table_title = table_title
      self.primary_col = valid_ident(primary_col)
      self.permissions = permissions
      self.columns = dict(columns)
      self.session = session          # dict-like (Flask session)
      self.db = db
      self.sc_name = sc_name
      self.page_url = page_url
      self.cookies = cookies or {}
      self.set_cookies = {}           # cookies the response must set
      self.ret = []
      self.warnings = []
      self.information = []
      self.user_actions = {}
      self.user_buttons = {}
      self.user_icons = {}
      self.user_columns = []
      self.has_description = any(info.get('description') for info in self.columns.values())
      self.set_defaults()

   # ---- configuration -------------------------------------------------------

   def sget(self, name, default=None):
      return self.session.get(self.var_prefix + name, default)

   def sset(self, name, value):
      self.session[self.var_prefix + name] = value

   def set_defaults(self):
      self.sc_and_table = self.table_name if not self.sc_name else self.sc_name + '.' + self.table_name
      self.var_prefix = self.primary_col + '-' + self.table_name
      self.start = 0
      self.display_num = int(self.sget('displayNum', 20))
      self.asc_or_desc = 'asc'
      self.order_by_column = self.primary_col
      self.search_string = ''
      self.add_row_title = LANG['ttlAddRow']
      self.edit_row_title = LANG['ttlEditRow']
      self.edit_mult_title = LANG['ttlEditMult']
      self.view_row_title = LANG['ttlViewRow']
      self.table_info = 'cellpadding="1" width="900" class="mateTable"'
      self.def_num_adv_searches = 1
      self.num_adv_searches = int(self.sget('numAdvSearches', self.def_num_adv_searches))
      self.search_type = self.sget('searchType', 'advanced')
      self.match_all = self.sget('matchAll', True)
      self.adv_searches = self.sget('advSearches', [])
      self.odd_row_color = '#FFFFF5'
      self.even_row_color = '#e1eaff'
      self.display_num_inc = 5
      self.max_disp_num = 200
      self.record_info = True
      self.replace_with_id = '#primaryColValue#'
      self.highlight_hash = 'background-color: #FFF547'
      self.use_highlight = True
      self.view_table_info = 'class="mateTable"'
      self.icon_col_position = 'last'
      self.icon_title = ''
      self.remove_icons = ''
      self.page_percent = 20
      self.page_range = 10
      self.page_begin = 5
      self.page_end = 5
      self.show_all = 200
      self.query_line_break = "\n"
      self.extra_order_by_info = ''
      self.extra_row_info = ''
      self.sql_filters = ''
      self.refresh_interval = 0
      self.require_dsid = False
      self.lock_info = self.sget('lockInfo')
      self.view_html_fun = None
      self.disable_mult_cb_fun = None
      self.select_clause = self.join_clause = self.where_clause = ''
      self.where_vals = []
      self.num_results = 0

   CONFIG_NAMES = {
      'tableInfo': 'table_info', 'orderByColumn': 'order_by_column', 'addRowTitle': 'add_row_title',
      'editRowTitle': 'edit_row_title', 'viewRowTitle': 'view_row_title',
      'editMultTitle': 'edit_mult_title', 'sqlFilters': 'sql_filters',
      'refreshInterval': 'refresh_interval', 'iconTitle': 'icon_title',
      'extraOrderByInfo': 'extra_order_by_info', 'displayNum': 'display_num',
   }

   def set_config(self, var, val):
      """AjaxTableEditor::setConfig: a value already kept in the session wins."""
      if self.var_prefix + var in self.session:
         return
      setattr(self, self.CONFIG_NAMES.get(var, var), val)

   def set_lock_info(self, host_field, time_field):
      """Record which columns hold the record lock (locking itself is phase 2)."""
      self.lock_info_fields = (valid_ident(host_field), valid_ident(time_field))

   # ---- request entry -------------------------------------------------------

   def main(self, action, info=''):
      self.action = action
      self.info = info
      self.handle_flow()
      if self.information:
         self.ret.append({'layer_id': 'information', 'where': 'innerHTML',
                          'value': '<br /><br />'.join(self.information)})
      if self.warnings:
         self.ret.append({'where': 'javascript',
                          'value': "alert('" + '\\n'.join(js_str(w) for w in self.warnings) + "');"})
      return self.ret

   def handle_flow(self):
      action, info = self.action, self.info
      if action == 'update_html':
         self.update_html(info)
      elif action == 'cancel_edit_row':
         self.update_html()
      elif action == 'view_row':
         self.view_row()
      elif action == 'handle_search':
         self.sset('searchType', 'quick')
         self.search_type = 'quick'
         self.sset('ss', str(info or ''))
         self.sset('start', 0)
         self.update_html()
      elif action == 'page_num_changed':
         self.sset('start', max(0, int(to_number(info))))
         self.update_html()
      elif action == 'display_num_changed':
         num = int(to_number(info))
         self.display_num = num if 0 < num <= self.max_disp_num else 20
         self.sset('displayNum', self.display_num)
         self.sset('start', 0)
         self.update_html()
         self.ret.append({'where': 'javascript', 'value': 'resetScrollTop();'})
      elif action == 'order_by_changed':
         col, aod = (list(info) + ['', ''])[:2] if isinstance(info, (list, tuple)) else ('', '')
         if col in self.columns:
            self.sset('obc', col)
            self.sset('aod', 'desc' if aod == 'desc' else 'asc')
         self.display_table()
      elif action == 'show_advanced_search':
         self.sset('numAdvSearches', self.def_num_adv_searches)
         self.num_adv_searches = self.def_num_adv_searches
         self.sset('ss', '')
         self.search_string = ''
         self.sset('searchType', 'advanced')
         self.search_type = 'advanced'
         self.update_html()
      elif action == 'show_quick_search':
         self.sset('advSearches', [])
         self.adv_searches = []
         self.sset('searchType', 'quick')
         self.search_type = 'quick'
         self.update_html()
      elif action == 'advanced_search':
         self.sset('searchType', 'advanced')
         self.search_type = 'advanced'
         self.advanced_search()
         self.update_html()
      elif action == 'match_all':
         self.sset('matchAll', True)
      elif action == 'match_any':
         self.sset('matchAll', False)
      elif action == 'clear_adv_search':
         self.sset('matchAll', True)
         self.match_all = True
         self.sset('numAdvSearches', self.def_num_adv_searches)
         self.num_adv_searches = self.def_num_adv_searches
         self.sset('advSearches', [])
         self.adv_searches = []
         self.update_html()
      elif action == 'add_adv_search':
         self.num_adv_searches += 1
         self.sset('numAdvSearches', self.num_adv_searches)
         self.update_html()
      elif action == 'show_summary':
         self.show_summary()
      elif action == 'release_lock':
         pass     # no record is ever locked until editing is ported (phase 2)
      elif action in PHASE2_ACTIONS:
         self.warnings.append("'{}' is not available yet in gdexms (read-only phase)".format(action))
      elif action in self.user_actions:
         self.user_actions[action](info)
      else:
         self.warnings.append(LANG['errNoAction'] % action)

   def advanced_search(self):
      self.sset('start', 0)
      searches = []
      items = info_items(self.info)
      for item in items:
         if isinstance(item, dict):
            searches.append({'cols': str(item.get('cols', '')), 'opts': str(item.get('opts', '')),
                             'strs': str(item.get('strs', ''))})
      self.adv_searches = searches
      self.sset('advSearches', searches)

   # ---- table screen --------------------------------------------------------

   def update_html(self, param=''):
      self.display_table(param)
      self.display_bottom_info()
      self.ret.append({'layer_id': 'recordLayer', 'where': 'innerHTML', 'value': ''})
      self.ret.append({'where': 'javascript', 'value': 'hideRecordPane();'})
      self.ret.append({'layer_id': 'titleLayer', 'where': 'innerHTML', 'value': self.table_title})
      if param and isinstance(param, str):
         self.ret.append({'where': 'javascript', 'value': "alert('" + js_str(param) + "');"})
      self.ret.append({'where': 'javascript', 'value': "set_view_interval('update_html', '{}', {});".format(
         self.var_prefix, int(self.refresh_interval or 0))})

   def display_table(self, param=''):
      if self.require_dsid:
         self.ret.append({'layer_id': 'tableLayer', 'where': 'innerHTML',
                          'value': '<b>Please enter a Dataset ID to view records.</b>'})
         return
      self.unset_hidden_columns()
      self.set_column_order()
      self.set_paging_vars()
      self.format_join_clause()
      self.format_select_clause()
      self.format_where_clause()
      self.set_num_results()
      self.display_table_html(param)

   def set_paging_vars(self):
      self.start = max(0, int(to_number(self.sget('start', self.start))))
      obc = self.sget('obc')
      if obc in self.columns:
         self.order_by_column = obc
      if self.sget('aod') is not None:
         self.asc_or_desc = self.sget('aod')
      if self.sget('ss') is not None:
         self.search_string = self.sget('ss')

   def asc_desc(self):
      return 'desc' if self.asc_or_desc == 'desc' else 'asc'

   def order_by(self):
      col = self.order_by_column if self.order_by_column in self.columns else self.primary_col
      extra = ', ' + self.extra_order_by_info if self.extra_order_by_info else ''
      return ' order by ' + pg_double_quotes(col) + ' ' + self.asc_desc() + ' ' + sql_lit(extra)

   def format_select_clause(self):
      sets = []
      for col, info in self.columns.items():
         if isinstance(info.get('join'), dict):
            sets.append(sql_lit(info['join']['display_mask']) + ' as ' + pg_double_quotes(col))
         elif info.get('display_mask'):
            sets.append(sql_lit(info['display_mask']) + ' as ' + pg_double_quotes(col))
         else:
            sets.append(pg_double_quotes(self.sc_and_table + '.' + col))
      lb = self.query_line_break
      self.select_clause = 'select ' + (', ' + lb).join(sets) + lb + 'from ' + self.sc_and_table + lb

   def format_join_clause(self):
      sets = []
      joins = {}
      counter = 0
      for col, info in self.columns.items():
         join = info.get('join')
         if not isinstance(join, dict):
            continue
         join = self.columns[col]['join'] = dict(join)
         join_table = join['db'] + '.' + join['table'] if join.get('db') else join['table']
         join_type = join.get('type', 'left')
         join_column = join.get('real_column', col)
         foreign_column = join['column']
         ident = join_table + join_column + foreign_column + join_type
         save_join = ident not in joins
         if save_join:
            join.setdefault('alias', '{}_j{}'.format(join['table'], counter))
            joins[ident] = join['alias']
         else:
            join['alias'] = joins[ident]
         alias = join['alias']
         if join.get('display_mask'):
            # replace the first table reference in each comma-separated part with the alias
            join['display_mask'] = ','.join(re.sub(re.escape(join['table']), alias, part, count=1)
                                            for part in join['display_mask'].split(','))
         else:
            join['display_mask'] = alias + '.' + foreign_column
         if save_join:
            if (self.sc_and_table + '.').lower() in join_column.lower():
               join_field = join_column
            else:
               join_field = pg_double_quotes(self.sc_and_table + '.' + join_column)
            sets.append('{} join {} as {} on {} = {}'.format(
               join_type, pg_double_quotes(join_table), pg_double_quotes(alias), join_field,
               pg_double_quotes(alias + '.' + foreign_column)))
            counter += 1
      self.join_clause = self.query_line_break.join(sets) + self.query_line_break if sets else ''

   def column_expr(self, col):
      """SQL expression a search on column col compares against."""
      info = self.columns[col]
      if isinstance(info.get('join'), dict):
         return sql_lit(info['join']['display_mask'])
      if info.get('display_mask'):
         return sql_lit(info['display_mask'])
      return pg_double_quotes(self.sc_and_table + '.' + col)

   def format_where_clause(self):
      sets, vals = [], []
      lb = self.query_line_break
      if self.search_string and self.search_type == 'quick':
         needle = '%' + str(self.search_string).strip() + '%'
         for col, info in self.columns.items():
            if has(info.get('perms'), 'Q'):
               sets.append(self.column_expr(col) + ' like %s')
               vals.append(needle)
      elif self.adv_searches and self.search_type == 'advanced':
         for search in self.adv_searches:
            col, opt = search.get('cols'), search.get('opts')
            if not col or col not in self.columns or not has(self.columns[col].get('perms'), 'S'):
               continue
            if opt not in SEARCH_OPTS:
               continue     # the PHP called handleHacking() (exit) on an unknown operator
            strs = str(search.get('strs', '')).strip()
            expr = self.column_expr(col)
            if opt in ('like', 'not like'):
               sets.append(expr + ' ' + opt + ' %s')
               vals.append('%' + strs + '%')
            elif opt == 'between':
               m = re.match(r'^\s*(.+)\s+and\s+(.+)\s*$', strs, re.I)
               if m:
                  sets.append(expr + ' between %s and %s')
                  vals += [unquote_value(m.group(1).strip()), unquote_value(m.group(2).strip())]
               else:
                  self.warnings.append("Between needs two values: 'value1 and value2'")
            else:
               sets.append(expr + ' ' + opt + ' %s')
               vals.append(unquote_value(strs))
      glue = 'and' if self.search_type == 'advanced' and self.match_all else 'or'
      where = '(' + (' ' + glue + lb).join(sets) + ')' if sets else ''
      self.where_clause = ' where ' + where + lb if where else ''
      if self.sql_filters:
         if not self.where_clause:
            self.where_clause = 'where ' + sql_lit(self.sql_filters) + lb
         else:
            self.where_clause += ' and ' + sql_lit(self.sql_filters) + lb
      self.where_vals = vals

   def set_num_results(self):
      sqlstr = 'select count(*) as num_results from ' + self.sc_and_table + ' ' + self.join_clause + ' ' + self.where_clause
      row = self.db.query_one(sqlstr, self.where_vals)
      self.num_results = int(row['num_results']) if row else 0

   def fetch_rows(self, limit=True):
      sqlstr = self.select_clause + ' ' + self.join_clause + ' ' + self.where_clause + self.order_by()
      vals = list(self.where_vals)
      if limit:
         sqlstr += ' limit %s offset %s'
         vals += [self.display_num, self.start]
      return [{k: php_str(v) for k, v in row.items()} for row in self.db.query(sqlstr, vals)]

   def display_table_html(self, param=''):
      rows = self.fetch_rows()
      perms = self.permissions
      out = []
      if rows:
         out.append('<div><form id="{}_table_form" style="margin: 0px;"><table {}>\n         <tr class="header">'.format(
            self.var_prefix, self.table_info))
         if has(perms, 'M'):
            out.append('<td id="select_all_cb_cell" class="first"><input type="checkbox" id="select_all_cb" '
                       'onclick="selectAllCbs(this,\'{}\');" /></td>'.format(self.var_prefix))
         icon_head = '<td>' + self.icon_title + '</td>' if self.icon_title else '<td>&nbsp;</td>'
         if has(perms, 'I') and self.icon_col_position == 'first':
            out.append(icon_head)
         for col, info in self.columns.items():
            if not has(info.get('perms'), 'T'):
               continue
            head_info = info.get('col_header_info', '')
            tip = '<span>' + info['description'] + '</span>' if info.get('description') else ''
            if self.order_by_column == col:
               opp, arrow = ('desc', '&uarr;') if self.asc_or_desc == 'asc' else ('asc', '&darr;')
               out.append('<td class="other" {} ><a href="javascript: toAjaxTableEditor(\'order_by_changed\', '
                          'new Array(\'{}\',\'{}\'));" class="mytip">{}{}</a> {}</td>'.format(
                             head_info, col, opp, info['display_text'], tip, arrow))
            else:
               out.append('<td class="other" {} ><a href="javascript: toAjaxTableEditor(\'order_by_changed\', '
                          'new Array(\'{}\',\'asc\'));" class="mytip">{}{}</a></td>'.format(
                             head_info, col, info['display_text'], tip))
         for column in self.user_columns:
            out.append('<td>' + column['title'] + '</td>' if column.get('title') else '<td>&nbsp;</td>')
         if has(perms, 'I') and self.icon_col_position == 'last':
            out.append(icon_head)
         out.append('</tr>')
         bg = self.even_row_color
         for num, row in enumerate(rows, 1):
            bg = self.even_row_color if bg == self.odd_row_color else self.odd_row_color
            row_sets = {'class': 'ajaxRow', 'bgcolor': bg}
            cb = ''
            pkey = row.get(self.primary_col, '')
            if has(perms, 'M'):
               if self.disable_mult_cb_fun and self.disable_mult_cb_fun(row):
                  cb = '<td><input class="rowCheckBox" type="checkbox" id="cb_{}" value="{}" disabled="disabled" /></td>'.format(num, pkey)
               else:
                  row_sets['onclick'] = "cellClicked('{}','{}');".format(num, self.var_prefix)
                  row_sets['style'] = 'cursor: pointer;'
                  cb = ('<td><input class="rowCheckBox" type="checkbox" id="cb_{}" onclick="checkBoxClicked(this)" '
                        'value="{}" /></td>').format(num, pkey)
            extra = (self.extra_row_info.replace(self.replace_with_id, pkey).replace('#rowNum#', str(num))
                     if self.extra_row_info else '')
            out.append('<tr id="row_{}" {} {}>{}'.format(
               num, ' '.join('{}="{}"'.format(k, v) for k, v in row_sets.items()), extra, cb))
            if has(perms, 'I') and self.icon_col_position == 'first':
               out.append(self.format_icons(pkey, row))
            for col, info in self.columns.items():
               if has(info.get('perms'), 'T'):
                  out.append(self.table_cell(col, info, row))
            for column in self.user_columns:
               if column.get('call_back_fun'):
                  out.append(column['call_back_fun'](row))
            if has(perms, 'I') and self.icon_col_position == 'last':
               out.append(self.format_icons(pkey, row))
            out.append('</tr>')
         out.append('</table></form></div>')
         html = ''.join(out)
      else:
         html = '<b>' + LANG['ttlNoRecord'] + '</b>'
      self.ret.append({'layer_id': 'tableLayer', 'where': 'innerHTML', 'value': html})
      if self.record_info:
         if self.num_results > 0:
            end = min(self.display_num + self.start, self.num_results)
            rec = '<div>' + LANG['ttlDispRecs'] % (self.start + 1, end, number_format(self.num_results)) + '</div>'
         else:
            rec = '<div>' + LANG['ttlDispNoRecs'] + '</div>'
         self.ret.append({'layer_id': 'recordLayer', 'where': 'innerHTML', 'value': rec})
      if param and isinstance(param, dict):
         self.ret.append({'where': 'javascript', 'value': "setCheckedCbs(new Array('{}'),'{}');".format(
            "','".join(js_str(v) for v in param.values()), self.var_prefix)})

   def table_cell(self, col, info, row):
      value = row.get(col, '')
      cell = info.get('table_cell_info', '')
      if info.get('table_fun'):
         value = info['table_fun'](col, value, row)
      elif 'data_precision' in info:
         value = format_data_size(value, 1)     # the PHP passes isset(...) == true, i.e. 1
         cell = (cell + ' ' if cell else '') + 'style="text-align: right; font-family: Fixed"'
      elif str(info.get('maxlen', '')) == '1':
         cell = (cell + ' ' if cell else '') + 'style="text-align: center; font-family: Fixed"'
      elif info.get('valtype') == 'integer' or col == 'dsid':
         cell = (cell + ' ' if cell else '') + 'style="text-align: right; font-family: Fixed"'
      value = value if value is not None and str(value).strip() else '&nbsp;'
      value = str(value)
      if 'sub_str' in info and len(value) > int(info['sub_str']):
         value = value[:int(info['sub_str'])] + '...'
      if self.search_string and self.use_highlight and value != '&nbsp;':
         value = self.highlight(self.search_string, value)
      return '<td ' + cell + '>' + value + '</td>'

   def highlight(self, needle, haystack):
      if not needle:
         return haystack
      pattern = '(?!<.*?)(' + re.escape(needle) + ')(?![^<>]*?>)'
      return re.sub(pattern, '<span style="' + self.highlight_hash + '">\\1</span>', haystack, flags=re.I)

   def format_icons(self, pkey, row):
      perms, html, num = self.permissions, '', 0
      for flag, cls, title, link in (
            ('V', 'info', LANG['ttlInfo'], "javascript: toAjaxTableEditor('view_row','{}');"),
            ('E', 'edit', LANG['ttlEdit'], "javascript: toAjaxTableEditor('edit_row','{}');"),
            ('C', 'copy', LANG['ttlCopy'], "javascript: toAjaxTableEditor('copy_row','{}');"),
            ('D', 'delete', LANG['ttlDelete'], "javascript: confirmDeleteRow('{}')")):
         if has(perms, flag) and not has(self.remove_icons, flag):
            html += '<li class="{}"><a href="{}" title="{}"></a></li>'.format(cls, link.format(pkey), title)
            num += 1
      if num > 0:
         html = '<td nowrap="nowrap"><ul class="actions" style="width: {}px;">{}</ul></td>'.format(num * 26, html)
      return html

   # ---- page and search controls --------------------------------------------

   def display_bottom_info(self):
      if self.require_dsid:
         self.ret.append({'layer_id': 'searchButtonsLayer', 'where': 'innerHTML', 'value': ''})
         return
      perms, vp = self.permissions, self.var_prefix
      html = '<div style="padding-top: 5px; padding-bottom: 5px;">' + LANG['lblPage'] + ' ' + self.page_drop_down() + '&nbsp;'
      if has(perms, 'U'):
         html += LANG['lblDisplay'] + ' ' + self.disp_num_drop_down() + '&nbsp;'
      if has(perms, 'A'):
         html += '<button onclick="toAjaxTableEditor(\'add_row\',\'\');">' + LANG['btnAdd'] + '</button>&nbsp;'
      for flag, action, label in (('E', 'edit_row', 'btnEdit'), ('V', 'view_row', 'btnView'),
                                  ('C', 'copy_row', 'btnCopy'), ('D', 'delete_row', 'btnDelete')):
         if has(perms, flag) and not has(perms, 'I'):
            html += '<button onclick="editCopyViewDelete(\'{}\',\'{}\');">{}</button>&nbsp;'.format(vp, action, LANG[label])
      if has(perms, 'X'):
         html += '<button onclick="window.location=\'' + self.page_url + '?export=1\'">' + LANG['btnExport'] + '</button>&nbsp;'
      if has(perms, 'H'):
         html += '<button onclick="toAjaxTableEditor(\'show_hide_columns\',\'\');">' + LANG['btnShowHide'] + '</button>&nbsp;'
      if has(perms, 'O'):
         html += '<button onclick="toAjaxTableEditor(\'order_columns_screen\',\'\');">' + LANG['btnOrderCols'] + '</button>&nbsp;'
      if has(perms, 'S') and self.search_type == 'quick':
         html += '<button onclick="toAjaxTableEditor(\'show_advanced_search\',\'\');">' + LANG['btnSearch'] + '</button>&nbsp;'
      elif has(perms, 'Q') and self.search_type == 'advanced':
         html += '<button onclick="toAjaxTableEditor(\'show_quick_search\',\'\');">' + LANG['btnQSearch'] + '</button>&nbsp;'
      for key, info in self.user_buttons.items():
         if 'button_html' in info:
            html += info['button_html'] + '&nbsp;'
         elif 'button_info' in info:
            html += '<button ' + info['button_info'] + '>' + info['label'] + '</button>&nbsp;'
      html += '<button onclick="toAjaxTableEditor(\'show_summary\',\'\');">Summary</button>&nbsp;'
      html += '</div>'
      if has(perms, 'Q') and self.search_type == 'quick':
         html += (LANG['lblSearch'] + ': <input type="text" id="searchString" value="' + html_esc(self.search_string)
                  + '" size="25" onKeyPress="if(enterPressed(event)){handleSearch(); return false;}" />&nbsp;'
                  '<button onclick="handleSearch();">' + LANG['lblSearch'] + '</button>&nbsp;'
                  '<button onclick="clearSearch();">' + LANG['btnCSearch'] + '</button>')
      elif has(perms, 'S') and self.search_type == 'advanced':
         html += self.advanced_search_html()
      self.ret.append({'layer_id': 'searchButtonsLayer', 'where': 'innerHTML', 'value': html})

   def disp_num_drop_down(self):
      value = self.display_num_inc
      html = '<select id="display_number" onchange="toAjaxTableEditor(\'display_num_changed\',this.value);">'
      while value < self.num_results and value < self.max_disp_num:
         value += self.display_num_inc
         sel = ' selected="selected"' if value == self.display_num else ''
         html += '<option value="{0}"{1}>{0}</option>'.format(value, sel)
      return html + '</select>'

   def page_drop_down(self):
      cur_page = php_round(self.start / self.display_num)
      num_pages = math.ceil(self.num_results / self.display_num)
      if num_pages == 0:
         pages = [0]
      elif num_pages < self.show_all:
         pages = list(range(1, num_pages + 1))
      else:
         pages = list(range(1, self.page_begin + 1)) + list(range(num_pages - self.page_end, num_pages + 1))
         i, x, met = self.page_begin, num_pages - self.page_end, False
         while i <= x:
            if cur_page - self.page_range <= i <= cur_page + self.page_range:
               i += 1
               met = True
            else:
               i += num_pages // self.page_percent
               if i > cur_page - self.page_range and not met:
                  i = cur_page - self.page_range
            if 0 < i <= x:
               pages.append(i)
         pages = sorted(set(pages))
      html = '<select id="page_number" onchange="toAjaxTableEditor(\'page_num_changed\',this.value);">'
      for i in pages:
         value = max(0, (i - 1) * self.display_num)
         if i - 1 == cur_page:
            html += '<option value="{}" selected="selected" style="font-weight: bold">{}</option>'.format(value, i)
         else:
            html += '<option value="{}">{}</option>'.format(value, i)
      return html + '</select>'

   def advanced_search_html(self):
      html = '<div id="searchLayer" >'
      for i in range(self.num_adv_searches):
         search = self.adv_searches[i] if i < len(self.adv_searches) else {}
         html += '<p><select id="as_cols_{}"><option value="">{}</option>'.format(i, LANG['lblSelect'])
         for col, info in self.columns.items():
            if has(info.get('perms'), 'S'):
               text = info['display_text'].replace('<br>', ' ')
               sel = ' selected' if search.get('cols') == col else ''
               html += '<option value="{}"{}>{}</option>'.format(col, sel, text)
         html += '</select>&nbsp;<select id="as_opts_{}">'.format(i)
         for sign, text in SEARCH_OPTS.items():
            sel = ' selected' if search.get('opts') == sign else ''
            html += '<option value="{}"{}>{}</option>'.format(sign, sel, text)
         html += '</select>&nbsp;'
         html += ('<input type="text" id="as_strs_{}" size="28" value="{}" onKeyPress="if(enterPressed(event))'
                  '{{handleAdvancedSearch(\'{}\'); return false;}}" /></p>').format(
                     i, html_esc(search.get('strs', '')), self.num_adv_searches)
      all_ck = 'checked="checked"' if self.match_all else ''
      any_ck = '' if self.match_all else 'checked="checked"'
      html += '<p align="center">'
      if self.num_adv_searches > 1:
         html += ('<p>' + LANG['lblMatch'] + '\n            <input type="radio" name="match" value="all" id="match_all" '
                  + all_ck + ' onclick="toAjaxTableEditor(\'match_all\',\'\');"> <label for="match_all">'
                  + LANG['lblAllCrit'] + '</label>\n            <input type="radio" name="match" value="any" id="match_any" '
                  + any_ck + ' onclick="toAjaxTableEditor(\'match_any\',\'\');"> <label for="match_any">'
                  + LANG['lblAnyCrit'] + '</label></p>')
      html += ('<button onclick="handleAdvancedSearch(\'{}\');">{}</button>&nbsp;<button onclick="toAjaxTableEditor('
               '\'clear_adv_search\',\'\');">{}</button>&nbsp;<button onclick="toAjaxTableEditor(\'add_adv_search\','
               '\'\');">{}</button></p></div>').format(self.num_adv_searches, LANG['lblSearch'], LANG['btnCSearch'],
                                                       LANG['btnAddCrit'])
      return html

   # ---- record view and summary ---------------------------------------------

   def view_row(self):
      html = ''
      row_id = str(self.info or '').strip()
      if has(self.permissions, 'V'):
         self.format_join_clause()
         self.format_select_clause()
         sqlstr = (self.select_clause + ' ' + self.join_clause + ' where ' + self.sc_and_table + '.'
                   + self.primary_col + ' = %s')
         row = self.db.query_one(sqlstr, [row_id])
         if not row:
            self.ret.append({'where': 'javascript', 'value': "toAjaxTableEditor('update_html','{}');".format(
               js_str('View screen was closed for the viewing record is gone!'))})
            return
         row = {k: php_str(v) for k, v in row.items()}
         html += '<table ' + self.view_table_info + '>'
         bg = self.even_row_color
         for col, info in self.columns.items():
            if not has(info.get('perms'), 'V'):
               continue
            value = row.get(col, '')
            if info.get('view_fun'):
               value = info['view_fun'](col, value, row)
            elif 'select_array' in info:
               if value and value in info['select_array']:
                  value = value + ' - ' + info['select_array'][value]
            elif 'data_precision' in info:
               value = format_data_size(value, 1)
            value = str(value) if value is not None and str(value).strip() else '&nbsp;'
            if value != '&nbsp;' and value.count('\n') >= 20:
               value = ('<div style="overflow-y: auto; max-height: 400px; white-space: pre-wrap;">'
                        + html_esc(value) + '</div>')
            bg = self.even_row_color if bg == self.odd_row_color else self.odd_row_color
            text = info['display_text'].replace('<br>', ' ')
            html += ('<tr bgcolor="{0}"><td id="{1}_label_cell" class="labelCell">{2}:</td>'
                     '<td id="{1}_value_cell" class="valueCell">{3}</td>').format(bg, col, text, value)
            if self.has_description:
               html += '<td id="{}_descript_cell" class="descriptCell">{}</td>'.format(
                  col, info.get('description') or '&nbsp;')
            html += '</tr>'
         if self.view_html_fun:
            html += self.view_html_fun(row)
         html += '</tr></table><div id="viewRowButtons">'
         if has(self.permissions, 'E'):
            html += ('<button class="ajaxButton" onclick="toAjaxTableEditor(\'edit_row\',\'{}\');">{}</button>'
                     .format(js_str(row_id), LANG['btnEdit']))
         html += ('<button class="ajaxButton" onclick="toAjaxTableEditor(\'update_html\',\'\');">'
                  + LANG['btnBack'] + '</button></div>')
      self.ret.append({'layer_id': 'titleLayer', 'where': 'innerHTML', 'value': self.view_row_title})
      self.ret.append({'layer_id': 'recordLayer', 'where': 'innerHTML', 'value': html})
      self.ret.append({'where': 'javascript', 'value': 'showRecordPane();'})
      self.ret.append({'where': 'javascript', 'value': "set_view_interval('view_row', '{}', {});".format(
         js_str(row_id), int(self.refresh_interval or 0))})

   def show_summary(self):
      self.unset_hidden_columns()
      self.set_column_order()
      self.set_paging_vars()
      self.format_join_clause()
      self.format_select_clause()
      self.format_where_clause()
      tail = ' from ' + self.sc_and_table + ' ' + self.join_clause + ' ' + self.where_clause
      row = self.db.query_one('select count(*) as num_results' + tail, self.where_vals)
      count = row['num_results'] if row else 0
      size_cols = [c for c, i in self.columns.items() if re.search(r'size|bytes', c, re.I) or 'data_precision' in i]
      count_cols = [c for c in self.columns if re.search(r'count|num_|cnt', c, re.I)]
      label = (lambda c: strip_tags(self.columns[c]['display_text']) if 'display_text' in self.columns[c]
               else c.replace('_', ' ').capitalize())
      td = '<tr><td style="padding:4px 12px 4px 4px;"><b>{}</b></td><td>{}</td></tr>'
      html = '<div style="padding: 15px;">'
      html += '<h3 style="margin-top:0;">' + html_esc(self.table_name) + ' Summary</h3>'
      html += '<table class="mateTable" style="min-width:300px;">'
      html += td.format('Total Records:', number_format(count))
      for col in count_cols:
         rec = self.db.query_one('select sum(' + pg_double_quotes(self.sc_and_table + '.' + col)
                                 + ') as total_count' + tail, self.where_vals)
         if rec:
            html += td.format('Total ' + html_esc(label(col)) + ':', number_format(rec['total_count']))
      for col in size_cols:
         rec = self.db.query_one('select sum(' + pg_double_quotes(self.sc_and_table + '.' + col)
                                 + ') as total_size' + tail, self.where_vals)
         if rec:
            html += td.format('Total ' + html_esc(label(col)) + ':', format_size(rec['total_size']))
      html += '</table>'
      html += '<br><button onclick="toAjaxTableEditor(\'update_html\',\'\');">Close</button>'
      html += '</div>'
      self.ret.append({'layer_id': 'recordLayer', 'where': 'innerHTML', 'value': html})
      self.ret.append({'where': 'javascript', 'value': 'showRecordPane();'})

   # ---- CSV export ----------------------------------------------------------

   def export_info(self):
      self.unset_hidden_columns()
      self.set_column_order()
      self.set_paging_vars()
      self.format_join_clause()
      self.format_select_clause()
      self.format_where_clause()
      rows = self.fetch_rows(limit=False)
      if not rows:
         return ''
      cols = [(c, i) for c, i in self.columns.items() if has(i.get('perms'), 'X')]
      lines = [','.join('"' + i['display_text'] + '"' for c, i in cols)]
      for row in rows:
         vals = []
         for col, info in cols:
            value = row.get(col, '')
            if info.get('csv_export_fun'):
               value = info['csv_export_fun'](col, value, row)
            vals.append('"' + str(value).replace('\r', '').replace('\n', '').replace('"', '""') + '"')
         lines.append(','.join(vals))
      return '\r\n'.join(lines) + '\r\n'

   # ---- per-user column preferences (mate_columns), read side ---------------

   def mate_user_id(self):
      """The mate_user_id cookie, created (and set on the response) when missing."""
      uid = self.cookies.get('mate_user_id')
      if not uid:
         uid = self.set_cookies.get('mate_user_id') or secrets.token_hex(16)
         self.set_cookies['mate_user_id'] = uid
      return uid

   def unset_hidden_columns(self):
      if not has(self.permissions, 'H'):
         return
      uid = self.mate_user_id()
      prefs = {r['mate_column']: r['hidden'] for r in self.db.query(
         'select mate_column, hidden from mate_columns where mate_user_id = %s and mate_var_prefix = %s',
         [uid, self.var_prefix])}
      for col, info in list(self.columns.items()):
         if has(info.get('perms'), 'H') and col != self.primary_col:
            hidden = prefs[col] == 'Yes' if col in prefs else bool(info.get('hidden'))
            if hidden:
               del self.columns[col]

   def set_column_order(self):
      if not has(self.permissions, 'O'):
         return
      uid = self.mate_user_id()
      rows = self.db.query("select mate_column from mate_columns where mate_user_id = %s and mate_var_prefix = %s"
                           " and hidden = 'No' and order_num > 0 order by order_num asc", [uid, self.var_prefix])
      ordered = {}
      for r in rows:
         col = r['mate_column']
         if col in self.columns and has(self.columns[col].get('perms'), 'O'):
            ordered[col] = self.columns.pop(col)
      ordered.update(self.columns)
      self.columns = ordered


def info_items(info):
   """The values of a JSON array or object sent as info (PHP get_object_vars order)."""
   if isinstance(info, dict):
      return list(info.values())
   if isinstance(info, list):
      return info
   return []


def decode_request(raw):
   """Decode the json form field into (action, info) the way Common::startup did."""
   data = json.loads(raw or '{}')
   if not isinstance(data, dict):
      data = {}
   info = data.get('info', '')
   if info is None or (isinstance(info, str) and not info.strip()):
      info = ''
   return str(data.get('action', '')), info
