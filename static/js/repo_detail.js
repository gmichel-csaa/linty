var copyButton = new Clipboard('.copy_button');
var btns = document.querySelectorAll('.copy_button');
for (var i = 0; i < btns.length; i++) {
  btns[i].addEventListener('mouseleave', function (e) {
    e.currentTarget.removeAttribute('data-tooltip');
  });
}
function showTooltip(elem, msg) {
  elem.setAttribute('data-tooltip', msg);
}
function fallbackMessage(action) {
  var actionMsg = '';
  var actionKey = (action === 'cut' ? 'X' : 'C');
  if (/iPhone|iPad/i.test(navigator.userAgent)) {
    actionMsg = 'No support :(';
  }
  else if (/Mac/i.test(navigator.userAgent)) {
    actionMsg = 'Press ⌘-' + actionKey + ' to ' + action;
  }
  else {
    actionMsg = 'Press Ctrl-' + actionKey + ' to ' + action;
  }
  return actionMsg;
}
copyButton.on('success', function (e) {
  e.clearSelection();
  showTooltip(e.trigger, 'Copied!');
});
copyButton.on('error', function (e) {
  showTooltip(e.trigger, fallbackMessage(e.action));
});

// Stop linting button

$('#stop_linting').api({
    action: 'stop_linting',
    on: 'click',
    method: 'DELETE',
    onSuccess: function() {
      // redirect user
      window.location = '/repos';
    },
    onFailure: function() {
      // Tell user it failed
      window.alert('An error occured while attempting to delete this repo.');
      $('#stop_linting').removeClass('loading');
    }
});

$('#default_branch').dropdown();
$('#settings_modal').modal({
  'autofocus': false,
  'onApprove': function() {
    $('#save_button').addClass('loading');
    $('#settings_form').submit().find('.field').addClass('disabled');
    return false;
  }
});
$('#settings').on('click', function(){
   $('#settings_modal').modal('show');
});
$('.build_row').on('click', function(){
  window.location = this.querySelector('.build_link').href;
});
$('#filter_select').dropdown({'action': function(text, value){
  var root = window.location.origin + window.location.pathname;
  if (value === '*') {
    window.location = root;
  } else {
    window.location = root + '?ref=' + value;
  }
}});