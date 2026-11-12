"""Page base class: a Python port of rda-pg-config's inc/Common.inc.

A page module subclasses Page, builds its column config in init_editor() and
creates self.editor (a TableEditor). The helpers here are the formatting and
lookup callbacks the PHP pages shared, with all lookups using bound values.
"""

import re
import time

from .engine import TableEditor, html_esc, php_round, php_str, to_number


def php_empty(val):
   """PHP empty() for a database string: '', '0' and None are empty."""
   return val is None or val == '' or val == '0' or val == 0


class Page:
   """One table page for one request."""

   title = ''           # menu text
   select_dsid = 'select dsid, title from search.datasets order by dsid'
   select_specialist = ("select logname, concat(fstname,' ',lstname) from dssdb.dssgrp "
                        "where stat_flag = 'C' order by logname")
   text_area = {'rows': 1, 'cols': 80}
   text_large = {'rows': 5, 'cols': 80}

   def __init__(self, db, session, specialist=None, page_url='', cookies=None, action='', info=''):
      self.db = db
      self.session = session
      self.specialist = specialist
      self.page_url = page_url
      self.cookies = cookies or {}
      self.action = action
      self.info = info
      self.editor = None

   def init_editor(self):
      raise NotImplementedError

   def make_editor(self, table_name, table_title, primary_col, permissions, columns):
      self.editor = TableEditor(table_name, table_title, primary_col, permissions, columns,
                                self.session, self.db, page_url=self.page_url, cookies=self.cookies)
      return self.editor

   def pre_html(self):
      """Extra HTML a page shows above the editor layers (PHP displayHtml override)."""
      return ''

   # ---- one-row lookups -----------------------------------------------------

   def one(self, sqlstr, vals=None):
      row = self.db.query_one(sqlstr, vals)
      return {k: php_str(v) for k, v in row.items()} if row else None

   def first(self, sqlstr, vals=None):
      row = self.one(sqlstr, vals)
      return next(iter(row.values())) if row else None

   # ---- formatting callbacks (col, val, row) --------------------------------

   def html2text(self, col, val, row):
      return html_esc(val) if val else ''

   def preserve_text(self, col, val, row):
      return '<pre>' + val + '</pre>' if val else ''

   def format_data_size(self, col, val, row):
      units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
      val = to_number(val)
      idx = 0
      while val > 1000 and idx < 5:
         idx += 1
         val /= 1000.
      return '{:.2f}{}'.format(val, units[idx])

   def format_interval(self, col, val, row):
      return self.get_interval_time(val) if not php_empty(val) else val

   @staticmethod
   def get_interval_time(val):
      val = int(to_number(val))
      out = ''
      sec = val % 60
      val //= 60
      if val:
         mins = val % 60
         val //= 60
         if val:
            hrs = val % 24
            days = val // 24
            if days: out += '{}D'.format(days)
            if hrs: out += '{}H'.format(hrs)
         if mins: out += '{}N'.format(mins)
      if sec: out += '{}S'.format(sec)
      return out

   def format_link(self, col, val, row):
      if not val:
         return ''
      html, link = '', val
      if link.startswith('/'):
         html = 'http://rda.ucar.edu'
      else:
         m = re.match(r'^(https*://rda.ucar.edu)(.*)', link, re.I)
         if m:
            html, link = m.group(1), m.group(2)
      if html:
         end, sep = '', '?'
         m = re.match(r'^(/datasets/[a-z]\d{6}/)(.+)$', link)
         m2 = re.match(r'^/(cgi-bin/datasets/getSubset\?dsnum=)([a-z]\d{6})(.+)$', link)
         if m:
            link = m.group(1) + 'index.html#'
            end = m.group(2)
            sep = '&' if '?' in end else '?'
         elif m2:
            link = '/datasets/{1}/index.html#{0}{1}'.format(m2.group(1), m2.group(2))
            end = m2.group(3)
            sep = '&'
         if end:
            if not php_empty(row.get('gindex')) and not re.search(r'gindex=\d+', end):
               end += sep + 'gindex=' + row['gindex']
               sep = '&'
            end += sep + '_da=y'
         link = html + link + end
      return '<a target="_blank" href="' + link + '">' + val + '</a>'

   # ---- running status of daemon-driven records -----------------------------

   def display_running_status(self, col, val, row):
      m = re.match(r'^(\d+) (.+)$', val or '')
      if m and int(m.group(1)) > 0:
         out = '{}({}'.format(m.group(2), m.group(1))
         info = self.get_running_info(col, row, m.group(2))
         if 'ptcount' in info: out += '/' + str(info['ptcount'])
         if 'runhost' in info: out += '/' + info['runhost']
         out += ')'
         if 'exetime' in info: out += ' ' + info['exetime']
         return out + self.get_complete_percentage(col, row)
      if to_number(row.get('pindex')) > 0:
         return 'Wait on CHK ' + row['pindex']
      return ''

   def get_running_info(self, col, row, hostname):
      info = {}
      cnd = vals = None
      if col == 'dscheck':
         if not php_empty(row.get('cindex')):
            cnd, vals = 'cindex = %s', [row['cindex']]
      else:
         oidx = None
         if col == 'dsupdt':
            oidx = row.get('cindex')
         elif col == 'partition':
            oidx = row.get('pindex')
         elif col == 'dsrqst':
            oidx = row.get('rindex')
            if not php_empty(oidx) and hostname == 'partition':
               ptcount = self.first('select ptcount from dsrqst where rindex = %s', [oidx])
               if to_number(ptcount) > 1: info['ptcount'] = ptcount
         if not php_empty(oidx):
            cnd, vals = 'oindex = %s AND command = %s', [oidx, col]
      if cnd:
         check = self.one('select subtime, stttime, runhost from dscheck where ' + cnd, vals)
         if check:
            now = int(time.time())
            if not php_empty(check['stttime']):
               info['exetime'] = self.get_interval_time(now - int(to_number(check['stttime'])))
            elif not php_empty(check['subtime']):
               info['exetime'] = self.get_interval_time(now - int(to_number(check['subtime'])))
            if hostname == 'PBS' and check['runhost']:
               info['runhost'] = check['runhost']
      return info

   def get_complete_percentage(self, col, row):
      if col == 'dscheck' and not php_empty(row.get('cindex')):
         return self.get_dscheck_percentage(row['cindex'])
      if col == 'dsupdt' and not php_empty(row.get('cindex')):
         return self.get_dsupdt_percentage(row['cindex'])
      if col == 'partition' and not php_empty(row.get('pindex')):
         return self.get_partition_percentage(row['pindex'])
      if col == 'dsrqst' and not php_empty(row.get('rindex')):
         return self.get_dsrqst_percentage(row['rindex'])
      return ''

   @staticmethod
   def done_percent(done, total):
      percent = php_round(100 * done / total)
      if percent:
         return ', {}% done'.format(min(percent, 99))
      return ''

   def get_dscheck_percentage(self, cindex):
      check = self.one('select dcount, fcount, command, oindex, otype from dscheck where cindex = %s', [cindex])
      if check:
         fcount, dcount = to_number(check['fcount']), to_number(check['dcount'])
         if fcount > 0 and dcount:
            return self.done_percent(dcount, fcount)
         if not php_empty(check['oindex']) and check['command'] == 'dsrqst':
            if check['otype'] == 'P':
               return self.get_partition_percentage(check['oindex'])
            return self.get_dsrqst_percentage(check['oindex'])
      return ''

   def get_dsupdt_percentage(self, cindex):
      check = self.one("select dcount, fcount from dscheck where oindex = %s AND command = 'dsupdt'", [cindex])
      if check and to_number(check['fcount']) > 0 and to_number(check['dcount']):
         return self.done_percent(to_number(check['dcount']), to_number(check['fcount']))
      return ''

   def get_dsrqst_percentage(self, rindex):
      rqst = self.one('select fcount, pcount from dsrqst where rindex = %s', [rindex])
      if rqst:
         fcnt = to_number(rqst['fcount'])
         if fcnt < 1:
            fcnt = to_number(self.first('select count(*) fcnt from wfrqst where rindex = %s', [rindex]))
         if fcnt > 0:
            dcnt = to_number(rqst['pcount'])
            if dcnt < 1:
               dcnt = to_number(self.first("select count(*) dcnt from wfrqst where rindex = %s AND status = 'O'",
                                           [rindex]))
               if dcnt > 0:
                  return self.done_percent(dcnt, fcnt)
      return ''

   def get_partition_percentage(self, pindex):
      part = self.one('select fcount from ptrqst where pindex = %s', [pindex])
      if part:
         fcnt = to_number(part['fcount'])
         if fcnt < 1:
            fcnt = to_number(self.first('select count(*) fcnt from wfrqst where pindex = %s', [pindex]))
         if fcnt > 0:
            dcnt = to_number(self.first("select count(*) dcnt from wfrqst where pindex = %s AND status = 'O'",
                                        [pindex]))
            if dcnt > 0:
               return self.done_percent(dcnt, fcnt)
      return ''
