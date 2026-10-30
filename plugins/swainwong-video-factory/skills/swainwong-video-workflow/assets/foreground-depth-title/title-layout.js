import {createTitleAnimation} from './title-animation.js';
// Independent typography module: no media, mask, subject geometry or word-position inputs.
const defaults={fontFamily:'sans-serif',fallbackFamilies:['Arial','PingFang SC','sans-serif'],fontSize:260,fontWeight:900,minFontSize:96,autoFit:true,alignment:'justify',safeInsets:{left:88,right:88,top:130,bottom:200},top:205,locale:'zh-CN',direction:'auto',lineHeight:1.2};
export async function createTitle(element,sceneId,options={}){
 const configURL=new URL(options.configURL||'./title-config.example.json',import.meta.url);
 const config=options.config || await (await fetch(configURL,{cache:'no-store'})).json();
 const fontBaseURL=new URL(options.fontBaseURL||'.',configURL);
 const sceneDuration=options.sceneDuration??5;
 if(!(sceneDuration>0))throw Error('sceneDuration must be positive');
 for(const f of config.fonts||[]){
  const url=new URL(f.src,fontBaseURL);
  const face=new FontFace(f.family,`url("${url.href}")`,{weight:f.weight||'normal',style:f.style||'normal'});
  document.fonts.add(await face.load());
 }
 const c={...defaults,...config.global,...config.scenes?.[String(sceneId)],safeInsets:{...defaults.safeInsets,...config.global?.safeInsets,...config.scenes?.[String(sceneId)]?.safeInsets}};
 if(!element?.isConnected||!element.getClientRects().length)throw Error('Title must participate in layout before preload: attach it and use visibility:hidden or opacity:0, not display:none.');
 if(!(Number(c.fontSize)>0))throw Error('fontSize must be positive');
 const cssValue=(property,value)=>{if(!CSS.supports(property,String(value)))throw Error(`Invalid ${property}: ${value}`);return String(value);};
 const length=value=>typeof value==='number'?`${value}px`:value;
 const host=getComputedStyle(element);
 const styles={fontStyle:cssValue('font-style',c.fontStyle??host.fontStyle),color:cssValue('color',c.color??host.color),letterSpacing:cssValue('letter-spacing',length(c.letterSpacing??'normal')),wordSpacing:cssValue('word-spacing',length(c.wordSpacing??'normal')),textShadow:cssValue('text-shadow',c.textShadow??host.textShadow),webkitTextStrokeWidth:cssValue('-webkit-text-stroke-width',length(c.textStrokeWidth??host.webkitTextStrokeWidth)),webkitTextStrokeColor:cssValue('-webkit-text-stroke-color',c.textStrokeColor??host.webkitTextStrokeColor)};
 const lineHeight=cssValue('line-height',c.lineHeight??1.2);
 if(typeof c.text!=='string')throw Error(`Scene ${sceneId}: text must be a string`);
 const text=c.text; // Never slice, normalize, trim, tokenize, reconstruct, or truncate authored text.
 const W=config.canvas?.width??1920,H=config.canvas?.height??1080;
 const family=[c.fontFamily,...(c.fallbackFamilies||[])].map(f=>['serif','sans-serif','monospace'].includes(f)?f:JSON.stringify(f)).join(',');
 element.textContent=text;element.setAttribute('aria-label',text);element.lang=c.locale||'';element.dir=c.direction||'auto';
 Object.assign(element.style,{fontFamily:family,fontWeight:String(c.fontWeight),fontSize:`${c.fontSize}px`,lineHeight,...styles,whiteSpace:'pre',overflow:'visible',textOverflow:'clip',width:'max-content',left:`${c.safeInsets.left}px`,top:`${Math.max(c.top,c.safeInsets.top)}px`});
 await document.fonts.load(`${styles.fontStyle} ${c.fontWeight} ${c.fontSize}px ${family}`,text);await document.fonts.ready;
 const available=W-c.safeInsets.left-c.safeInsets.right;
 if(!(available>0))throw Error('safeInsets leave no horizontal space');
 const measure=size=>{element.style.fontSize=`${size}px`;return element.getBoundingClientRect().width;};
 const requested=c.fontSize,natural=measure(requested);let effective=requested;
 if(!(element.getBoundingClientRect().height>0))throw Error('Title has no measurable height after font/style load.');
 if(natural>available+.25){
  if(!c.autoFit)throw Error(`Title exceeds available width (${natural.toFixed(1)} > ${available}px). Enable autoFit or reduce fontSize; no text was truncated.`);
  let lo=.1,hi=requested;
  for(let i=0;i<24;i++){let m=(lo+hi)/2;measure(m)<=available?lo=m:hi=m;}
  effective=Math.floor(lo*100)/100;measure(effective);
 }
 // Enforce vertical safety independently of subject masks; exceptionally long text can become small, never clipped.
 const maxHeight=H-c.safeInsets.bottom-Math.max(c.top,c.safeInsets.top);
 if(!(maxHeight>0))throw Error('safeInsets/top leave no vertical space');
 if(element.getBoundingClientRect().height>maxHeight){
  if(!c.autoFit)throw Error('Title exceeds vertical safe area; enable autoFit or reduce fontSize.');
  let lo=.1,hi=effective;
  for(let i=0;i<24;i++){let m=(lo+hi)/2;measure(m);element.getBoundingClientRect().height<=maxHeight?lo=m:hi=m;}
  effective=Math.floor(lo*100)/100;measure(effective);
 }
 const warnings=[];if(effective<c.minFontSize)warnings.push(`Auto-fit required ${effective}px, below preferred minFontSize ${c.minFontSize}px. Shorten/reflow text or expand safe area for readability; full string is preserved.`);
 // Native browser justification keeps the original single text node, shaping, ligatures and spaces.
 // Latin justification expands word spaces; CJK permits inter-character justification.
 const alignment=c.alignment||'justify';
 Object.assign(element.style,{width:`${available}px`,whiteSpace:'pre-wrap',overflowWrap:'normal',wordBreak:'keep-all',hyphens:'none',textAlign:alignment,textAlignLast:alignment,textJustify:'auto'});
 if(element.scrollWidth>available+1)throw Error('Layout overflow after font loading; no truncation is permitted.');
 const metrics={sceneId,text,requestedFontSize:requested,effectiveFontSize:effective,naturalWidth:natural,availableWidth:available,fontFamily:family,fontWeight:c.fontWeight,styles,lineHeight,alignment,locale:c.locale,direction:c.direction,safeInsets:c.safeInsets,warnings,textPreserved:element.textContent===text};
 window.titleLayout=metrics;window.titleConfig=c;
 const animation=createTitleAnimation({element,config:c.animation||{},labelElement:options.labelElement??null,sceneDuration});
 return {metrics,animationMetrics:animation.metrics,dispose:()=>animation.dispose(),frame(t,anchor){
  element.style.top=`${Math.max(c.top,c.safeInsets.top)}px`;
  animation.frame(t,anchor);
  metrics.phase='natural-depth';
 }};
}
