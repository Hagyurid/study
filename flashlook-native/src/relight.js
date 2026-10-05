// Pure response-map relighting math. No model is retained here.
export function makeFlashMap(depth,w,h){
 const map=new Uint8Array(w*h);
 const at=(x,y)=>depth[Math.max(0,Math.min(h-1,y))*w+Math.max(0,Math.min(w-1,x))]/255;
 for(let y=0;y<h;y++)for(let x=0;x<w;x++){
  const d=at(x,y),gx=at(x+1,y)-at(x-1,y),gy=at(x,y+1)-at(x,y-1);
  const facing=1/Math.sqrt(1+36*(gx*gx+gy*gy));
  const near=Math.max(0,Math.min(1,(d-.08)/.92));
  map[y*w+x]=Math.round(255*Math.min(1,(.18+.82*near*near)*(.42+.58*facing)));
 }
 return map;
}
export function makeSpecMap(depth,w,h){
 const m=new Uint8Array(w*h);
 for(let i=0;i<m.length;i++){const d=depth[i]/255;m[i]=Math.round(255*Math.pow(Math.max(0,(d-.2)/.8),2.2))}
 return m;
}