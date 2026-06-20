
/* ═══════════════════════════════════════
   14. PAGE LOADING OVERLAY
   Shows instantly, hides when content ready
═══════════════════════════════════════ */
var _pageLoaderShown = false;
(function(){
  // Show overlay only if page takes >120ms to become interactive
  // (avoids flicker on instant cached loads)
  var t = setTimeout(function(){
    var ov = document.createElement('div');
    ov.id = 'pageLoader';
    ov.className = 'page-loading';
    ov.innerHTML =
      '<div class="page-loading-logo">🎓</div>' +
      '<div class="page-loading-bar"></div>' +
      '<div class="page-loading-text">Loading...</div>';
    var b = document.body;
    if(b) b.insertBefore(ov, b.firstChild);
    _pageLoaderShown = true;
  }, 120);
  window._pageLoaderTimer = t;
})();

function hidePageLoader(){
  clearTimeout(window._pageLoaderTimer);
  var ov = document.getElementById('pageLoader');
  if(!ov) return;
  ov.classList.add('done');
  setTimeout(function(){ ov.remove(); }, 320);
}
window.hidePageLoader = hidePageLoader;


/* ═══════════════════════════════════════
   15. SKELETON HELPERS
═══════════════════════════════════════ */
function skelRows(n, cols){
  var h = '<tbody>';
  for(var i=0; i<(n||5); i++){
    h += '<tr>';
    for(var c=0; c<(cols||4); c++)
      h += '<td><div class="ske ske-row-sm" style="width:'+(60+Math.random()*30).toFixed(0)+'%"></div></td>';
    h += '</tr>';
  }
  return h + '</tbody>';
}
function skelCards(n){
  var h = '';
  for(var i=0; i<(n||3); i++)
    h += '<div class="ske ske-row" style="margin-bottom:8px;"></div>';
  return h;
}
window.skelRows  = skelRows;
window.skelCards = skelCards;

/**
 * School Management System — Ultra Speed Engine v5
 * Mobile-first · Every interaction < 80ms perceived
 */
'use strict';

/* ═══════════════════════════════════════
   1. IN-MEMORY + SESSION CACHE
   90s TTL students · 60s others
═══════════════════════════════════════ */
var CACHE = (function(){
  var _m = {};
  return {
    set: function(k,v,ttl){
      var e = {v:v, x:Date.now()+(ttl||60000)};
      _m[k] = e;
      try{ sessionStorage.setItem('_s_'+k, JSON.stringify(e)); }catch(err){}
    },
    get: function(k){
      var e = _m[k];
      if(!e){ try{ var s=sessionStorage.getItem('_s_'+k); if(s){e=JSON.parse(s);_m[k]=e;} }catch(err){} }
      if(!e || Date.now()>e.x){ delete _m[k]; try{sessionStorage.removeItem('_s_'+k);}catch(err){} return null; }
      return e.v;
    },
    del: function(p){
      Object.keys(_m).forEach(function(k){
        if(!p||k.indexOf(p)===0){ delete _m[k]; try{sessionStorage.removeItem('_s_'+k);}catch(e){} }
      });
    },
    has: function(k){ return this.get(k)!==null; }
  };
})();
window.CACHE = CACHE;

/* ═══════════════════════════════════════
   2. FAST FETCH — abort + timeout + cache
═══════════════════════════════════════ */
function fastFetch(url, opts, cacheKey, ttl){
  if(cacheKey && !opts){
    var cached = CACHE.get(cacheKey);
    if(cached) return Promise.resolve(cached);
  }
  var ctrl  = window.AbortController ? new AbortController() : null;
  var timer = ctrl ? setTimeout(function(){ctrl.abort();}, 10000) : null;
  var o = Object.assign({credentials:'same-origin'}, opts||{});
  if(ctrl) o.signal = ctrl.signal;
  return fetch(url, o)
    .then(function(r){ clearTimeout(timer); if(!r.ok) throw new Error(r.status); return r.json(); })
    .then(function(d){
      if(cacheKey && !opts) CACHE.set(cacheKey, d, ttl||60000);
      return d;
    })
    .catch(function(e){ clearTimeout(timer); throw e; });
}
window.fastFetch = fastFetch;

