(function () {
  'use strict';
  var dados = JSON.parse(document.getElementById('dados').textContent);
  function $(id) { return document.getElementById(id); }

  /* PURE:START */
  var HORARIOS = dados.horarios;
  function waLink(texto) { return 'https://wa.me/' + dados.whatsapp + '?text=' + encodeURIComponent(texto); }
  function brl(v) { return v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }); }
  function pmt(principal, taxa, n) {
    if (!(principal > 0) || !(n > 0)) return 0;
    if (!(taxa > 0)) return principal / n;
    return principal * taxa / (1 - Math.pow(1 + taxa, -n));
  }
  function toMin(hhmm) { var p = hhmm.split(':'); return (+p[0]) * 60 + (+p[1]); }
  function agoraRO(data) {
    var parts = new Intl.DateTimeFormat('en-US', { timeZone: 'America/Porto_Velho', weekday: 'short', hour: 'numeric', minute: 'numeric', hourCycle: 'h23' }).formatToParts(data || new Date());
    var get = function (t) { for (var i = 0; i < parts.length; i++) { if (parts[i].type === t) return parts[i].value; } return '0'; };
    var dias = { Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6 };
    return { dia: dias[get('weekday')], min: (parseInt(get('hour'), 10) % 24) * 60 + parseInt(get('minute'), 10) };
  }
  function situacao(data) {
    var a = agoraRO(data), h = HORARIOS[a.dia].h;
    if (h && a.min >= toMin(h[0]) && a.min < toMin(h[1])) return { aberto: true, texto: 'Aberto agora, fecha às ' + h[1] };
    for (var k = 0; k <= 7; k++) {
      var d = (a.dia + k) % 7, hh = HORARIOS[d].h;
      if (hh && (k > 0 || a.min < toMin(hh[0]))) {
        var quando = k === 0 ? 'hoje' : (k === 1 ? 'amanhã' : HORARIOS[d].nome);
        return { aberto: false, texto: 'Fechado agora, abre ' + quando + ' às ' + hh[0] };
      }
    }
    return { aberto: false, texto: 'Fechado agora' };
  }
  function cmpNum(x, y, asc) {
    if (x == null && y == null) return 0;
    if (x == null) return 1;
    if (y == null) return -1;
    return asc ? x - y : y - x;
  }
  /* PURE:END */

  /* Situação da loja e dia de hoje na tabela de horários */
  var st = $('status');
  if (st) {
    var s = situacao();
    st.className = 'status ' + (s.aberto ? 'open' : 'closed');
    $('statusText').textContent = s.texto;
  }
  var linhas = document.querySelectorAll('#horarios tr[data-dia]');
  if (linhas.length) {
    var hoje = String(agoraRO().dia);
    for (var i = 0; i < linhas.length; i++) {
      if (linhas[i].getAttribute('data-dia') === hoje) linhas[i].className = 'today';
    }
  }

  /* Estoque: filtro e ordem sobre os cartões já presentes na página */
  var grid = $('grid');
  if (grid) {
    var cartoes = Array.prototype.slice.call(grid.querySelectorAll('.car'));
    var filtro = 'todos', ordem = 'padrao';
    var val = function (c, k) {
      var v = c.getAttribute('data-' + k);
      return v === null || v === '' ? null : parseFloat(v);
    };
    var comparadores = {
      'padrao': function (a, b) { return val(a, 'pos') - val(b, 'pos'); },
      'preco-asc': function (a, b) { return cmpNum(val(a, 'preco'), val(b, 'preco'), true); },
      'preco-desc': function (a, b) { return cmpNum(val(a, 'preco'), val(b, 'preco'), false); },
      'ano-desc': function (a, b) { return cmpNum(val(a, 'ano'), val(b, 'ano'), false); },
      'km-asc': function (a, b) { return cmpNum(val(a, 'km'), val(b, 'km'), true); }
    };
    var aplicar = function () {
      var lista = cartoes.filter(function (c) { return filtro === 'todos' || c.getAttribute('data-tipo') === filtro; });
      cartoes.forEach(function (c) { c.hidden = lista.indexOf(c) === -1; });
      lista.sort(comparadores[ordem]).forEach(function (c) { grid.appendChild(c); });
      var v = $('vazio'); if (v) v.hidden = lista.length > 0;
    };
    var chips = document.querySelectorAll('.chip');
    chips.forEach(function (b) {
      b.addEventListener('click', function () {
        filtro = b.getAttribute('data-f');
        chips.forEach(function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
        aplicar();
      });
    });
    $('ordem').addEventListener('change', function (e) { ordem = e.target.value; aplicar(); });
  }

  /* Simulador de financiamento */
  if ($('sim')) {
    var simular = function () {
      var valor = parseFloat($('s-valor').value) || 0;
      var entrada = parseFloat($('s-entrada').value) || 0;
      var n = parseInt($('s-parcelas').value, 10);
      var taxa = (parseFloat($('s-taxa').value) || 0) / 100;
      var fin = Math.max(valor - entrada, 0);
      var p = pmt(fin, taxa, n);
      $('r-parcela').textContent = brl(p);
      $('r-fin').textContent = brl(fin);
      $('r-total').textContent = brl(p * n);
      $('r-wa').href = waLink('Olá! Fiz uma simulação no site da Branco Veículos: veículo de ' + brl(valor) + ', entrada de ' + brl(entrada) +
        ', ' + n + ' parcelas de cerca de ' + brl(p) + ' (taxa estimada de ' + (taxa * 100).toLocaleString('pt-BR') + '% ao mês). Pode me ajudar com as condições?');
    };
    ['s-valor', 's-entrada', 's-parcelas', 's-taxa'].forEach(function (id) { $(id).addEventListener('input', simular); });
    $('sim').addEventListener('submit', function (e) { e.preventDefault(); });
    simular();
  }

  /* Avaliação para compra ou troca */
  if ($('troca')) {
    $('troca').addEventListener('submit', function (e) {
      e.preventDefault();
      var nota = $('t-nota');
      var nome = $('t-nome').value.trim(), modelo = $('t-modelo').value.trim(), ano = $('t-ano').value.trim();
      if (!nome || !modelo || !ano) {
        nota.className = 'form-note form-err';
        nota.textContent = 'Preencha seu nome, a marca e modelo e o ano do veículo.';
        return;
      }
      var km = $('t-km').value.trim(), obs = $('t-obs').value.trim();
      var msg = 'Olá! Quero avaliar meu veículo para compra ou troca.\nNome: ' + nome + '\nVeículo: ' + modelo + '\nAno: ' + ano +
        (km ? '\nQuilometragem: ' + parseInt(km, 10).toLocaleString('pt-BR') + ' km' : '') + (obs ? '\nObservações: ' + obs : '');
      window.open(waLink(msg), '_blank', 'noopener');
      nota.className = 'form-note';
      nota.textContent = 'O WhatsApp abriu com a mensagem pronta. Falta só enviar.';
    });
  }

  /* Galeria de fotos da página do veículo */
  var viewer = $('g-viewer');
  if (viewer) {
    var ths = document.querySelectorAll('#g-ths .th');
    var n = ths.length, idx = 0;
    var img = $('g-img'), cnt = $('g-count'), cap = $('g-cap'), tira = $('g-ths');
    var nome = img.getAttribute('data-nome') || '';
    var ir = function (k) {
      idx = (k + n) % n;
      var t = ths[idx], legenda = t.getAttribute('data-leg') || '';
      img.src = t.getAttribute('data-full');
      img.alt = nome + (legenda ? ': ' + legenda : '');
      cnt.textContent = (idx + 1) + ' / ' + n;
      cap.textContent = legenda;
      for (var j = 0; j < n; j++) ths[j].setAttribute('aria-current', j === idx ? 'true' : 'false');
      if (tira.scrollTo) tira.scrollTo({ left: t.offsetLeft - (tira.clientWidth - t.offsetWidth) / 2, behavior: 'smooth' });
    };
    if (n > 1) {
      $('g-prev').addEventListener('click', function () { ir(idx - 1); });
      $('g-next').addEventListener('click', function () { ir(idx + 1); });
      for (var j = 0; j < n; j++) { (function (k) { ths[k].addEventListener('click', function () { ir(k); }); })(j); }
      var x0 = null;
      viewer.addEventListener('touchstart', function (e) { x0 = e.touches[0].clientX; }, { passive: true });
      viewer.addEventListener('touchend', function (e) {
        if (x0 === null) return;
        var dx = e.changedTouches[0].clientX - x0; x0 = null;
        if (Math.abs(dx) > 40) ir(dx < 0 ? idx + 1 : idx - 1);
      }, { passive: true });
      document.addEventListener('keydown', function (e) {
        var t = e.target && e.target.tagName;
        if (t === 'INPUT' || t === 'TEXTAREA' || t === 'SELECT') return;
        if (e.key === 'ArrowLeft') ir(idx - 1);
        if (e.key === 'ArrowRight') ir(idx + 1);
      });
    }
  }
})();
