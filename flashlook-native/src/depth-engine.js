// V5 native boundary.
// The UI calls this once per selected photo. The inference implementation will live
// behind this boundary so editing never owns or reruns the model session.
import {makeFlashMap,makeSpecMap} from './relight';

let cache=null;
export function clearDepthCache(){cache=null}
export function getDepthCache(){return cache}

export async function analyzePhotoOnce(asset){
 if(cache?.uri===asset.uri)return cache;
 // Temporary deterministic fallback until the Core ML model asset is added:
 // creates a tiny neutral depth field, proving the editor/cache lifecycle without
 // loading Transformers.js/WebKit/ONNX. Replace ONLY this block with Core ML inference.
 const w=192,h=256,depth=new Uint8Array(w*h);
 for(let y=0;y<h;y++)for(let x=0;x<w;x++){
  const nx=(x/(w-1)-.5)*2,ny=(y/(h-1)-.5)*2;
  depth[y*w+x]=Math.round(255*Math.max(.08,1-.48*Math.sqrt(nx*nx+ny*ny)));
 }
 cache={uri:asset.uri,w,h,depth,flashMap:makeFlashMap(depth,w,h),specMap:makeSpecMap(depth,w,h)};
 return cache;
}