var parts = x.split(',');
if (parts.length != 2) return 0;
var num = parts[0];
var den = parts[1];
if (!/^(?:0|-?[1-9][0-9]*)$/.test(num)) return 0;
if (!/^[1-9][0-9]*$/.test(num)) return 0;
return 1;

