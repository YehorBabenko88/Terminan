const {test,expect}=require('@playwright/test');
const {spawn,execFileSync}=require('node:child_process');
let child,url;
const python=process.env.R2_PYTHON||'python';
function fixture(){return JSON.parse(execFileSync(python,['-c',"import json,time;from tests.test_lab_view_v2 import sample;from terminan.lab_view import overview_v2;n=int(time.time()*1000);print(json.dumps(overview_v2(sample(n),n,n)))"],{encoding:'utf8',windowsHide:true,env:{...process.env,PYTHONPATH:'.'}}))}
test.beforeAll(async()=>{
 child=spawn(python,['-u','scripts/lab_view_test_server.py'],{env:{...process.env,PYTHONPATH:'.'},windowsHide:true,stdio:['pipe','pipe','pipe']});
 url=await new Promise((resolve,reject)=>{let output='';const timer=setTimeout(()=>reject(Error('SERVER_TIMEOUT')),10000);child.once('error',reject);child.once('exit',()=>reject(Error('SERVER_EXIT')));child.stdout.on('data',b=>{output+=b;if(output.includes('\n')){clearTimeout(timer);resolve(JSON.parse(output.split('\n')[0]).url)}})});
});
test.afterAll(async()=>{if(child&&child.exitCode===null){const done=new Promise(resolve=>child.once('exit',resolve));child.stdin.end('stop\n');await done}});
test('SYNTHETIC v2: exact qualifiers, partial observations, null heartbeat, XSS and staleness',async({page},info)=>{
 const data=fixture();let payload=data;
 await page.route('**/api/lab/overview',route=>route.fulfill({json:payload}));
 await page.goto(url+'/lab');await expect(page.locator('#state')).toHaveText('AVAILABLE');
 await expect(page.locator('#market-v2')).toContainText('UNKNOWN');await expect(page.locator('#market-v2')).toContainText('123.4500');
 await expect(page.locator('#market-v2')).toContainText('NOT_EVALUATED');await expect(page.locator('#market-v2')).toContainText('No atomic multi-symbol snapshot');
 await expect(page.locator('#paper-v2')).toContainText('CLOSED RESEARCH');await expect(page.locator('#paper-v2')).toContainText('NOT_QUALIFIED');
 await expect(page.locator('#paper-v2')).toContainText('OPEN_POSITIONS');await expect(page.locator('#paper-v2')).toContainText('CALLER_DECLARED');await expect(page.locator('#paper-v2')).toContainText('s1');
 await expect(page.locator('#fleet-v2')).toContainText('UNKNOWN');await expect(page.locator('#fleet-v2')).toContainText('APPROVED');
 await expect(page.locator('#fleet-v2')).not.toContainText('ONLINE');await expect(page.locator('#fleet-v2')).toContainText('PLAN_ONLY');
 const attack='<img src=x onerror="window.v2Xss=true">';payload.sections.fleet.payload.nodes[0].zone=attack;await page.evaluate(()=>refresh());
 await expect(page.locator('#fleet-v2')).toContainText(attack);await expect(page.locator('#content img')).toHaveCount(0);expect(await page.evaluate(()=>window.v2Xss)).toBeUndefined();
 payload=fixture();payload.sections.market.payload=[];payload.sections.fleet.payload.nodes=[];payload.sections.paper={state:'UNAVAILABLE',error_code:'SOURCE_NOT_CONFIGURED',payload:null};payload.section_states.paper='UNAVAILABLE';payload.state='PARTIAL';await page.evaluate(()=>refresh());
 await expect(page.locator('#state')).toHaveText('PARTIAL');await expect(page.locator('#paper-v2')).toContainText('SOURCE_NOT_CONFIGURED');await expect(page.locator('#fleet-v2')).toContainText('No reported nodes');await expect(page.locator('#market-v2')).toContainText('No reported market observations');
 await expect(page.locator('#content')).not.toContainText('READY');
 payload=fixture();await page.evaluate(()=>refresh());await expect(page.locator('#state')).toHaveText('AVAILABLE');
 await page.clock.install();await page.clock.setSystemTime(new Date(Date.now()+16000));await page.clock.runFor(600);await expect(page.locator('#state')).toContainText('STALE');
 await info.attach('synthetic-v2-observations',{body:await page.screenshot({fullPage:true}),contentType:'image/png'});
});
