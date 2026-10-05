const {withXcodeProject,withDangerousMod}=require('@expo/config-plugins');
const fs=require('fs'),path=require('path');
module.exports=function withFlashDepth(config){
 config=withDangerousMod(config,['ios',async c=>{
   const root=c.modRequest.projectRoot,src=path.join(root,'models','DepthAnythingV2SmallF16P6.mlpackage');
   if(!fs.existsSync(src)) throw new Error('Missing models/DepthAnythingV2SmallF16P6.mlpackage. Download the official Apple Core ML package before EAS build.');
   return c;
 }]);
 return withXcodeProject(config,c=>{
   const p=c.modResults;
   const rel='models/DepthAnythingV2SmallF16P6.mlpackage';
   if(!p.hasFile(rel)) p.addResourceFile(rel,{target:p.getFirstTarget().uuid});
   return c;
 });
};