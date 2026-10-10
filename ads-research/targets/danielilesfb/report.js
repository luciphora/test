(function(){
  var q=document.getElementById('txq'), st=document.getElementById('txst'), co=document.getElementById('txco'),
      list=document.getElementById('txlist'), count=document.getElementById('txcount');
  if(!q||!st||!co||!list||!count) return;
  var items=[].slice.call(list.querySelectorAll('.tx'));
  // Cohort options come from the rendered transcripts, so the filter never offers an empty bucket.
  var seen={};
  items.forEach(function(el){ seen[el.dataset.c]=1; });
  Object.keys(seen).sort().forEach(function(c){
    var o=document.createElement('option'); o.value=c; o.textContent=c; co.appendChild(o); });
  items.forEach(function(el){ el._p=el.querySelector('p'); el._raw=el._p.textContent;
                              el._t=el._raw.toLowerCase(); });
  function rx(t){ return t.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'); }
  function esc(t){ return t.replace(/[&<>]/g,function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;'}[c]; }); }
  function run(){
    var term=q.value.trim().toLowerCase(), s=st.value, c=co.value, shown=0;
    var re=term?new RegExp('('+rx(term)+')','ig'):null;
    items.forEach(function(el){
      var hit=(!term||el._t.indexOf(term)>-1)&&(!s||el.dataset.s===s)&&(!c||el.dataset.c===c);
      el.hidden=!hit;
      if(hit){ shown++; el._p.innerHTML=re?esc(el._raw).replace(re,'<mark>$1</mark>'):esc(el._raw); }
    });
    count.textContent=shown+' of '+items.length;
  }
  [q,st,co].forEach(function(el){ el.addEventListener('input',run); el.addEventListener('change',run); });
  run();
})();
