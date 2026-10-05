import FlashDepth from '../modules/flash-depth';
import {makeFlashMap,makeSpecMap} from './relight';
let cache=null;
function decode64(s){const chars='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';let out=[],buf=0,bits=0;for(const ch of s.replace(/=+$/,'')){buf=(buf<<6)|chars.indexOf(ch);bits+=6;if(bits>=8){bits-=8;out.push((buf>>bits)&255)}}return new Uint8Array(out)}
export async function analyzeNativeOnce(asset){
 if(cache?.uri===asset.uri)return cache;
 const r=await FlashDepth.analyze(asset.uri);
 const depth=decode64(r.depth);
 cache={uri:asset.uri,w:r.width,h:r.height,depth,flashMap:makeFlashMap(depth,r.width,r.height),specMap:makeSpecMap(depth,r.width,r.height)};
 return cache;
}
export function clearNativeDepth(){cache=null}
