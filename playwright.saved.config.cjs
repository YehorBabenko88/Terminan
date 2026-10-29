const base=require('./playwright.config.cjs');
const {execFileSync}=require('node:child_process');
module.exports={...base,testIgnore:[],testMatch:'**/saved.spec.cjs',timeout:60000,metadata:{invocation:process.env.SAVED_INVOCATION,started_ms:Number(process.env.SAVED_STARTED_MS),source_sha:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim()},reporter:[['list'],['json',{outputFile:'reports/saved-browser.json'}]],outputDir:'saved-test-results'};
