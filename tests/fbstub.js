(function(){
  const docs={}; const subs={};
  let user=null; const authCbs=[];
  const notifyAuth=()=>authCbs.forEach(cb=>setTimeout(()=>cb(user),0));
  const authObj={
    get currentUser(){return user;},
    onAuthStateChanged(cb){authCbs.push(cb); setTimeout(()=>cb(user),0); return ()=>{};},
    signInWithPopup(){ user=window.__fakeUser; notifyAuth(); return Promise.resolve({user}); },
    signInWithRedirect(){ return this.signInWithPopup(); },
    getRedirectResult(){ return Promise.resolve(null); },
    signOut(){ user=null; notifyAuth(); return Promise.resolve(); }
  };
  function snap(id){ const d=docs[id]; return {exists:!!d, data:()=>d&&JSON.parse(JSON.stringify(d))}; }
  function emit(id){ (subs[id]||[]).forEach(cb=>setTimeout(()=>cb(snap(id)),0)); }
  function ref(c,id){ const key=c+'/'+id; return {
    key, get(){ return Promise.resolve(snap(key)); },
    set(v){ docs[key]=JSON.parse(JSON.stringify(v)); emit(key); return Promise.resolve(); },
    onSnapshot(cb){ (subs[key]=subs[key]||[]).push(cb); setTimeout(()=>cb(snap(key)),0); return ()=>{ subs[key]=subs[key].filter(x=>x!==cb); }; }
  };}
  const db={ collection:c=>({doc:id=>ref(c,id)}),
    async runTransaction(fn){ const pend=[]; const tx={get:r=>r.get(), set:(r,v)=>pend.push([r,v])}; await fn(tx); pend.forEach(([r,v])=>r.set(v)); } };
  const auth=()=>authObj; auth.GoogleAuthProvider=function(){ this.setCustomParameters=()=>{}; };
  window.firebase={ initializeApp(){}, auth, firestore:()=>db };
  window.__fbdocs=docs;
})();
