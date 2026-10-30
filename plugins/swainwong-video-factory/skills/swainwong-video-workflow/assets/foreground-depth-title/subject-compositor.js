// Same-source background/foreground compositor. No subject detector is bundled.
// Decode video to frames and supply matching masks, or supply a still + alpha mask.
export async function createSubjectCompositor({background,foreground,source,baseURL=document.baseURI,width=1920,height=1080,duration=5,fps=30}){
 if(!(duration>0&&fps>0&&width>0&&height>0))throw Error('Invalid scene dimensions/time');
 const B=background.getContext('2d'),F=foreground.getContext('2d');
 for(const canvas of [background,foreground]){canvas.width=width;canvas.height=height;}
 const rect=source.rect||[0,0,width,height],cache=new Map();
 async function image(path){
  if(!path)throw Error('Missing source/mask path');
  const url=new URL(path,baseURL).href;
  if(cache.has(url))return cache.get(url);
  const im=new Image();im.src=url;await im.decode();cache.set(url,im);
  if(cache.size>8)cache.delete(cache.keys().next().value);return im;
 }
 const pathAt=(pattern,n)=>pattern?.replace('{frame}',String(n).padStart(source.frameDigits??5,'0'));
 const count=source.frameCount??Math.ceil(duration*fps);
 if(source.type==='video'&&!source.framePattern)throw Error('Video export requires a decoded framePattern for this adapter');
 if(!source.mask&&!source.maskPattern&&!source.polygon&&!source.polygons)throw Error('A subject alpha mask or polygon is required');
 async function frame(t){
  const n=Math.min(count-1,Math.max(0,Math.floor((t+1e-6)*fps)));
  const polygon=source.polygon||source.polygons?.[n];
  const [im,mask]=await Promise.all([image(source.type==='video'?pathAt(source.framePattern,n):source.src),polygon?null:image(source.mask||pathAt(source.maskPattern,n))]);
  const z=source.type==='image'?1+(source.zoomAmount??0)*Math.max(0,Math.min(1,t/duration)):1;
  for(const ctx of [B,F]){ctx.clearRect(0,0,width,height);ctx.save();ctx.translate(width/2,height/2);ctx.scale(z,z);ctx.translate(-width/2,-height/2);}
  B.fillStyle=source.backgroundColor||'#11191f';B.fillRect(0,0,width,height);
  if(source.sideFill){B.save();B.filter=`blur(${source.sideFill.blur}px) brightness(${source.sideFill.brightness})`;B.drawImage(im,...source.sideFill.rect);B.restore();}
  B.drawImage(im,...rect);
  if(polygon){F.beginPath();polygon.forEach(([x,y],i)=>{const p=[rect[0]+x*rect[2],rect[1]+y*rect[3]];i?F.lineTo(...p):F.moveTo(...p);});F.closePath();F.clip();F.drawImage(im,...rect);}
  else{
   let alpha=mask;
   if(!source.maskIsAlpha){alpha=document.createElement('canvas');alpha.width=mask.width;alpha.height=mask.height;const A=alpha.getContext('2d',{willReadFrequently:true});A.drawImage(mask,0,0);const d=A.getImageData(0,0,alpha.width,alpha.height);for(let i=0;i<d.data.length;i+=4){d.data[i+3]=d.data[i];d.data[i]=d.data[i+1]=d.data[i+2]=255;}A.putImageData(d,0,0);}
   F.drawImage(im,...rect);F.globalCompositeOperation='destination-in';F.drawImage(alpha,...rect);F.globalCompositeOperation='source-over';
  }
  B.restore();F.restore();return {frame:n,sourceTime:source.type==='video'?n/fps:0};
 }
 await frame(0);return {frame,width,height,duration,fps};
}
