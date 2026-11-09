'use strict';
// Scoped test restriction for the pinned SDK's Windows forced-cleanup callsite.
// This does not issue a native permit or establish an OS security boundary.
const cp=require('node:child_process'),{syncBuiltinESMExports}=require('node:module');
let state;
function install(){
 if(arguments.length!==0)throw Error('GUARD_ARGUMENTS');
 if(state)return state;
 for(const p of Object.keys(require.cache))if(/[\\/]node_modules[\\/](?:@playwright[\\/]test|playwright|playwright-core)[\\/]/.test(p))throw Error('SDK_ALREADY_IMPORTED');
 let denied=0;
 const deny=()=>{denied=Math.min(65535,denied+1);if(denied===1)process.stderr.write('SYNC_SPAWN_DENIED_ROOT_JOB_TEARDOWN_REQUIRED\n');throw Error('SYNC_SPAWN_DENIED_ROOT_JOB_TEARDOWN_REQUIRED');};
 Object.defineProperty(cp,'spawnSync',{value:deny,writable:false,configurable:false,enumerable:true});
 syncBuiltinESMExports();
 state=Object.freeze({snapshot:()=>Object.freeze({scope:'PINNED_SDK_SPAWNSYNC_RESTRICTION_NOT_OS_BOUNDARY',installed:true,denied_attempts:denied,root_job_teardown_required:denied>0})});
 return state;
}
module.exports=Object.freeze({install});