/* ═══════════════════════════════════════
   3. SEARCH — 120ms debounce (mobile-safe)
   + instant cache hit
═══════════════════════════════════════ */
var _st = null, _lastQ = '';
function fastSearch(q, cb, delay){
  clearTimeout(_st);
  q = (q||'').trim();
  if(!q){ cb([]); return; }
  if(q === _lastQ){ /* same query — use cache or re-fire */ }
  var ck = 'q_'+q.toLowerCase();
  var hit = CACHE.get(ck);
  if(hit){ _lastQ=q; cb(hit); return; }
  _st = setTimeout(function(){
    _lastQ = q;
    fetch('/search_student?q='+encodeURIComponent(q), {credentials:'same-origin'})
      .then(function(r){ return r.json(); })
      .then(function(d){
        var s = d.students||[];
        CACHE.set(ck, s, 90000);
        cb(s);
      })
      .catch(function(){ cb([]); });
  }, delay !== undefined ? delay : 120);
}
window.fastSearch = fastSearch;

/* ═══════════════════════════════════════
   4. SKELETON LOADER
═══════════════════════════════════════ */
(function(){
  var s = document.createElement('style');
  s.textContent = '@keyframes _shim{0%{background-position:200% 0}100%{background-position:-200% 0}}._sk{height:44px;margin-bottom:8px;border-radius:9px;background:linear-gradient(90deg,#f0f0f0 25%,#e8e8e8 50%,#f0f0f0 75%);background-size:200%;animation:_shim 1.2s infinite;}';
  document.head.appendChild(s);
})();
function skeleton(n){
  var h=''; for(var i=0;i<(n||4);i++) h+='<div class="_sk"></div>';
  return h;
}
window.skeleton = skeleton;

/* ═══════════════════════════════════════
   5. TOAST — instant, mobile-friendly
═══════════════════════════════════════ */
function toast(msg, type, dur){
  var c = document.getElementById('alertContainer');
  if(!c) return;
  var el = document.createElement('div');
  el.className = 'alert alert-'+(type||'success');
  el.style.cssText = 'transform:translateY(-20px);opacity:0;transition:transform .2s cubic-bezier(.34,1.56,.64,1),opacity .2s ease;will-change:transform,opacity;margin-bottom:6px;';
  el.textContent = (type==='error'?'❌ ':type==='warning'?'⚠️ ':'✅ ')+msg;
  c.appendChild(el);
  requestAnimationFrame(function(){
    requestAnimationFrame(function(){
      el.style.transform='translateY(0)';
      el.style.opacity='1';
    });
  });
  setTimeout(function(){
    el.style.transform='translateY(-10px)';
    el.style.opacity='0';
    setTimeout(function(){ el.remove(); }, 220);
  }, dur||3500);
}
window.toast    = toast;
window.showAlert = toast;

