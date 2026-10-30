import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from visual_qa import validate_report,validate_metrics,TITLE,PROJECTS
class VisualEvidenceTests(unittest.TestCase):
 def report(self):return dict(config=dict(metadata=dict(source_sha='a'*40,tree='b'*40,invocation='c'*32,zoom_method='CHROME_TABS_SETZOOM_GETZOOM')),stats=dict(expected=3,unexpected=0,skipped=0,flaky=0),errors=[],suites=[dict(specs=[dict(title=TITLE,tests=[dict(projectName=p,expectedStatus='passed',status='expected',results=[dict(status='passed',errors=[])]) for p in PROJECTS])])])
 def test_complete_and_interrupted_partial_stale_false_zero(self):
  validate_report(self.report(),'a'*40,'b'*40,'c'*32)
  for case in ('missing','interrupted','skipped','stale','duplicate','false_zero'):
   r=self.report()
   if case=='missing':r['suites'][0]['specs'][0]['tests'].pop()
   if case=='interrupted':r['suites'][0]['specs'][0]['tests'][1]['results'][0]['status']='interrupted'
   if case=='skipped':r['stats']['skipped']=1
   if case=='stale':r['config']['metadata']['invocation']='0'*32
   if case=='duplicate':r['suites'][0]['specs'][0]['tests'][1]['projectName']=PROJECTS[0]
   if case=='false_zero':r['stats']['expected']=1
   with self.subTest(case=case),self.assertRaises(ValueError):validate_report(r,'a'*40,'b'*40,'c'*32)
 def test_matrix_must_be_complete_and_bound(self):
  values=[]
  for p,dpr in zip(PROJECTS,(1,1.5,2)):
   rows=[dict(size=dict(width=w,height=h),zoom=z,actualZoom=z,route=r,width=w/z,scrollWidth=w/z,controls=[],overlaps=[],replacementChars=False,browser=dict(dpr=dpr*z,pinch=1)) for w,h in ((1280,720),(1920,1080)) for z in (1,1.5,2) for r in ('/','/saved','/math','/history-overlay','/monitor','/cache')]
   values.append(dict(project=p,dpr=dpr,source_sha='a'*40,tree='b'*40,invocation='c'*32,rows=rows,state_retention=dict(terminal=True,saved=True,lab=True),page_errors=[],console_errors=[],pixel_parity=[dict(equal=True)]*3))
  self.assertEqual(validate_metrics(values,'a'*40,'b'*40,'c'*32),108)
  for case in ('missing','clipped','wrong_zoom','stale','controls'):
   r=copy.deepcopy(values)
   if case=='missing':r[0]['rows'].pop()
   if case=='clipped':r[0]['rows'][0]['scrollWidth']=5000
   if case=='wrong_zoom':r[0]['rows'][0]['browser']['dpr']=99
   if case=='stale':r[0]['source_sha']='0'*40
   if case=='controls':r[0]['rows'][0]['controls']=['hidden-button']
   with self.subTest(case=case),self.assertRaises(ValueError):validate_metrics(r,'a'*40,'b'*40,'c'*32)
if __name__=='__main__':unittest.main()
