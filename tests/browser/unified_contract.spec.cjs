// Browser contract fixtures only. No Grid, Math, numerical worker or final E2E.
const {test,expect}=require('@playwright/test');
const {spawn,execFileSync}=require('node:child_process');
const path=require('node:path');let child,url;
const fixture=path.resolve('tests/fixtures/unified-contract.v1.json');
test.beforeAll(async()=>{
 child=spawn(process.env.R2_PYTHON||'python',['scripts/unified_contract_test_server.py'],{env:{...process.env,PYTHONPATH:'.'},windowsHide:true,stdio:['pipe','pipe','pipe']});
 url=await new Promise((resolve,reject)=>{let s='',err='';const t=setTimeout(()=>reject(Error('SERVER_TIMEOUT '+err)),10000);
  child.stderr.on('data',b=>err+=b);child.once('error',reject);child.once('exit',()=>{clearTimeout(t);reject(Error('SERVER_EXIT '+err))});
  child.stdout.on('data',b=>{s+=b;if(s.includes('\n')){clearTimeout(t);resolve(JSON.parse(s.split('\n')[0]).url.replace('/math','/history-overlay'))}})});
});
test.afterAll(async()=>{if(child&&child.exitCode===null){const done=new Promise(r=>child.once('exit',r));child.stdin.end('\n');await done}});
test.beforeEach(async({page})=>{await page.goto(url);await page.setInputFiles('#upload',fixture);await expect(page.locator('#status')).toContainText('READ_ONLY')});
async function asof(page,time){await page.fill('#asof',String(time));await page.locator('#asof').dispatchEvent('change')}

test('delayed facts, frozen forecasts and joint publication remain distinct',async({page})=>{
 await expect(page.locator('#status')).toContainText('UNQUALIFIED_CONTRACT_ONLY');await expect(page.locator('.layer-toggle')).toHaveCount(3);
 await asof(page,1200000);await expect(page.locator('.observation-point')).toHaveCount(19);await expect(page.locator('.forecast-past')).toHaveCount(1);
 await expect(page.locator('.scientific-point')).toHaveCount(0);await expect(page.locator('#diagnostics')).toContainText('NOT_AVAILABLE_ASOF');
 await asof(page,1200500);await expect(page.locator('.observation-point')).toHaveCount(20);await expect(page.locator('.forecast-future')).toHaveCount(0);
 await asof(page,1201000);await expect(page.locator('.forecast-future')).toHaveCount(1);await expect(page.locator('.scientific-point')).toHaveCount(0);
 await asof(page,1202000);await expect(page.locator('.scientific-point')).toHaveCount(40);await expect(page.locator('#diagnostics')).toContainText('DESCRIPTIVE_NOT_OOS');
 await expect(page.locator('#oos')).toContainText('NOT_AVAILABLE_ASOF');
});

test('OOS is displayed only after its declared publication, outside diagnostics',async({page},info)=>{
 await asof(page,1269999);await expect(page.locator('#oos')).toContainText('NOT_AVAILABLE_ASOF');
 await asof(page,1270000);await expect(page.locator('#oos')).toContainText('PRODUCER_REPORTED_OOS_UNATTESTED');
 await expect(page.locator('#oos')).toContainText('net_pnl');await expect(page.locator('#diagnostics')).not.toContainText('net_pnl');
 await expect(page.locator('.forecast-past')).toHaveCount(2);await expect(page.locator('.forecast-future')).toHaveCount(1);
 await page.selectOption('#mode','forward');await expect(page.locator('.forecast-past')).toHaveCount(0);await expect(page.locator('.observation-point')).toHaveCount(21);
 await info.attach('unified-contract-screenshot',{body:await page.screenshot({fullPage:true}),contentType:'image/png'});
});

test('rehashed envelope cannot bypass scientific output trace integrity',async({page})=>{
 const code="import sys,json,hashlib;p=json.load(open(sys.argv[1]));j=p['joint_result'];j['scientific']['outputs'][0]['values'][0]=999;h=lambda x:hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest();j['completion_receipt']=h({k:v for k,v in j.items() if k!='completion_receipt'});p['packet_sha256']=h({k:v for k,v in p.items() if k!='packet_sha256'});print(json.dumps(p))";
 const buffer=execFileSync(process.env.R2_PYTHON||'python',['-c',code,fixture]);
 await page.setInputFiles('#upload',{name:'tampered.json',mimeType:'application/json',buffer});
 await expect(page.locator('#status')).toContainText('SCIENTIFIC_OUTPUT_DIGEST');await expect(page.locator('.layer-toggle')).toHaveCount(3);
});

test('asOf slider reaches publication later than every event and forecast target',async({page})=>{
 const code="import sys,json,hashlib;p=json.load(open(sys.argv[1]));p['joint_published_at_ms']=2000000;p.pop('packet_sha256');p['packet_sha256']=hashlib.sha256(json.dumps(p,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest();print(json.dumps(p))";
 const buffer=execFileSync(process.env.R2_PYTHON||'python',['-c',code,fixture]);
 await page.click('#clear');await page.setInputFiles('#upload',{name:'late.json',mimeType:'application/json',buffer});
 await expect(page.locator('#status')).toContainText('READ_ONLY');await expect(page.locator('#asofSlider')).toHaveAttribute('max','2000000');
 await page.locator('#asofSlider').fill('2000000');await page.locator('#asofSlider').dispatchEvent('input');
 await expect(page.locator('.scientific-point')).toHaveCount(40);await expect(page.locator('#diagnostics')).toContainText('DESCRIPTIVE_NOT_OOS');
});