/* ═══════════════════════════════════════
   18. FEE RECEIPT
   Shows a printable receipt after a payment
   is recorded (pay_fee / pay_monthly).
═══════════════════════════════════════ */
function showReceipt(receipt, onClose){
  if(!receipt) return;

  var existing = document.getElementById('receiptOverlay');
  if(existing) existing.remove();

  var overlay = document.createElement('div');
  overlay.id = 'receiptOverlay';
  overlay.className = 'modal-overlay';
  overlay.style.display = 'flex';

  var balanceColor = receipt.new_balance <= 0 ? 'var(--success)' : 'var(--warning)';
  var balanceLabel = receipt.new_balance <= 0 ? 'PAID IN FULL' : 'Remaining Balance';

  overlay.innerHTML =
    '<div class="modal" style="max-width:380px;">'+
      '<div id="receiptPrintArea">'+
        '<div style="text-align:center;margin-bottom:16px;">'+
          '<img src="/static/images/logo.png" alt="School Logo" style="width:52px;height:52px;border-radius:50%;object-fit:cover;margin-bottom:8px;" onerror="this.style.display=\'none\'">'+
          '<div style="font-weight:900;font-size:1.05rem;color:var(--dark);">School Management System</div>'+
          '<div style="font-size:.76rem;color:var(--subtext);">Payment Receipt</div>'+
        '</div>'+
        '<div style="border-top:2px dashed #e0e0e0;border-bottom:2px dashed #e0e0e0;padding:12px 0;margin-bottom:12px;">'+
          receiptRow('Receipt No', receipt.receipt_no) +
          receiptRow('Date', receipt.date) +
          receiptRow('Student ID', receipt.student_id) +
          receiptRow('Name', receipt.student_name) +
          receiptRow('Class', formatClassName(receipt.class)) +
          receiptRow('School Year', receipt.school_year) +
          (receipt.month ? receiptRow('Month', receipt.month) : '') +
        '</div>'+
        '<div style="margin-bottom:12px;">'+
          receiptRow('Amount Paid', '$'+Number(receipt.amount).toFixed(2), true) +
          receiptRow('Total Paid', '$'+Number(receipt.new_paid).toFixed(2)) +
          receiptRow('Total Fee', '$'+Number(receipt.total_fee).toFixed(2)) +
        '</div>'+
        '<div style="background:'+(receipt.new_balance<=0?'#e8f5e9':'#fff8e1')+';border-radius:10px;padding:12px;text-align:center;margin-bottom:16px;">'+
          '<div style="font-size:.74rem;color:var(--subtext);font-weight:700;text-transform:uppercase;letter-spacing:.5px;">'+balanceLabel+'</div>'+
          (receipt.new_balance > 0 ? '<div style="font-size:1.3rem;font-weight:900;color:'+balanceColor+';">$'+Number(receipt.new_balance).toFixed(2)+'</div>' : '<div style="font-size:1.1rem;font-weight:900;color:var(--success);">✅ Fully Paid</div>')+
        '</div>'+
        '<div style="text-align:center;font-size:.7rem;color:var(--subtext);">Thank you! Keep this receipt for your records.</div>'+
      '</div>'+
      '<div style="display:flex;gap:8px;margin-top:16px;">'+
        '<button class="btn btn-primary" style="flex:1;" onclick="printReceipt()">🖨️ Print / Save PDF</button>'+
        '<button class="btn btn-danger" id="receiptCloseBtn">✖ Close</button>'+
      '</div>'+
    '</div>';

  document.body.appendChild(overlay);

  function closeReceipt(){
    overlay.remove();
    if(typeof onClose === 'function') onClose();
  }
  document.getElementById('receiptCloseBtn').addEventListener('click', closeReceipt);
  overlay.addEventListener('click', function(e){
    if(e.target === overlay) closeReceipt();
  });
}
window.showReceipt = showReceipt;

function receiptRow(label, value, highlight){
  return '<div style="display:flex;justify-content:space-between;padding:3px 0;font-size:'+(highlight?'.92rem':'.82rem')+';'+(highlight?'font-weight:800;color:var(--dark);':'color:var(--text);')+'">'+
    '<span style="color:var(--subtext);'+(highlight?'font-weight:700;':'')+'">'+label+'</span>'+
    '<span>'+value+'</span>'+
  '</div>';
}

function formatClassName(cls){
  if(cls === 'Xaddaano') return 'Xaddaano';
  if(['1','2','3','4','5','6','7','8'].indexOf(String(cls)) !== -1) return 'Class '+cls;
  return cls;
}

function printReceipt(){
  var content = document.getElementById('receiptPrintArea');
  if(!content) return;
  var win = window.open('', '_blank', 'width=400,height=600');
  win.document.write(
    '<html><head><title>Receipt</title><style>'+
    'body{font-family:Inter,system-ui,sans-serif;padding:24px;color:#212121;}'+
    'img{display:block;margin:0 auto;}'+
    '@media print{body{padding:0;}}'+
    '</style></head><body>'+content.innerHTML+'</body></html>'
  );
  win.document.close();
  win.focus();
  setTimeout(function(){ win.print(); }, 300);
}
window.printReceipt = printReceipt;

