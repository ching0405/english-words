// Home-screen app: registers sw.js (offline play, see sw.js) and picks up a
// new version. The new worker takes over at once; this page then reloads the
// next time the home screen shows, so a round in progress is never cut off.
// Progress lives in localStorage, so a reload loses nothing.
(function () {
  'use strict';

  var sw = navigator.serviceWorker;
  var pending = false;
  window.Pwa = { atHome: function () { if (pending) location.reload(); } };
  if (!sw || location.protocol === 'file:') return;

  var hadController = !!sw.controller;
  sw.addEventListener('controllerchange', function () {
    // The first install also fires this; only a replaced worker means a new version.
    if (!hadController) { hadController = true; return; }
    pending = true;
    var home = document.querySelector('#home');
    if (home && !home.hidden) location.reload();
  });

  window.addEventListener('load', function () {
    sw.register('sw.js', { updateViaCache: 'none' }).then(function (reg) {
      // An app left open on the iPad checks for a new version when it comes back.
      document.addEventListener('visibilitychange', function () {
        if (document.visibilityState === 'visible') reg.update().catch(function () { /* offline */ });
      });
    }).catch(function () { /* no offline play; the game still works online */ });
  });
})();
