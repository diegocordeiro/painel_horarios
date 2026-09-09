(function () {
  // Tema claro/escuro
  var btn = document.getElementById('themeToggle');
  var saved = null;
  try { saved = localStorage.getItem('site-theme'); } catch (e) {}
  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    try { localStorage.setItem('site-theme', theme); } catch (e) {}
  }
  if (saved) applyTheme(saved);
  else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) applyTheme('dark');
  if (btn) {
    btn.addEventListener('click', function () {
      var cur = document.documentElement.getAttribute('data-theme');
      applyTheme(cur === 'dark' ? 'light' : 'dark');
    });
  }

  // Modos de visualização da grade
  var table = document.getElementById('timetable');
  if (!table) return;
  var rows = Array.prototype.slice.call(table.querySelectorAll('tbody .time-row'));
  var first = parseInt(table.dataset.first || '0', 10);
  var last = parseInt(table.dataset.last || (rows.length - 1), 10);
  var activeDays = new Set((table.dataset.activeDays || '').split('|').filter(Boolean));

  function apply(mode) {
    rows.forEach(function (row, i) {
      var hasClass = row.classList.contains('row-active');
      if (mode === 'completed') row.style.display = '';
      else if (mode === 'condensed') row.style.display = (i >= first && i <= last) ? '' : 'none';
      else row.style.display = hasClass ? '' : 'none';
    });
    table.querySelectorAll('.day-head, .day-cell').forEach(function (el) {
      var day = el.getAttribute('data-day');
      el.style.display = (mode === 'superCondensed' && !activeDays.has(day)) ? 'none' : '';
    });
  }

  var toolbar = document.querySelector('.timetable-toolbar') || table.previousElementSibling;
  var modeBtns = (toolbar && toolbar.querySelectorAll) ? toolbar.querySelectorAll('.mode-btn') : [];
  Array.prototype.forEach.call(modeBtns, function (b) {
    b.addEventListener('click', function () {
      Array.prototype.forEach.call(modeBtns, function (x) { x.classList.remove('active'); });
      b.classList.add('active');
      apply(b.getAttribute('data-mode'));
    });
  });

  // Aplica o modo padrão ao abrir a página (botão ativo no HTML, ou superCondensed).
  var current = (toolbar && toolbar.querySelector) ? toolbar.querySelector('.mode-btn.active') : null;
  apply(current ? current.getAttribute('data-mode') : 'superCondensed');
})();