/* ═══════════════════════════════════════
   19. PRINT REPORT
   Prints the #printArea element with a
   School header, using browser native print
   (works for "Save as PDF" too).
═══════════════════════════════════════ */
function printPage(reportTitle){
  var area = document.getElementById('printArea');
  if(!area){ toast('Nothing to print on this page', 'warning'); return; }

  var win = window.open('', '_blank');
  var now = new Date().toLocaleString();

  win.document.write(
    '<html><head><title>'+(reportTitle||'Report')+'</title><style>'+
    'body{font-family:Inter,system-ui,sans-serif;padding:20px;color:#212121;}'+
    'table{width:100%;border-collapse:collapse;font-size:.8rem;}'+
    'th,td{padding:6px 8px;border:1px solid #ddd;text-align:left;}'+
    'th{background:#1565C0;color:white;}'+
    '.print-header{text-align:center;margin-bottom:18px;}'+
    '.print-header img{width:48px;height:48px;border-radius:50%;margin-bottom:6px;}'+
    '.print-header h1{font-size:1.1rem;margin:4px 0;}'+
    '.print-header p{font-size:.78rem;color:#757575;margin:0;}'+
    '@media print{ @page{ margin:1cm; } }'+
    '</style></head><body>'+
    '<div class="print-header">'+
      '<img src="/static/images/logo.png" onerror="this.style.display=\'none\'">'+
      '<h1>School Management System</h1>'+
      '<p>'+(reportTitle||'Report')+' — Generated '+now+'</p>'+
    '</div>'+
    area.innerHTML+
    '</body></html>'
  );
  win.document.close();
  win.focus();
  setTimeout(function(){ win.print(); }, 350);
}
window.printPage = printPage;

/* ═══════════════════════════════════════
   6. SIDEBAR — GPU transform
═══════════════════════════════════════ */
function toggleSidebar(){
  var s = document.getElementById('sidebar');
  var o = document.getElementById('sidebarOverlay');
  var m = document.getElementById('mainContent');
  if(!s) return;
  if(window.innerWidth <= 768){
    var isOpen = s.classList.toggle('mobile-open');
    if(o) o.classList.toggle('active', isOpen);
    // Lock body scroll when sidebar open on mobile
    document.body.style.overflow = isOpen ? 'hidden' : '';
  } else {
    var col = s.classList.toggle('collapsed');
    if(m) m.classList.toggle('expanded', col);
  }
}
function closeSidebar(){
  var s=document.getElementById('sidebar'), o=document.getElementById('sidebarOverlay');
  if(s) s.classList.remove('mobile-open');
  if(o) o.classList.remove('active');
  document.body.style.overflow = '';
}
window.toggleSidebar = toggleSidebar;
window.closeSidebar  = closeSidebar;

/* ═══════════════════════════════════════
   7. MODAL — bottom sheet on mobile
═══════════════════════════════════════ */
function openModal(id){
  var el=document.getElementById(id);
  if(!el) return;
  el.style.display='flex';
  document.body.style.overflow='hidden';
  // Animate in
  var m = el.querySelector('.modal');
  if(m){
    m.style.transform = 'translateY(40px)';
    m.style.opacity   = '0';
    m.style.transition= 'transform .22s cubic-bezier(.34,1.56,.64,1), opacity .18s ease';
    requestAnimationFrame(function(){
      requestAnimationFrame(function(){
        m.style.transform = 'translateY(0)';
        m.style.opacity   = '1';
      });
    });
  }
}
function closeModal(id){
  var el=document.getElementById(id);
  if(!el) return;
  var m = el.querySelector('.modal');
  if(m){
    m.style.transform = 'translateY(40px)';
    m.style.opacity   = '0';
    setTimeout(function(){ el.style.display='none'; document.body.style.overflow=''; }, 200);
  } else {
    el.style.display='none';
    document.body.style.overflow='';
  }
}
window.openModal  = openModal;
window.closeModal = closeModal;

/* ═══════════════════════════════════════
   8. OPTIMISTIC SAVE — instant UI update
   Invalidates cache, shows spinner
═══════════════════════════════════════ */
function optimisticSave(url, data, onOk, onErr, btn, loadTxt){
  var orig = btn ? btn.innerHTML : '';
  if(btn){
    btn.innerHTML = '<span class="spinner"></span>'+(loadTxt?' '+loadTxt:'');
    btn.disabled  = true;
    btn.style.opacity = '.75';
    btn.style.pointerEvents = 'none';
  }
  // Invalidate all write-sensitive caches
  CACHE.del('q_');
  CACHE.del('students');
  fetch(url, {
    method:  'POST',
    headers: {'Content-Type':'application/json'},
    body:    JSON.stringify(data),
    credentials: 'same-origin'
  })
  .then(function(r){ return r.json(); })
  .then(function(d){
    if(btn){ btn.innerHTML=orig; btn.disabled=false; btn.style.opacity=''; btn.style.pointerEvents=''; }
    if(d.success){ if(onOk) onOk(d); }
    else          { if(onErr) onErr(d); }
  })
  .catch(function(){
    if(btn){ btn.innerHTML=orig; btn.disabled=false; btn.style.opacity=''; btn.style.pointerEvents=''; }
    if(onErr) onErr({message:'Connection failed — please try again'});
  });
}
window.optimisticSave = optimisticSave;

