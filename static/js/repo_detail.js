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

// Stop linting button

$('#stop_linting').on('click', function (e) {
  var elem = e.target;
  $('#stop_linting').addClass('loading');
  $('#stop_linting_modal').modal({
    onDeny: function () {
      $('#stop_linting').removeClass('loading');
    },
    onApprove: function () {
      $('#confirm_button').addClass('loading');
      $('#stop_linting').api({
          action: 'stop_linting',
          on: 'now',
          method: 'DELETE',
          onSuccess: function() {
            // redirect user
            window.location = '/repos';
          },
          onFailure: function() {
            // Tell user it failed
            window.alert('An error occured while attempting to delete this repo.');
            $('#confirm_button').removeClass('loading');
            $('#stop_linting').removeClass('loading');
          }
      });
      return false;
    }
  }).modal('show');
});
