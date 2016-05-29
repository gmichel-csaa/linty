var copyButton = new Clipboard('.copy_button');
var btns = document.querySelectorAll('.copy_button');
for (var i = 0; i < btns.length; i++) {
  btns[i].addEventListener('mouseleave', function (e) {
    $('.copy_button').popup('hide');
    e.currentTarget.removeAttribute('data-content');
  });
}
function showTooltip(elem, msg) {
  elem.setAttribute('data-content', msg);
  $('.copy_button').popup('show');
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
