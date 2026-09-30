/* site.js — 全站交互：公告条、移动端导航、客服弹窗、复制微信、FAQ 折叠 */
(function () {
  'use strict';

  var cfg = {};
  try {
    var el = document.getElementById('site-config');
    if (el) cfg = JSON.parse(el.textContent || '{}');
  } catch (e) { cfg = {}; }

  var contact = cfg.contact || {};
  var wechatList = contact.wechatList || [];
  var qrImage = contact.qrImage || '';
  var services = contact.modalServices || [];
  var orderQueryUrl = contact.orderQueryUrl || '';

  /* ---------- 公告条高度 ----------
     页面里有一段内联脚本（紧随公告条）在解析阶段就测量并写好了 CSS 变量，
     这里只负责关闭按钮与尺寸变化后重算。 */
  function applyNoticeHeight() {
    if (typeof window.__applyNoticeHeight === 'function') { window.__applyNoticeHeight(); return; }
    var bar = document.querySelector('.notice-bar');
    var h = 0;
    if (bar && !bar.hidden && bar.offsetHeight > 0) h = bar.offsetHeight;
    document.documentElement.style.setProperty('--notice-bar-height', h + 'px');
  }

  function initNoticeBar() {
    var bar = document.querySelector('.notice-bar');
    if (!bar) return;
    var dismissed = false;
    try { dismissed = localStorage.getItem('notice-dismissed') === '1'; } catch (e) {}
    if (dismissed) bar.hidden = true;
    var btn = bar.querySelector('.notice-close');
    if (btn) {
      btn.addEventListener('click', function () {
        bar.hidden = true;
        try { localStorage.setItem('notice-dismissed', '1'); } catch (e) {}
        applyNoticeHeight();
      });
    }
    applyNoticeHeight();
    window.addEventListener('resize', applyNoticeHeight);
    window.addEventListener('load', applyNoticeHeight);
  }

  /* ---------- 移动端导航 ---------- */
  function initMobileNav() {
    var toggle = document.querySelector('.mobile-nav-toggle');
    var menu = document.querySelector('.mobile-nav-menu');
    if (!toggle || !menu) return;
    toggle.addEventListener('click', function (e) {
      e.stopPropagation();
      menu.classList.toggle('active');
      toggle.setAttribute('aria-expanded', menu.classList.contains('active') ? 'true' : 'false');
    });
    document.addEventListener('click', function (e) {
      if (menu.classList.contains('active') && !menu.contains(e.target) && !toggle.contains(e.target)) {
        menu.classList.remove('active');
      }
    });
  }

  /* ---------- 滚动阴影 ---------- */
  function initHeaderShadow() {
    var header = document.querySelector('.main-header');
    if (!header) return;
    var onScroll = function () {
      if (window.scrollY > 6) header.classList.add('scrolled');
      else header.classList.remove('scrolled');
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  /* ---------- Toast ---------- */
  var toastTimer = null;
  function toast(msg) {
    var t = document.querySelector('.toast');
    if (!t) {
      t = document.createElement('div');
      t.className = 'toast';
      document.body.appendChild(t);
    }
    t.textContent = msg;
    requestAnimationFrame(function () { t.classList.add('show'); });
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { t.classList.remove('show'); }, 1900);
  }

  /* ---------- 复制微信 ---------- */
  function copyText(text) {
    var handled = false;
    function done() { if (handled) return; handled = true; toast('已复制微信号：' + text); }
    function fallback() {
      if (handled) return;
      var ta = document.createElement('textarea');
      ta.value = text;
      ta.setAttribute('readonly', '');
      ta.style.cssText = 'position:absolute;left:-9999px;top:0;';
      document.body.appendChild(ta);
      ta.select();
      var ok = false;
      try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
      document.body.removeChild(ta);
      if (ok) done(); else { handled = true; toast('请手动复制：' + text); }
    }

    if (navigator.clipboard && navigator.clipboard.writeText && window.isSecureContext) {
      // 剪贴板 API 在部分浏览器/未获得焦点时会一直不 resolve，加个兜底计时器
      var timer = setTimeout(fallback, 300);
      navigator.clipboard.writeText(text).then(
        function () { clearTimeout(timer); done(); },
        function () { clearTimeout(timer); fallback(); }
      );
    } else {
      fallback();
    }
  }

  function initCopy() {
    document.addEventListener('click', function (e) {
      var target = e.target.closest('[data-copy]');
      if (!target) return;
      e.preventDefault();
      e.stopPropagation();
      copyText(target.getAttribute('data-copy'));
    });
  }

  /* ---------- 客服弹窗 ---------- */
  var modalEl = null;
  var lastFocus = null;

  function svgChat() {
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/></svg>';
  }

  function buildModal() {
    var chips = services.map(function (s) { return '<span><i></i>' + s + '</span>'; }).join('');
    var ids = wechatList.map(function (w) {
      return '<span class="id" data-copy="' + w + '" style="cursor:pointer">' + w + '</span>';
    }).join(' / ');

    var html = '' +
      '<div class="cs-modal" role="dialog" aria-modal="true" aria-label="联系客服">' +
        '<div class="cs-card">' +
          '<div class="cs-head">' +
            '<h3>联系客服</h3>' +
            '<button class="cs-close" type="button" aria-label="关闭">' +
              '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>' +
            '</button>' +
          '</div>' +
          '<div class="cs-panel">' +
            '<h4>AI 工具充值服务</h4>' +
            '<p>支持充值多种 AI 工具，让您畅享智能体验：</p>' +
            '<div class="cs-chips">' + chips + '</div>' +
          '</div>' +
          '<div class="cs-qr">' +
            (qrImage ? '<img src="' + qrImage + '" alt="微信二维码">' : '') +
            '<div class="cs-wechat">微信号：' + ids + '</div>' +
            '<p class="cs-time">' + (contact.workTime || '') + '</p>' +
            '<p class="cs-time" style="margin-top:6px">点击微信号即可复制</p>' +
          '</div>' +
        '</div>' +
      '</div>';

    var wrap = document.createElement('div');
    wrap.innerHTML = html;
    modalEl = wrap.firstChild;
    document.body.appendChild(modalEl);
    document.body.style.overflow = 'hidden';

    modalEl.addEventListener('click', function (e) {
      if (e.target === modalEl || e.target.closest('.cs-close')) closeModal();
    });
    document.addEventListener('keydown', onKeydown);
  }

  function onKeydown(e) {
    if (e.key === 'Escape' && modalEl) closeModal();
  }

  function closeModal() {
    if (!modalEl) return;
    modalEl.remove();
    modalEl = null;
    document.body.style.overflow = '';
    document.removeEventListener('keydown', onKeydown);
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  function openCustomerService(e) {
    if (e) e.preventDefault();
    lastFocus = document.activeElement;
    if (modalEl) return;
    buildModal();
    var btn = modalEl.querySelector('.cs-close');
    if (btn) btn.focus();
  }

  function initCustomerService() {
    document.addEventListener('click', function (e) {
      var trigger = e.target.closest('[data-action="customer-service"]');
      if (trigger) openCustomerService(e);
    });
  }

  /* ---------- 查询订单 ---------- */
  function initOrderQuery() {
    document.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-action="order-query"]');
      if (!btn) return;
      e.preventDefault();
      if (orderQueryUrl) window.open(orderQueryUrl, '_blank', 'noopener');
      else openCustomerService(e);
    });
  }

  /* ---------- 购买按钮 ---------- */
  function initBuyButtons() {
    document.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-buy]');
      if (!btn) return;
      var url = btn.getAttribute('data-buy');
      if (!url || url === '#') {
        e.preventDefault();
        toast('该套餐请添加客服微信下单');
        openCustomerService(e);
      }
    });
  }

  /* ---------- FAQ 折叠 ---------- */
  function initFaq() {
    var qs = document.querySelectorAll('.faq-q');
    Array.prototype.forEach.call(qs, function (q) {
      q.addEventListener('click', function () {
        var item = q.closest('.faq-item');
        var open = item.classList.contains('open');
        Array.prototype.forEach.call(document.querySelectorAll('.faq-item.open'), function (o) { o.classList.remove('open'); });
        if (!open) item.classList.add('open');
      });
    });
  }

  /* ---------- 启动 ---------- */
  function init() {
    initNoticeBar();
    initMobileNav();
    initHeaderShadow();
    initCopy();
    initCustomerService();
    initOrderQuery();
    initBuyButtons();
    initFaq();

    // 动态渲染悬浮客服按钮（避免每页重复写）
    if (!document.querySelector('.fab')) {
      var fab = document.createElement('button');
      fab.className = 'fab';
      fab.type = 'button';
      fab.setAttribute('data-action', 'customer-service');
      fab.setAttribute('aria-label', '联系客服');
      fab.innerHTML = svgChat() + '<span>客服</span>';
      document.body.appendChild(fab);
    }

    // 页面深处的锚点跳转补偿固定头部
    if (location.hash) {
      var t = document.querySelector(location.hash);
      if (t) setTimeout(function () { t.scrollIntoView({ behavior: 'smooth', block: 'start' }); }, 60);
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();

  window.SiteUI = { toast: toast, openCustomerService: openCustomerService, copyText: copyText };
})();
