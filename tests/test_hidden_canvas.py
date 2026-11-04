"""Execute the real renderers with a zero-sized hidden-layout canvas."""
import shutil
import subprocess
import unittest
from pathlib import Path


class HiddenCanvasTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node runtime not configured')
    def test_hidden_render_does_not_destroy_retained_backing_buffer(self):
        root = Path(__file__).resolve().parents[1]
        script = r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
for(const [file,name,next] of [['r2_preview.js','drawChart','function drawPanels'],['r4_preview.js','drawChart','function drawPanels'],['saved.js','draw',' function tick']]){
 const source=fs.readFileSync('terminan/'+file,'utf8');
 const start=source.indexOf('function '+name+'(){');
 const end=source.indexOf('\n'+next,start);
 assert(start>=0&&end>start,file+' function boundary missing');
 let draws=0;
 const context=new Proxy({}, {get:()=>()=>draws++});
 const canvas={width:1200,height:450,clientWidth:0,clientHeight:0,getBoundingClientRect:()=>({width:0,height:0}),getContext:()=>context};
 const scope={document:{body:{dataset:{loading:'false'}}},canvas,ctx:context,devicePixelRatio:1.5,s:{data:null,start:0,end:0},text:()=>{},raf:1,dataset:()=>null,rows:[],replay:0,span:1,pan:0,chartTimes:[],syncClusterWindow:()=>{},$:id=>id==='saved-chart'?canvas:{hidden:false}};
 vm.createContext(scope);vm.runInContext(source.slice(start,end)+'\n'+name+'();',scope);
 assert.equal(canvas.width,1200,file+' discarded retained backing width while hidden');
 assert.equal(canvas.height,450,file+' discarded retained backing height while hidden');
 assert.equal(draws,0,file+' modified retained pixels while hidden');
}
'''
        completed = subprocess.run(['node', '-e', script], cwd=root, capture_output=True, text=True, timeout=10)
        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == '__main__': unittest.main()
