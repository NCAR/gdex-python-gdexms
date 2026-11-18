/************************************************************************************************
 * 
 *     Title : validation.js
 *    Author : Zaihua Ji,  zji@ucar.edu
 *      Date : 2013-10-11
 *   Purpose : code to validate input field
 *
 * Work File : $DSSWEB/internal/rda_pg_config/js/validation.js
 * 
 * **********************************************************************************************/

/**
 * validating keypress against the given field type
 */
function validate_keypress(e,type) {

   var key;

   if(!e) {
     if(window.event) {
        e = window.event;
     } else {
        e = event;
     }
   }
   key = (e.which ? e.which : e.keyCode);

//   alert('Key code = ' + key);    // uncomment for debug

   if(key < 32) return true;

   switch(type) {
   case 'integer':
      return validate_integer(key, true);
   case 'frequency':
      return validate_frequency(key);
   case 'interval':
      return validate_interval(key);
   case 'phoneno':
      return validate_phone_number(key);
   }
   return true;
}

function validate_integer(key, signed) {

   return (key > 47 && key < 58 || signed && key == 45) ? true : false;
}

function validate_unit(key,offset) {
   var units = new Array(83, 78, 72, 68, 87, 77, 89);    //S,N,H,D,W,M,Y

   return (units.indexOf(key,offset) > -1) ? true : false;
}
function validate_frequency(key) {
   var slash = 47;    // '/'
   
   return (validate_integer(key, false) || validate_unit(key,2) || key == slash) ? true : false;
}

function validate_interval(key) {

   return (validate_integer(key, false) || validate_unit(key,0)) ? true : false;
}

function validate_phone_number(key) {
   var chars = new Array(32, 40, 41);   // ' ','(',')'

   return (validate_integer(key, true) || chars.indexOf(key) > -1) ? true : false;
}