/* ═══════════════════════════════════════
   9. PAGE TRANSITION — 70ms fade
═══════════════════════════════════════ */
var _navLock = false;
function navTo(url){
  if(_navLock) return;
  _navLock = true;
  var pc = document.querySelector('.page-content');
  if(pc){
    pc.style.transition = 'opacity .07s ease';
    pc.style.opacity    = '0';
  }
  setTimeout(function(){ window.location.href = url; }, 70);
}
window.navTo = navTo;

/* ═══════════════════════════════════════
   10. RIPPLE — GPU composite, 0 delay
═══════════════════════════════════════ */
(function(){
  var s = document.createElement('style');
  s.textContent='@keyframes _rpl{to{transform:scale(2.8);opacity:0;}}';
  document.head.appendChild(s);
})();
function addRipple(el){
  el.addEventListener('touchstart', function(e){
    var r   = document.createElement('span');
    var rc  = el.getBoundingClientRect();
    var t   = e.touches[0];
    var sz  = Math.max(rc.width, rc.height);
    r.style.cssText=[
      'position:absolute','border-radius:50%',
      'background:rgba(255,255,255,.28)','pointer-events:none',
      'width:'+sz+'px','height:'+sz+'px',
      'left:'+(t.clientX-rc.left-sz/2)+'px',
      'top:'+(t.clientY-rc.top-sz/2)+'px',
      'transform:scale(0)',
      'animation:_rpl .5s linear',
      'z-index:1'
    ].join(';');
    el.style.position='relative';
    el.style.overflow='hidden';
    el.appendChild(r);
    setTimeout(function(){ r.remove(); }, 550);
  }, {passive:true});
  el.addEventListener('click', function(e){
    if(e.sourceCapabilities && e.sourceCapabilities.firesTouchEvents) return;
    var r   = document.createElement('span');
    var rc  = el.getBoundingClientRect();
    var sz  = Math.max(rc.width, rc.height);
    r.style.cssText=[
      'position:absolute','border-radius:50%',
      'background:rgba(255,255,255,.28)','pointer-events:none',
      'width:'+sz+'px','height:'+sz+'px',
      'left:'+(e.clientX-rc.left-sz/2)+'px',
      'top:'+(e.clientY-rc.top-sz/2)+'px',
      'transform:scale(0)',
      'animation:_rpl .5s linear',
      'z-index:1'
    ].join(';');
    el.style.position='relative';
    el.style.overflow='hidden';
    el.appendChild(r);
    setTimeout(function(){ r.remove(); }, 550);
  }, {passive:true});
}

/* ═══════════════════════════════════════
   11. PREFETCH students in background
═══════════════════════════════════════ */
function prefetch(){
  if(CACHE.has('q_cs')) return;
  setTimeout(function(){
    fetch('/search_student?q=cs',{credentials:'same-origin'})
      .then(function(r){ return r.json(); })
      .then(function(d){ if(d.students) CACHE.set('q_cs', d.students, 90000); })
      .catch(function(){});
  }, 600);
}

/* ═══════════════════════════════════════
   12. VOTE SUBMIT — instant feedback
   Prevents double-tap double-vote
═══════════════════════════════════════ */
var _voteInProgress = false;
function submitVote(candidateId, btn){
  if(_voteInProgress) return;
  if(!candidateId){ toast('Please select a candidate!', 'warning'); return; }
  _voteInProgress = true;
  var orig = btn ? btn.innerHTML : '';
  if(btn){
    btn.innerHTML = '<span class="spinner"></span> Submitting vote...';
    btn.disabled  = true;
  }
  fetch('/submit_vote', {
    method:  'POST',
    headers: {'Content-Type':'application/json'},
    body:    JSON.stringify({candidate_id: candidateId}),
    credentials: 'same-origin'
  })
  .then(function(r){ return r.json(); })
  .then(function(d){
    if(d.success){
      toast(d.message || 'Your vote has been recorded! 🎉', 'success', 4000);
      CACHE.del('votes');
      setTimeout(function(){ window.location.reload(); }, 1200);
    } else {
      toast(d.message || 'Khalad dhacay', 'error');
      if(btn){ btn.innerHTML=orig; btn.disabled=false; }
      _voteInProgress = false;
    }
  })
  .catch(function(){
    toast('Connection failed — please try again', 'error');
    if(btn){ btn.innerHTML=orig; btn.disabled=false; }
    _voteInProgress = false;
  });
}
window.submitVote = submitVote;

