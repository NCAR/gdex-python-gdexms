/*
 * Mysql Ajax Table Editor
 *
 * Copyright (c) 2008 Chris Kitchen <info@mysqlajaxtableeditor.com>
 * All rights reserved.
 *
 * See COPYING file for license information.
 *
 * Download the latest version from
 * http://www.mysqlajaxtableeditor.com
 * 
 * ************************************************************************
 * Work File : $DSSWEB/internal/rda_pg_config/js/ajax_table_editor.js
 *             
 * Modified to work for rda_config by zji@ucar.edu, starts on 2012-01-30
 * Modified to work for rda_pg_config by zji@ucar.edu, starts on 2023-10-04
 * 
 */
var historyObject = new Array();
var historyCounter = 0;
var trackHistory = false;
var javascript = '';
var scripts = document.getElementsByTagName('script');
var script = scripts[scripts.length - 1];
var pathWithFile = script.getAttribute("src");
var jsPath = pathWithFile.indexOf('/') >= 0 ? pathWithFile.match(/^(.+)\//)[0] : '';
var loadTimeout = null;
var editTimeout = null;
var editWarnTimeout = null;
var editLocked = false;
var viewInterval = null;
var viewAction = '';

if(typeof(mateDeleteMsg) == 'undefined' || mateDeleteMsg == null)
{
   document.write('<script type="text/javascript" src="'+jsPath+'lang/lang_vars-en.js"></scr' + 'ipt>');
}

function clear_all_times() {
   
   clear_load_timeout(0);

   if(viewInterval) {
      clear_view_interval();
   }
   if(editTimeout) {
      clear_edit_timeout(0);
   }
}

function set_view_interval(action, id, interval)
{
   if(!viewInterval || action != viewAction) {
      if(interval) {
         interval *= 1000;     // convert seconds to miliseconds
      } else {
         interval = 600000;    // default to 10 minutes = 10*60*1000 miliseconds
      }
      viewAction = action;
      viewInterval = window.setInterval("refresh_view_display('"+action+"', '"+id+"')", interval);
   }
}

function refresh_view_display(action, id) {

   if(action == 'update_html') {
      id = get_checked_array(id);
   }
   toAjaxTableEditor(action, id);
}
   
function get_checked_array(varPrefix) {
   var info = new Object();
   var numRows = 0;
   var tableForm = $(varPrefix + '_table_form');

   for(var i=0; i < tableForm.elements.length; i++) {
      var cb = tableForm.elements[i];
      if(cb.checked) {
         info[numRows++] = i;
         if(i == 0) break;
      }
   }
   return (numRows > 0 ? info : '');
}

function clear_view_interval() {

   window.clearInterval(viewInterval);
   viewInterval = null;
   viewAction = '';
}

function set_edit_timeout()
{
   if(editTimeout) window.clearTimeout(editTimeout);
   if(editWarnTimeout) window.clearTimeout(editWarnTimeout);
   editLocked = true;
   // Warning popup at 50 minutes
   editWarnTimeout = window.setTimeout(function() {
      var stay = confirm("You have been in Edit mode for 50 minutes.\nClick OK to stay in edit mode for another hour, or Cancel to close the edit.");
      if(stay) {
         set_edit_timeout();
      } else {
         clear_edit_timeout(1);
      }
   }, 3000000);  // 50 minutes = 50*60*1000 ms
   // Auto-close at 60 minutes
   editTimeout = window.setTimeout("clear_edit_timeout(1)", 3600000);  // 60 minutes = 60*60*1000 ms
}

function clear_edit_timeout(timedOut)
{
   window.clearTimeout(editTimeout);
   window.clearTimeout(editWarnTimeout);
   editTimeout = null;
   editWarnTimeout = null;
   editLocked = false;
   if(timedOut) {
      if(loadTimeout == null) {
         loadTimeout = '';
      }
      toAjaxTableEditor('update_html',"Edit screen was closed after 1 hour timeout.");
   }
}

function set_load_timeout(action)
{
   if(loadTimeout == null) {
      loadTimeout = window.setTimeout("clear_load_timeout(1)", 3000);  // timeout for 3 seconds
   }
}

function clear_load_timeout(timedOut)
{
   if(loadTimeout) {
      window.clearTimeout(loadTimeout);
      loadTimeout = null;
   }
   if($('ajaxLoader') != null) {
      if(timedOut) {
         $('ajaxLoader').setStyle('display: inline;');
      } else {
         $('ajaxLoader').setStyle('display: none;');
      }
   }
   loadTimeout = null;
}

function displayInfo(info)
{
   javascript = '';
   var i = 0;
   while(info[i] != null) {
      if(info[i].where == 'innerHTML') {
         $(info[i].layer_id).innerHTML = info[i].value;
      } else if(info[i].where == 'remove') {
         $(info[i].layer_id).remove();
      } else if(info[i].where == 'append') {
         $(info[i].layer_id).insert(info[i].value);
      } else if(info[i].where == 'value') {
         $(info[i].layer_id).value = info[i].value;
      } else if(info[i].where == 'javascript') {
         eval(info[i].value);
         if(trackHistory != null && trackHistory) {
            javascript += info[i].value+"\n";
         }
      }
      i = i + 1;
      
   }
   clear_load_timeout(0);
}

function toAjaxTableEditor(action,info)
{
   if(editTimeout) {
      clear_edit_timeout(0);
   }
   if(viewInterval && action != viewAction) {
      clear_view_interval();
   }
   set_load_timeout();
   
   var data = new Object();
   data.action = action;
   data.info = info;

   var json = encodeURIComponent(Object.toJSON(data));

   new Ajax.Request(ajaxUrl,
   {
      method:'post',
      parameters: 'json='+json,
      onSuccess: 
      function(transport) {
         if(transport.responseText.isJSON()) {
            displayInfo(transport.responseText.evalJSON(true));
            if(trackHistory != null && trackHistory) {
               setTimeout("storeHistory();",100);
            }
         } else {
            var respText = transport.responseText.replace(/<br \/>/g, '\n');
            clear_all_times();
            alert(mateErrRespText+'\n\n' + respText.replace(/<br>/g, '\n')); 
         }
         // Un-comment to view json returned from server
         // alert(transport.responseText);
      },
      onFailure: function(){ alert(mateErrAjaxUrl); }
   });
}

function storeHistory()
{
   var index = historyObject.length;
   if((historyCounter + 1) < index)
   {
      index = historyCounter + 1;
   }
   historyObject[index] = new Object();
   historyObject[index].historyHtml = $('historyContainer').innerHTML;
   historyObject[index].javascript = javascript;
   
   
   // Unset all future history entries
   var minValue = index + 1;
   var maxValue = historyObject.length - 1;
   
   while(minValue <= maxValue)
   {
      if(delete historyObject[minValue])
      {
         historyObject.length--;
      }
      minValue++;
   }
   
   historyCounter = index;
   updateHistoryButtons();
}   

function backButtonPressed()
{
   historyCounter--;
   $('historyContainer').innerHTML = historyObject[historyCounter].historyHtml;
   eval(historyObject[historyCounter].javascript);
   updateHistoryButtons();
}

function forwardButtonPressed()
{
   historyCounter++;
   $('historyContainer').innerHTML = historyObject[historyCounter].historyHtml;
   eval(historyObject[historyCounter].javascript);
   updateHistoryButtons();
}

function updateHistoryButtons(disableForward)
{
   var backDisabled = '';
   var forwardDisabled = '';
   if(historyCounter == 0)
   {
      backDisabled = 'disabled="disabled"';
   }
   if((historyCounter + 1) >= historyObject.length)
   {
      forwardDisabled = 'disabled="disabled"';      
   }
   var navButtonHtml = '<button onclick="backButtonPressed();" ' + backDisabled + '>'+mateBtnBack+'</button>&nbsp;<button onclick="forwardButtonPressed();" ' + forwardDisabled + '>'+mateBtnForward+'</button>';
   $('historyButtonsLayer').innerHTML = navButtonHtml;
}

function handleSearch()
{
   var info = $('searchString').value;   
   toAjaxTableEditor('handle_search',info);
}

function clearSearch()
{
   $('searchString').value = '';   
   toAjaxTableEditor('handle_search','');
}

function confirmDeleteRow(id)
{
   if(confirm(mateDeleteMsg))
   {
      toAjaxTableEditor('delete_row',id);   
   }
}

function getMultipleSelection(elem) {
   var array = new Array();
   var sep = elem.getAttribute("separator");
   var exclusive = '!';
   var lead = '';
 
   if(!sep) sep = '';

   for(var j = 0; j < elem.length; j++) {
      if(elem.options[j].selected) {
         if(j == 0 && elem.options[0].value == exclusive) {
            lead = exclusive;
         } else {
            array.push(elem.options[j].value);
         }
      }
   }
   if(array.length > 0) {
      return lead + array.join(sep);
   } else {
      return ""; 
   }
}

function updateRow(id,varPrefix)
{
   var info = new Object();
   info['old_primary_key_value'] = id;
   var formElem = document.getElementById(varPrefix + '_edit_form');

   for(var i=0; i < formElem.elements.length; i++) {
      var elem = formElem.elements[i];
      var inputId = elem.id;
      if(elem.type.toLowerCase() == 'radio') {
         if(elem.checked) {
            info[inputId] = elem.value;
         }
      } else if(elem.type.toLowerCase() == 'select-multiple') {
         info[inputId] = getMultipleSelection(elem);
      } else {
         info[inputId] = $(inputId).value;
      }
   }
   toAjaxTableEditor('update_row',info);
}


/**
 * save the changed entries and refresh the edit page
 * @param id - the primary key id under editing
 * @param varPrefix
 */

function refreshEditPage(id,varPrefix) {

   var info = new Object();
   var formElem = document.getElementById(varPrefix + '_edit_form');

   info['old_primary_key_value'] = id;

   for(var i=0; i < formElem.elements.length; i++) {
      var elem = formElem.elements[i];
      var inputId = elem.id;
      if(elem.type.toLowerCase() == 'radio') {
         if(elem.checked) {
            info[inputId] = elem.value;
         }
      } else if(elem.type.toLowerCase() == 'select-multiple') {
         info[inputId] = getMultipleSelection(elem);
      } else {
         info[inputId] = $(inputId).value;
      }
   }
   toAjaxTableEditor('edit_row',info);
}

/**
 * show alert and disable the edit page
 * @param varPrefix
 * @param message - alert meesage
 */

function disableEditPage(varPrefix,message) {

   var updateButton = document.getElementById(varPrefix + '_update');

   clear_load_timeout(0);
   if(updateButton) {
      updateButton.disabled=true;
   }
   if(message) {
      alert(message);
   } else {
      alert('Edit Page is Disabled!');
   }
}

function updateMultRows(idArr,varPrefix) {
   if(confirm(mateUpdateMultMsg.replace(/#num_rows#/,idArr.length))) {
      var info = new Object();
      info.idArr = idArr;
      info.inputInfo = new Object();
      var formElem = document.getElementById(varPrefix + '_edit_form');
      for(var i=0; i < formElem.elements.length; i++) {
         var elem = formElem.elements[i];
         var inputId = elem.id;
         if(elem.disabled == false) {
            if(elem.type.toLowerCase() == 'radio') {
               if(elem.checked) {
                  info.inputInfo[inputId] = elem.value;
               }
            } else if(elem.type.toLowerCase() == 'select-multiple') {
               info.inputInfo[inputId] = getMultipleSelection(elem);
            } else {
               info.inputInfo[inputId] = $(inputId).value;
            }
         }
      }
      toAjaxTableEditor('update_mult_rows',info);
   }
}

/**
 * save the changed entries and refresh the mult-edit page
 * @param idArr - the array of primary key ids under editing
 * @param varPrefix
 */

function refreshMultEditPage(idArr,varPrefix) {

   var info = new Object();
   var formElem = document.getElementById(varPrefix + '_edit_form');

   info.idArr = idArr;
   info.inputInfo = new Object();
   for(var i=0; i < formElem.elements.length; i++) {
      var elem = formElem.elements[i];
      var inputId = elem.id;
      if(elem.disabled == false) {
         if(elem.type.toLowerCase() == 'radio') {
            if(elem.checked) {
               info.inputInfo[inputId] = elem.value;
            }
         } else if(elem.type.toLowerCase() == 'select-multiple') {
            info.inputInfo[inputId] = getMultipleSelection(elem);
         } else {
            info.inputInfo[inputId] = $(inputId).value;
         }
      }
   }

   info['old_primary_key_value'] = id;

   toAjaxTableEditor('edit_mult_rows',info);
}

function addRow(varPrefix) {
   var info = new Object();
   var formElem = document.getElementById(varPrefix + '_add_form');

   for(var i=0; i < formElem.elements.length; i++) {
      var elem = formElem.elements[i];
      var inputId = elem.id;
      if(elem.type.toLowerCase() == 'radio') {
         if(elem.checked) {
            info[inputId] = elem.value;
         }
      } else if(elem.type.toLowerCase() == 'select-multiple') {
         info[inputId] = getMultipleSelection(elem);
      } else {
         info[inputId] = $(inputId).value;
      }
   }
   toAjaxTableEditor('insert_row',info);
}

/**
 * save the new or changed entries and refresh the add page
 * @param varPrefix
 */
function refreshAddPage(varPrefix) {

   var info = new Object();
   var formElem = document.getElementById(varPrefix + '_add_form');

   for(var i=0; i < formElem.elements.length; i++) {
      var elem = formElem.elements[i];
      var inputId = elem.id;
      if(elem.type.toLowerCase() == 'radio') {
         if(elem.checked) {
            info[inputId] = elem.value;
         }
      } else if(elem.type.toLowerCase() == 'select-multiple') {
         info[inputId] = getMultipleSelection(elem);
      } else {
         info[inputId] = $(inputId).value;
      }
   }
   toAjaxTableEditor('add_row',info);
}

function enterPressed(e)
{
   var key;
   if(!e) {
      if(window.event) {
         e = window.event;
      } else {
         e = event;
      }
    }
    key = (e.which ? e.which : e.keyCode);

   if (key == 13) {
      return true;   // Enter key is 13
   } else {
      return false;
   }
}

function handleAdvancedSearch(numSearches)
{
   var i;
   var info = new Object();
   for(i = 0; i < numSearches; i++)
   {
      info[i] = new Object();
      info[i]['cols'] = $('as_cols_' + i).value;
      info[i]['opts'] = $('as_opts_' + i).value;
      info[i]['strs'] = $('as_strs_' + i).value;
   }
   toAjaxTableEditor('advanced_search',info);
}

function selectAllCbs(cb,varPrefix)
{
   var i;
   var tableForm = $(varPrefix + '_table_form');
   if(cb.checked) {
      for(i=0; i < tableForm.elements.length; i++) {
         var checkbox = tableForm.elements[i];
         if(checkbox.disabled == false) {
            checkbox.checked = true;
            changeRowStyle(checkbox);
         }
      }
   } else {
      for(i=0; i < tableForm.elements.length; i++) {
         var checkbox = tableForm.elements[i];
         if(checkbox.disabled == false) {
            checkbox.checked = false;
            changeRowStyle(checkbox);
         }
      }
   }
}

function setCheckedCbs(idArr,varPrefix)
{
   for(var i=0; i < idArr.length; i++) {
      if(idArr[i] == 0) {
         selectAllCbs($('select_all_cb'), varPrefix);
      } else {
         cellClicked(idArr[i], '');
      }
   }
}

function changeRowStyle(cb)
{
   var idParts = cb.id.split('_');
   var id = idParts[1];
   if(cb.checked) {
      var row = $('row_' + id);
      if(row != null) {
         row.setStyle('background-color: #fcffd0;');
      }
   } else {
      var row = $('row_' + id);
      if(row != null) {
         var oldColor = '#ffffff;';
         if(row.hasAttribute("bgcolor")) {
            oldColor = row.getAttribute("bgcolor");
         }
         row.setStyle('background-color: ' + oldColor + ';');
      }
   }
}

function checkBoxClicked(cb)
{
   if(cb.checked) {
      cb.checked = false;
   } else {
      cb.checked = true;
   }
}

function cellClicked(id,varPrefix)
{
   var cb = $('cb_' + id);
   if(cb.checked) {
      cb.checked = false;
   } else {
      cb.checked = true;
   }
   changeRowStyle(cb);
   if(varPrefix != '') {
      resetSelectAll(cb.checked,varPrefix);
   }
}

function resetSelectAll(checked,varPrefix)
{
   var cb = $('select_all_cb');
   if(cb.checked) {
      if(!checked) cb.checked = false;
   } else if(checked) {
      var tableForm = $(varPrefix + '_table_form');
      var cbCnt = tableForm.elements.length;
      var i;
      for(i=1; i < cbCnt; i++) {
         var checkbox = tableForm.elements[i];
         if(!(checkbox.disabled || checkbox.checked)) break;
      }
      if(i == cbCnt) {
         cb.checked = true;
      }
   }
}

function userButtonClicked(varPrefix,buttonKey,confirmMsg)
{
   var info = new Object();
   info['buttonKey'] = buttonKey;
   info['checkboxes'] = new Object();
   var numRows = 0;
   var tableForm = $(varPrefix + '_table_form');
   for(var i=0; i < tableForm.elements.length; i++)
   {
      var cb = tableForm.elements[i];
      if(cb.checked && cb.id != 'select_all_cb')
      {
         info['checkboxes'][i] = cb.value;
         numRows++;
      }
   }
   if(numRows == 0)
   {
      alert(mateSelectRow);   
   }
   else if(confirmMsg.length > 0)
   {
      if(confirm(confirmMsg))
      {
         toAjaxTableEditor('user_button_clicked',info);
      }
   }
   else
   {
      toAjaxTableEditor('user_button_clicked',info);      
   }
}

function userIconClicked(action,info,confirmMsg)
{
   if(confirmMsg.length > 0)
   {
      if(confirm(confirmMsg))
      {
         toAjaxTableEditor(action,info);
      }
   }
   else
   {
      toAjaxTableEditor(action,info);      
   }
}

function editCopyViewDelete(varPrefix,action)
{
   var info = new Object();
   var numRows = 0;
   var selectedIndex = 0;
   var tableForm = $(varPrefix + '_table_form');
   for(var i=0; i < tableForm.elements.length; i++) {
      var cb = tableForm.elements[i];
      if(cb.checked && cb.id != 'select_all_cb') {
         info[i] = cb.value;
         selectedIndex = i;
         numRows++;
      }
   }
   if(numRows == 0) {
      alert(mateSelectRow);
   } else {
      if(action == 'edit_row') {
         if(numRows == 1) {
            toAjaxTableEditor(action,info[selectedIndex]);
         } else {
            //alert(mateEdit1Row);
            toAjaxTableEditor('edit_mult_rows',info);            
         }
      } else if(action == 'view_row') {
         if(numRows == 1) {
            toAjaxTableEditor(action,info[selectedIndex]);
         } else {
            alert(mateView1Row);   
         }
      } else if(action == 'copy_row') {
         if(numRows == 1) {
            toAjaxTableEditor(action,info[selectedIndex]);
         } else {
            alert(mateCopy1Row);
         }
      } else if(action == 'delete_row') {
         var confirmMsg;
         if(numRows == 1) {
            confirmMsg = mateDeleteMsg;
         } else {
            confirmMsg = mateDeleteMultMsg.replace(/#num_rows#/,numRows);
         } 
         if(confirm(confirmMsg)) {
            if(numRows == 1) {
               toAjaxTableEditor(action,info[selectedIndex]);
            } else {
               toAjaxTableEditor('delete_mult_rows',info);
            }
         }
      } else if(action == 'copy_mult_rows') {
         if(numRows == 1)
         {
            toAjaxTableEditor('copy_row',info[selectedIndex]);
         }
         else if(confirm(mateCopyMultMsg.replace(/#num_rows#/,numRows)))
         {
            toAjaxTableEditor(action,info);
         }
      }
   }
}

function formatDate(dateStr,dateFormat)
{
   var date = new Date(dateStr.substring(0,4),dateStr.substring(5,7) - 1,dateStr.substring(8,10),dateStr.substring(11,13),dateStr.substring(14,16),dateStr.substring(17,19));
   info = new Object();
   info["disp_date"] = date.print(dateFormat);
   info["php_date"] = dateStr;
   info["js_date"] = date;
   return info;
}

function prepareForCalendar(input,id,dateFormat,resetDate,extraInfo,hide)
{
   var jsPath2 = jsPath == null ? 'js/' : jsPath;
   if(input) {
      if(!dateFormat) { dateFormat = '%d %B %Y'; }
//      input.id = id;
      var phpDate = '0000-00-00';
      var dispDate = mateNoDate;
      var jsDate = new Date();
      var result = input.value.search(/0000-00-00/);
      var resetStr = resetDate ? '<a class="resetDate" href="javascript: void(0);" onclick="resetDate(\''+
            id+'\');" title="'+mateRemoveDate+'"><img src="'+jsPath2.substring(0,jsPath2.length - 3)+
            'images/reset_date.gif" alt="reset" /></a>' : '';

      if(result == -1 && input.value.length > 0) {
         dateInfo = formatDate(input.value,dateFormat);
         dispDate = dateInfo["disp_date"];
         jsDate = dateInfo["js_date"];
         phpDate = dateInfo["php_date"];
      }
      var stime = (dateFormat.match(/%H/)? true : false);
      var container = input.parentNode;
      var display = hide ?  ' style="display: none;"' : '';
      container.innerHTML = '<span id="show_'+id+'">'+dispDate+'</span><span id="'+id+'_calendar"'+display+'><img src="'+jsPath2+'jscalendar/img.gif" id="trigger_'+id+
         '" style="cursor: pointer; border: 1px solid blue; margin: 0 2px 0 2px;" title="Date selector" onMouseOver="this.style.background=\'red\';" onmouseout="this.style.background=\'\'" />'+
         resetStr+extraInfo+'<input type="hidden" name="'+id+'" id="'+id+'" value="'+phpDate+'" disabled="disabled" /></span>';
      Calendar.setup({
         inputField     :    id,     // id of the input field
         ifFormat       :    "%Y-%m-%d %H:%M:%S",     // format of the input field (even if hidden, this format will be honored)
         displayArea    :    "show_"+id,       // ID of the span where the date is to be shown
         daFormat       :    dateFormat,     // format of the displayed date
         button         :    "trigger_"+id,  // trigger button (well, IMG in our case)
         align          :    "Tl",
         date           :    jsDate,
         showsTime      :    stime,
         singleClick    :    true,      
         weekNumbers    :    false
      });         
   }
}

function resetDate(id)
{
   $(id).value = '0000-00-00';
   $('show_'+id).innerHTML = mateNoDate;
}

function resetScrollTop()
{
   document.documentElement.scrollTop = 0;
   document.body.scrollTop = 0;
}

function showHideColumn(cb,col)
{
    if(cb.checked)
    {
        toAjaxTableEditor('show_column',col);
    }
    else
    {
        toAjaxTableEditor('hide_column',col);
    }
}

function disableEnableInput(column,cb)
{
   var col = $(column);
   var req = $(column + '_req_mark');
   var cal = $(column + '_calendar');
   
   if(cb.checked) {
/**
      if(col && col.type != 'hidden') {
         col.disabled = false;
      }
 */
      if(col) {
         col.disabled = false;
      }
      if(req) {
         req.setStyle("display: inline;");
      }
      if(cal) {
         cal.setStyle("display: inline;");
      }
   } else {
/**
      if(col && col.type != 'hidden') {
         col.disabled = true;
      }
 */
      if(col) {
         col.disabled = true;
      }
      if(req) {
         req.setStyle("display: none;");
      }
      if(cal) {
         cal.setStyle("display: none;");
      }
   }
}

function updateCheckBoxValue(cb,checkedValue,unCheckedValue)
{
   if(cb.checked)
   {
      cb.value = checkedValue;
   }
   else
   {
      cb.value = unCheckedValue;
   }
}
