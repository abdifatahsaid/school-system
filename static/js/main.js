
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
    if(onErr) onErr({message:'Xiriirka kama jaro — mar kale isku day'});
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
  if(!candidateId){ toast('Musharaxa dooro!', 'warning'); return; }
  _voteInProgress = true;
  var orig = btn ? btn.innerHTML : '';
  if(btn){
    btn.innerHTML = '<span class="spinner"></span> Codbixinaya...';
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
      toast(d.message || 'Codkaagii la diiwaan-geliyay! 🎉', 'success', 4000);
      CACHE.del('votes');
      setTimeout(function(){ window.location.reload(); }, 1200);
    } else {
      toast(d.message || 'Khalad dhacay', 'error');
      if(btn){ btn.innerHTML=orig; btn.disabled=false; }
      _voteInProgress = false;
    }
  })
  .catch(function(){
    toast('Xiriirka kama jaro — mar kale isku day', 'error');
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

/* Preconnect before DOMContentLoaded */
(function(){
  ['https://sheets.googleapis.com','https://fonts.googleapis.com'].forEach(function(h){
    var l=document.createElement('link'); l.rel='preconnect'; l.href=h;
    document.head.appendChild(l);
  });
})();