/* ═══════════════════════════════════════
   13. INIT
═══════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', function(){

  /* a. Hide page loader */
  hidePageLoader();

  /* a2. Set dark mode icon */
  updateThemeIcon();

  /* a. Page fade-in */
  var pc = document.querySelector('.page-content');
  if(pc){
    pc.style.opacity   = '0';
    pc.style.transform = 'translate3d(0,8px,0)';
    pc.style.transition= 'opacity .18s ease, transform .18s ease';
    pc.style.willChange= 'opacity,transform';
    requestAnimationFrame(function(){
      requestAnimationFrame(function(){
        pc.style.opacity   = '1';
        pc.style.transform = 'translate3d(0,0,0)';
      });
    });
  }

  /* b. Ripple on all interactive elements */
  document.querySelectorAll('.btn,.action-btn,.role-btn,.login-btn,.stat-card').forEach(addRipple);

  /* c. Modal overlay click-to-close */
  document.querySelectorAll('.modal-overlay').forEach(function(o){
    o.addEventListener('click', function(e){
      if(e.target===o) closeModal(o.id);
    });
  });

  /* d. Swipe down to close modal on mobile */
  document.querySelectorAll('.modal').forEach(function(m){
    var startY = 0, isDragging = false;
    m.addEventListener('touchstart', function(e){
      if(m.scrollTop > 0) return;
      startY = e.touches[0].clientY;
      isDragging = true;
    }, {passive:true});
    m.addEventListener('touchmove', function(e){
      if(!isDragging) return;
      var dy = e.touches[0].clientY - startY;
      if(dy > 0) m.style.transform = 'translateY('+Math.min(dy,120)+'px)';
    }, {passive:true});
    m.addEventListener('touchend', function(e){
      if(!isDragging) return;
      isDragging = false;
      var dy = e.changedTouches[0].clientY - startY;
      if(dy > 80){
        var ov = m.closest('.modal-overlay');
        if(ov) closeModal(ov.id);
      } else {
        m.style.transform = '';
      }
    }, {passive:true});
  });

  /* e. Smooth nav */
  document.querySelectorAll('a.nav-item[href]').forEach(function(a){
    if(!a.href || a.href.includes('logout') || a.href.includes('#')) return;
    a.addEventListener('mouseenter', function(){
      var l=document.createElement('link'); l.rel='prefetch'; l.href=a.href;
      document.head.appendChild(l);
    }, {once:true});
    a.addEventListener('click', function(e){
      if(e.ctrlKey||e.metaKey||e.shiftKey) return;
      e.preventDefault();
      closeSidebar();
      document.querySelectorAll('.nav-item').forEach(function(n){ n.classList.remove('active'); });
      a.classList.add('active');
      navTo(a.href);
    });
  });

  /* f. ESC closes modals */
  document.addEventListener('keydown', function(e){
    if(e.key==='Escape'){
      document.querySelectorAll('.modal-overlay').forEach(function(o){
        if(o.style.display!=='none') closeModal(o.id);
      });
    }
  });

  /* g. Instant tactile feedback on touch */
  document.addEventListener('touchstart', function(e){
    var el = e.target.closest('button,.btn,.action-btn,.stat-card');
    if(!el||el.disabled) return;
    el.style.transition = 'transform .08s ease,opacity .08s ease';
    el.style.transform  = 'scale(.95)';
    el.style.opacity    = '.85';
  }, {passive:true});
  document.addEventListener('touchend', function(e){
    var el = e.target.closest('button,.btn,.action-btn,.stat-card');
    if(!el) return;
    el.style.transform = '';
    el.style.opacity   = '';
  }, {passive:true});

  /* h. Preconnect */
  ['https://sheets.googleapis.com','https://fonts.googleapis.com'].forEach(function(h){
    var l=document.createElement('link'); l.rel='preconnect'; l.href=h;
    document.head.appendChild(l);
  });

  /* i. Prefetch students */
  prefetch();

  /* j. Fix viewport width on mobile resize */
  function fixVP(){
    var mw=document.getElementById('mainContent');
    if(mw && window.innerWidth<=768){
      mw.style.width='100vw'; mw.style.maxWidth='100vw';
    }
  }
  window.addEventListener('resize', fixVP, {passive:true});
  fixVP();

  /* k. Prevent double-submit on all forms */
  document.querySelectorAll('form').forEach(function(f){
    var _submitted = false;
    f.addEventListener('submit', function(e){
      if(_submitted){ e.preventDefault(); return; }
      _submitted = true;
      setTimeout(function(){ _submitted=false; }, 5000);
    });
  });

  /* l. Auto-close sidebar on nav click (mobile) */
  document.querySelectorAll('.nav-item').forEach(function(item){
    item.addEventListener('click', function(){
      if(window.innerWidth <= 768) closeSidebar();
    });
  });
});

