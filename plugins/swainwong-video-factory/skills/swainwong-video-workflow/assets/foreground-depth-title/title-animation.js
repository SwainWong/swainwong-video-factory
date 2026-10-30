// Deterministic title entrances. All geometry comes from the already-typeset title,
// never from the foreground subject. Call only after fonts/layout are ready.
export const TITLE_EFFECTS = Object.freeze([
  {type:'heavy-drop',label:'沉重掉落'},
  {type:'fragments',label:'碎片重组'},
  {type:'spring',label:'弹性弹入'},
  {type:'grapheme-reveal',label:'逐字显影'},
  {type:'light-wipe',label:'光幕扫入'},
  {type:'ink-reveal',label:'墨迹显现'},
  {type:'side-slide',label:'侧向滑入'},
  {type:'flip-open',label:'翻转展开'},
  {type:'depth-push',label:'纵深推进'},
  {type:'blur-focus',label:'模糊聚焦'}
]);
const aliases={'shard-rebuild':'fragments','elastic-pop':'spring','letter-reveal':'grapheme-reveal','slide-in':'side-slide'};
const clamp=(x,a=0,b=1)=>Math.max(a,Math.min(b,x));
const out=p=>1-Math.pow(1-clamp(p),3);
const smooth=p=>{p=clamp(p);return p*p*(3-2*p);};
function seeded(seed){let n=(Number(seed)||1997)>>>0;return()=>{n=(Math.imul(n,1664525)+1013904223)>>>0;return n/4294967296;};}
function reset(node){
  Object.assign(node.style,{opacity:'0',transform:'none',transformOrigin:'50% 50%',filter:'none',clipPath:'none',maskImage:'none',webkitMaskImage:'none',maskSize:'auto',webkitMaskSize:'auto',maskPosition:'0 0',webkitMaskPosition:'0 0',maskRepeat:'no-repeat',webkitMaskRepeat:'no-repeat',backfaceVisibility:'visible'});
}
function setMask(node,images,sizes,positions){
  const s=node.style;
  s.maskImage=s.webkitMaskImage=images.join(',');
  s.maskSize=s.webkitMaskSize=sizes.join(',');
  s.maskPosition=s.webkitMaskPosition=positions.join(',');
  s.maskRepeat=s.webkitMaskRepeat='no-repeat';
}
function finite(value,fallback){return Number.isFinite(Number(value))?Number(value):fallback;}

/**
 * config: {cues:[{type,label,at,until,enterDuration,exitDuration,seed, ...}]}
 * All times are seconds local to the configured scene. `duration` aliases
 * enterDuration. `at` omitted uses frame's anchor argument. until defaults to
 * the next cue or sceneDuration. Visual clones remain before #foreground.
 */
