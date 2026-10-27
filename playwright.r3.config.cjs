const base=require('./playwright.config.cjs');
const path=require('node:path');const {spawnSync}=require('node:child_process');
const root=process.env.R3_WORK_ROOT||'.';
const git=spawnSync('git',['rev-parse','HEAD'],{encoding:'utf8'});
module.exports={...base,metadata:{r3_invocation:process.env.R3_INVOCATION,r3_source_sha:git.status===0?git.stdout.trim():null},testIgnore:['**/r4.spec.cjs'],testMatch:'**/r3.spec.cjs',reporter:[['list'],['json',{outputFile:path.resolve(root,'reports/r3-browser.json')}]],outputDir:path.resolve(root,'r3-test-results')};