/* ═══════════════════════════════════════
   17. DARK MODE
   Applied immediately (before DOMContentLoaded)
   to avoid a flash of light theme.
═══════════════════════════════════════ */
(function(){
  try{
    var saved = localStorage.getItem('theme');
    var theme = saved || 'light';
    if(theme === 'dark'){
      document.documentElement.setAttribute('data-theme', 'dark');
    }
  }catch(e){}
})();

var _themeLock = false;
function toggleTheme(){
  if(_themeLock) return;
  _themeLock = true;
  setTimeout(function(){ _themeLock = false; }, 400);

  var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  var next = isDark ? 'light' : 'dark';
  if(next === 'dark'){
    document.documentElement.setAttribute('data-theme', 'dark');
  } else {
    document.documentElement.removeAttribute('data-theme');
  }
  try{ localStorage.setItem('theme', next); }catch(e){}
  updateThemeIcon();
}
window.toggleTheme = toggleTheme;

function updateThemeIcon(){
  var icon = document.getElementById('themeIcon');
  if(!icon) return;
  var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  icon.textContent = isDark ? '☀️' : '🌙';
}

/* Preconnect before DOMContentLoaded */
(function(){
  ['https://sheets.googleapis.com','https://fonts.googleapis.com'].forEach(function(h){
    var l=document.createElement('link'); l.rel='preconnect'; l.href=h;
    document.head.appendChild(l);
  });
})();

/* ═══════════════════════════════════════
   16. PUSH NOTIFICATIONS
   Subscribes the device to receive OS-level
   notifications (school logo + name), like
   WhatsApp/Facebook.
═══════════════════════════════════════ */
function urlBase64ToUint8Array(base64String){
  var padding = '='.repeat((4 - base64String.length % 4) % 4);
  var base64  = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  var raw     = window.atob(base64);
  var arr     = new Uint8Array(raw.length);
  for(var i=0; i<raw.length; i++) arr[i] = raw.charCodeAt(i);
  return arr;
}

/* ═══════════════════════════════════════
   PUSH NOTIFICATIONS — FIXED
   - initPushNotifications: silent state sync only, NO toasts
   - toggleNotifications: user-initiated only, single toast
   - subscribeToPush: calls callback with result
   - No double-fire protection via _notifLock
═══════════════════════════════════════ */
var _notifLock = false; // prevent double-tap double-call

function initPushNotifications(){
  /* SILENT — only syncs the toggle UI with real subscription state.
     Never shows toasts. Never subscribes automatically. */
  if(!('serviceWorker' in navigator) || !('PushManager' in window)) return;
  if(!('Notification' in window)) return;

  navigator.serviceWorker.ready.then(function(reg){
    reg.pushManager.getSubscription().then(function(existingSub){
      updateNotifToggleUI(!!existingSub);
      // Silently re-sync to server if already subscribed (no toast)
      if(existingSub) sendSubscriptionToServer(existingSub);
    });
  }).catch(function(){/* silent */});
}