export function createTitleAnimation({element,config={},labelElement=null,sceneDuration=5}){
  if(!element?.parentElement)throw Error('Title animation needs an attached, typeset title element.');
  const text=element.textContent;
  const width=element.offsetWidth,height=element.offsetHeight;
  if(!(width>0&&height>0))throw Error('Title animation must be created after font/layout measurement.');
  const parent=element.parentElement;
  const foreground=parent.querySelector('#foreground');
  if(foreground && !(element.compareDocumentPosition(foreground)&Node.DOCUMENT_POSITION_FOLLOWING))throw Error('Title must precede foreground in the layer stack.');
  const baseRect=element.getBoundingClientRect();
  const clones=[];
  function clone(kind){
    const n=element.cloneNode(true);
    n.removeAttribute('id');n.removeAttribute('aria-label');n.setAttribute('aria-hidden','true');
    n.dataset.titleEffectClone=kind;
    Object.assign(n.style,{pointerEvents:'none',zIndex:'auto',position:'absolute'});
    // Immediate sibling insertion is deliberately below the foreground canvas.
    parent.insertBefore(n,element.nextSibling);reset(n);clones.push(n);return n;
  }
  const cues=(config.cues?.length?config.cues:[config]).map((c,i)=>{
    const type=aliases[c.type]||c.type||'spring';
    const known=TITLE_EFFECTS.find(e=>e.type===type);
    if(!known)throw Error(`Unknown title effect: ${type}`);
    const enterDuration=finite(c.enterDuration??c.duration,.85);
    if(!(enterDuration>0))throw Error(`Cue ${i}: enterDuration must be positive.`);
    for(const [key,css] of [['highlightColor','color'],['highlightShadow','text-shadow']])if(c[key]!=null&&!CSS.supports(css,String(c[key])))throw Error(`Cue ${i}: invalid ${key}`);
    return {...c,type,label:c.label||known.label,at:c.at==null?null:finite(c.at,0),enterDuration,exitDuration:Math.max(0,finite(c.exitDuration,.16)),seed:finite(c.seed,1997+i*101)};
  });
  const explicit=cues.filter(c=>c.at!=null);
  for(let i=1;i<explicit.length;i++)if(explicit[i].at<=explicit[i-1].at)throw Error('Title cues must have strictly increasing at values.');
  // Grapheme geometry is measured on the original single node. Range offsets
  // are UTF-16 indices supplied by Intl.Segmenter, preserving original shaping.
  const graphemes=[];
  const warnings=[];
  if(cues.some(c=>c.type==='grapheme-reveal')){
    if(!Intl.Segmenter)throw Error('grapheme-reveal requires Intl.Segmenter; no unsafe code-point fallback is used.');
    if(element.childNodes.length!==1||element.firstChild.nodeType!==Node.TEXT_NODE)throw Error('grapheme-reveal requires the canonical single text node.');
    const segments=[...new Intl.Segmenter(element.lang||undefined,{granularity:'grapheme'}).segment(text)];
    for(const s of segments){
      if(/^\s+$/u.test(s.segment))continue;
      const range=document.createRange();range.setStart(element.firstChild,s.index);range.setEnd(element.firstChild,s.index+s.segment.length);
      const rects=[...range.getClientRects()].map(r=>({x:r.left-baseRect.left-2,y:r.top-baseRect.top-3,w:r.width+4,h:r.height+27}));
      if(rects.length)graphemes.push({text:s.segment,index:s.index,rects});
      range.detach();
    }
    if(!graphemes.length)warnings.push('No non-whitespace graphemes to reveal.');
  }
  const fragments=[];
  if(cues.some(c=>c.type==='fragments')){
    // Twenty triangular pieces tile the complete typeset surface, not words.
    const cols=5,rows=2;
    for(let y=0;y<rows;y++)for(let x=0;x<cols;x++)for(let tri=0;tri<2;tri++){
      const x0=x/cols*100,x1=(x+1)/cols*100,y0=y/rows*100,y1=(y+1)/rows*100;
      const points=tri===0?[[x0,y0],[x1,y0],[x1,y1]]:[[x0,y0],[x1,y1],[x0,y1]];
      fragments.push({node:clone('fragment'),polygon:`polygon(${points.map(p=>p.join('% ')+'%').join(',')})`,x:(x+.5)/cols,y:(y+.5)/rows,index:fragments.length});
    }
  }
  const sheen=cues.some(c=>c.type==='light-wipe')?clone('sheen'):null;
  const metrics={effects:cues.map(c=>c.type),labels:cues.map(c=>c.label),textPreserved:element.textContent===text,width,height,graphemeCount:graphemes.length,fragmentCount:fragments.length,warnings,currentCue:null,progress:0};
  let disposed=false;
  function frame(t,anchor=0){
    if(disposed)throw Error('Title animator is disposed.');
    reset(element);for(const n of clones)reset(n);
    if(t>=sceneDuration){if(labelElement)labelElement.style.opacity='0';metrics.currentCue=null;return metrics;}
    if(element.textContent!==text)throw Error('Title text changed after animation initialization; recreate the animator after re-layout.');
    const starts=cues.map(c=>c.at==null?anchor:c.at);
    let ci=-1;for(let i=0;i<cues.length;i++)if(t>=starts[i])ci=i;
    if(ci<0){if(labelElement){labelElement.textContent=cues[0].label;labelElement.style.opacity='0';}metrics.currentCue=null;return metrics;}
    const c=cues[ci],at=starts[ci],until=finite(c.until,starts[ci+1]??sceneDuration);
    const elapsed=t-at,p=clamp(elapsed/c.enterDuration);
    const leave=c.exitDuration>0?1-smooth((t-(until-c.exitDuration))/c.exitDuration):(t<until?1:0);
    metrics.currentCue=ci;metrics.type=c.type;metrics.progress=p;metrics.at=at;metrics.until=until;
    if(labelElement){labelElement.textContent=c.label;labelElement.style.opacity=String(clamp(elapsed/.08)*leave);}
    if(t>=until||t<at)return metrics;
    // Every completed entrance uses exactly the original typeset title.
    if(p>=1){element.style.opacity=String(leave);return metrics;}
    const e=out(p);element.style.opacity=String(leave);
    switch(c.type){
      case 'heavy-drop': {
        const impact=.62;let y=0,x=0,sx=1,sy=1,rot=0;
        if(p<impact){const fall=p/impact;y=-finite(c.distance,440)*(1-fall*fall);}
        else {const q=(p-impact)/(1-impact),decay=Math.exp(-5*q);y=-31*Math.sin(Math.PI*q)*decay;sx=1+.12*Math.exp(-14*q);sy=1-.19*Math.exp(-14*q);x=7*Math.sin(q*36)*decay;rot=.6*Math.sin(q*29)*decay;}
        element.style.transformOrigin='50% 88%';element.style.transform=`translate(${x}px,${y}px) rotate(${rot}deg) scale(${sx},${sy})`;element.style.opacity=String(clamp(p/.05)*leave);break;
      }
      case 'fragments': {
        element.style.opacity='0';const rand=seeded(c.seed);
        for(const f of fragments){
          const delay=rand()*.18,q=clamp((p-delay)/(1-delay)),r=out(q);
          const dx=(f.x-.5)*finite(c.scatter,630)+(rand()-.5)*190,dy=(f.y-.5)*360+(rand()-.5)*220,angle=(rand()-.5)*88;
          f.node.style.clipPath=f.polygon;f.node.style.transform=`translate(${dx*(1-r)}px,${dy*(1-r)}px) rotate(${angle*(1-r)}deg)`;
          f.node.style.opacity=String(smooth(q/.24)*leave);f.node.style.filter=`blur(${(1-r)*1.5}px)`;
        }break;
      }
      case 'spring': {
        const s=1-.78*Math.exp(-6.8*p)*Math.cos(12.5*p),rot=5*Math.sin(p*10)*Math.exp(-5*p);
        element.style.transform=`scale(${s}) rotate(${rot}deg)`;element.style.opacity=String(clamp(p/.1)*leave);break;
      }
      case 'grapheme-reveal': {
        const images=[],sizes=[],positions=[],count=Math.max(1,graphemes.length);
        for(let i=0;i<graphemes.length;i++){
          const a=clamp((p-i/count*.77)/.23);
          for(const r of graphemes[i].rects){images.push(`linear-gradient(rgba(0,0,0,${a}),rgba(0,0,0,${a}))`);sizes.push(`${r.w}px ${r.h}px`);positions.push(`${r.x}px ${r.y}px`);}
        }
        if(images.length)setMask(element,images,sizes,positions);break;
      }
      case 'light-wipe': {
        const edge=e*width;const rtl=getComputedStyle(element).direction==='rtl';
        element.style.clipPath=rtl?`inset(0 0 0 ${100*(1-e)}%)`:`inset(0 ${100*(1-e)}% 0 0)`;
        if(sheen){sheen.style.color=c.highlightColor??'#fff5c3';sheen.style.textShadow=c.highlightShadow??'0 0 22px #ffe9a8,0 0 42px #fff9';const x=rtl?width-edge:edge;sheen.style.clipPath=`polygon(${x-42}px -30px,${x+22}px -30px,${x+42}px ${height+35}px,${x-22}px ${height+35}px)`;sheen.style.opacity=String(Math.sin(Math.PI*p)*leave);}
        break;
      }
      case 'ink-reveal': {
        const rand=seeded(c.seed),images=[],sizes=[],positions=[];
        const cols=7,rows=2,cell=width/cols;
        for(let row=0;row<rows;row++)for(let col=0;col<cols;col++){
          const lag=col/cols*.30+rand()*.10,q=smooth((p-lag)/.60);
          const x=(col+.5)*cell+(rand()-.5)*cell*.30,y=(row+.4)*height/rows;
          const rx=Math.max(.1,cell*.95*q),ry=Math.max(.1,height*.81*q);
          images.push('radial-gradient(ellipse at center,#000 0%,#000 63%,rgba(0,0,0,.7) 70%,transparent 75%)');sizes.push(`${rx*2}px ${ry*2}px`);positions.push(`${x-rx}px ${y-ry}px`);
        }
        setMask(element,images,sizes,positions);break;
      }
      case 'side-slide': {
        const direction=c.from==='right'?1:-1;
        element.style.transform=`translateX(${direction*finite(c.distance,width*.58)*(1-e)}px) skewX(${-direction*16*(1-e)}deg)`;
        element.style.filter=`blur(${5*(1-e)}px)`;element.style.opacity=String(clamp(p/.08)*leave);break;
      }
      case 'flip-open': {
        element.style.transformOrigin='50% 100%';element.style.backfaceVisibility='hidden';
        element.style.transform=`perspective(1300px) rotateX(${-90*(1-e)}deg)`;element.style.opacity=String(clamp(p/.08)*leave);break;
      }
      case 'depth-push': {
        element.style.transform=`perspective(1100px) translateZ(${-1400*(1-e)}px) rotateY(${9*(1-e)}deg)`;
        element.style.filter=`blur(${12*(1-e)}px) brightness(${1+.3*(1-e)})`;element.style.opacity=String(clamp(p/.15)*leave);break;
      }
      case 'blur-focus': {
        element.style.filter=`blur(${32*Math.pow(1-p,2)}px) contrast(${1+.8*(1-p)})`;
        element.style.opacity=String((.12+.88*smooth(p/.7))*leave);break;
      }
    }
    return metrics;
  }
  function dispose(){if(disposed)return;for(const n of clones)n.remove();reset(element);element.style.opacity='1';disposed=true;}
  frame(-1);
  return {frame,dispose,metrics,effects:TITLE_EFFECTS};
}

// Convenience compatibility name for direct element/config integration.
export function createTitleAnimator(element,config,options={}){
  return createTitleAnimation({element,config,...options});
}
