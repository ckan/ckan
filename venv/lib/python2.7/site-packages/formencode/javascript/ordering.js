function up(formElement) {
    var i, select;
    select = getSelect(formElement);
    i = select.selectedIndex;
    if (i == -1 || i == 0) {
        return;
    }
    swapOptions(select, i, i-1);
    select.selectedIndex = i-1;
    saveValue(select);
}
function down(formElement) {
    var i, select;
    select = getSelect(formElement);
    i = select.selectedIndex;
    if (i == -1 || i == select.length-1) {
        return;
    }
    swapOptions(select, i, i+1);
    select.selectedIndex = i+1;
    saveValue(select);
}
function getSelect(formElement) {
    return formElement.form['%(name)s']
}
function swapOptions(select, op1, op2) {
    var tmpValue, tmpText;
    tmpValue = select.options[op1].value;
    tmpText = select.options[op1].text;
    select.options[op1].value = select.options[op2].value;
    select.options[op1].text = select.options[op2].text;
    select.options[op2].value = tmpValue;
    select.options[op2].text = tmpText;
}
function saveValue(select) {
    if (origValues == false) {
        saveOrigValues(select);
    }
    var s = "", i;
    for (i=0; i < select.length; i++) {
        s = s + escape(select.options[i].value) + " ";
    }
    select.form['%(hidden_name)s'].value = s;
}
function saveOrigValues(select) {
    origValues = new Array();
    for (i=0; i<select.length; i++) {
        origValues[i*2] = select.options[i].value;
        origValues[i*2+1] = select.options[i].text;
    }
}
origValues = false;
function resetEntries(formElement) {
    var select;
    select = getSelect(formElement);
    for (i=0; i<origValues.length; i+=2) {
        select.options[Math.floor(i/2)] = new Option(origValues[i+1], origValues[i], false, false);
        select.options[Math.floor(i/2)].selected = false;
    }
    saveValue(select);
}
