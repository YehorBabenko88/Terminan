const base=require('./playwright.config.cjs');
const path=require('node:path');const {spawnSync}=require('node:child_process');
const root=process.env.R4_WORK_ROOT||'.';
const git=spawnSync('git',['rev-parse','HEAD'],{encoding:'utf8'});
module.exports={...base,metadata:{r4_invocation:process.env.R4_INVOCATION,r4_source_sha:git.status===0?git.stdout.trim():null},testIgnore:['**/r3.spec.cjs'],testMatch:'**/r4.spec.cjs',reporter:[['list'],['json',{outputFile:path.resolve(root,'reports/r4-browser.json')}]],outputDir:path.resolve(root,'r4-test-results')};
