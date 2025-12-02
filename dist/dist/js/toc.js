// Simple scroll-spy for TOC: adds .active to the current category link
(function(){
  function idxSections(){
    return Array.from(document.querySelectorAll('main .category-section')).map(s=>{
      return {id: s.id, top: s.getBoundingClientRect().top + window.scrollY};
    });
  }

  function onScroll(){
    const sections = idxSections();
    const y = window.scrollY + 80; // offset for header
    let current = sections[0] && sections[0].id;
    for(const s of sections){
      if(y >= s.top) current = s.id;
    }
    document.querySelectorAll('.toc a').forEach(a=> a.classList.toggle('active', a.getAttribute('href') === '#'+current));
  }

  document.addEventListener('DOMContentLoaded', function(){
    // smooth scrolling on toc click
    document.querySelectorAll('.toc a').forEach(a=>{
      a.addEventListener('click', function(e){
        e.preventDefault();
        const id = this.getAttribute('href').slice(1);
        const el = document.getElementById(id);
        if(el) window.scrollTo({top: el.getBoundingClientRect().top + window.scrollY - 60, behavior:'smooth'});
      });
    });
    onScroll();
    window.addEventListener('scroll', onScroll, {passive:true});
    window.addEventListener('resize', onScroll);
  });
})();