function updateNotifToggleUI(isOn){
  document.querySelectorAll('.notif-toggle').forEach(function(t){
    t.classList.toggle('on', isOn);
    var icon = t.querySelector('.notif-icon');
    if(icon) icon.textContent = isOn ? '🔔' : '🔕';
  });
}

function toggleNotifications(){
  /* Guard against double-tap */
  if(_notifLock) return;
  _notifLock = true;
  setTimeout(function(){ _notifLock = false; }, 2000);

  if(!('serviceWorker' in navigator) || !('PushManager' in window) || !('Notification' in window)){
    toast('Push notifications not supported on this device', 'warning');
    _notifLock = false;
    return;
  }

  navigator.serviceWorker.ready.then(function(reg){
    reg.pushManager.getSubscription().then(function(existingSub){
      if(existingSub){
        /* ── Currently ON → turn OFF ── */
        var endpoint = existingSub.endpoint;
        existingSub.unsubscribe().then(function(success){
          _notifLock = false;
          updateNotifToggleUI(false);
          toast('Notifications turned off', 'success');
          fetch('/remove_subscription',{
            method:'POST',
            headers:{'Content-Type':'application/json'},
            credentials:'same-origin',
            body:JSON.stringify({endpoint:endpoint})
          }).catch(function(){});
        }).catch(function(){
          _notifLock = false;
          toast('Could not turn off notifications', 'error');
        });
      } else {
        /* ── Currently OFF → turn ON ── */
        if(Notification.permission === 'denied'){
          _notifLock = false;
          toast('Notifications are blocked — enable them in browser settings', 'warning', 5000);
          updateNotifToggleUI(false);
          return;
        }
        Notification.requestPermission().then(function(perm){
          if(perm !== 'granted'){
            _notifLock = false;
            updateNotifToggleUI(false);
            /* Only show toast if user actively denied (not just dismissed) */
            if(perm === 'denied') toast('Notifications blocked by browser', 'warning');
            return;
          }
          subscribeToPush(reg, function(success){
            _notifLock = false;
            updateNotifToggleUI(success);
            /* Single toast — success or failure, never duplicated */
            if(success){
              toast('Notifications enabled 🔔', 'success');
            } else {
              toast('Could not enable notifications — check browser settings', 'warning', 4000);
            }
          });
        }).catch(function(){
          _notifLock = false;
          updateNotifToggleUI(false);
        });
      }
    });
  }).catch(function(){
    _notifLock = false;
    toast('Connection error — please try again', 'error');
  });
}
window.toggleNotifications = toggleNotifications;

function subscribeToPush(reg, callback){
  fetch('/vapid_public_key', {credentials:'same-origin'})
    .then(function(r){ return r.json(); })
    .then(function(d){
      if(!d.enabled || !d.publicKey) throw new Error('Server push not configured');
      return reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(d.publicKey)
      });
    })
    .then(function(sub){
      sendSubscriptionToServer(sub);
      if(callback) callback(true);
    })
    .catch(function(){
      if(callback) callback(false);
    });
}

function sendSubscriptionToServer(sub){
  fetch('/save_subscription',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    credentials:'same-origin',
    body:JSON.stringify({subscription: sub.toJSON ? sub.toJSON() : sub})
  }).catch(function(){});
}

// Initialize on load — SILENT, no toasts, no auto-subscribe
document.addEventListener('DOMContentLoaded', function(){
  try{ initPushNotifications(); }catch(e){}


  /* Unsubscribe push on logout — prevents next user on this device
     from receiving the previous user's notifications */
  document.querySelectorAll('a.logout-btn').forEach(function(a){
    a.addEventListener('click', function(e){
      if(!('serviceWorker' in navigator)) return; // let normal nav happen
      e.preventDefault();
      var target = a.href;
      navigator.serviceWorker.ready
        .then(function(reg){ return reg.pushManager.getSubscription(); })
        .then(function(sub){
          if(!sub) return;
          var endpoint = sub.endpoint;
          return sub.unsubscribe().then(function(){
            return fetch('/remove_subscription', {
              method:'POST',
              headers:{'Content-Type':'application/json'},
              credentials:'same-origin',
              body: JSON.stringify({endpoint: endpoint})
            });
          });
        })
        .catch(function(){})
        .finally(function(){ window.location.href = target; });
    });
  });
});
