"""Protected-source API protocol tests; no service or kernel qualification."""
import hashlib,os,shutil,subprocess,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from terminan import unified_runner as runner

class ProtectedSourceTests(unittest.TestCase):
 def setUp(self):
  # CI supplies this separate pinned checkout explicitly. Never substitute a
  # vendored/cached verifier or treat the fixture as runtime authorization.
  from integration import source_guard
  expected=os.environ.get('TERMINAN_TEST_UNIFIED_ROOT')
  if expected:self.assertEqual(Path(source_guard.__file__).resolve(),(Path(expected)/'integration/source_guard.py').resolve())
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve()/'source';(self.root/'terminan').mkdir(parents=True)
  self.file=self.root/'terminan/unified_runner.py';self.file.write_bytes(b'INERT_TEST_SOURCE\n')
  def git(*args):return subprocess.check_output(['git','-C',str(self.root),*args],stderr=subprocess.DEVNULL).decode().strip()
  git('init','-q');git('config','core.autocrlf','false');git('add','.');git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','fixture')
  self.head=git('rev-parse','HEAD');self.tree=git('rev-parse','HEAD^{tree}');self.git=Path(shutil.which('git')).resolve();self.config=(self.root/'.git/config').read_bytes();self.calls=[]
  def scope(module,root,head):
   self.calls.append((module,root,head))
   if (module,root,head)!=('terminan',self.root,self.head):raise ValueError('wrong scope')
   return self.root
  self.admission=SimpleNamespace(require_current=lambda:True,source_scope=scope,source_identity=lambda module:dict(commit=self.head,tree=self.tree),git_executable=str(self.git),git_sha256=hashlib.sha256(self.git.read_bytes()).hexdigest())
  self.file_patch=patch.object(runner,'__file__',str(self.file));self.file_patch.start();self.addCleanup(self.file_patch.stop)
 def test_default_foreign_owner_denied_but_exact_protected_scope_passes_without_git_config_write(self):
  real=subprocess.Popen
  def foreign(*args,**kwargs):kwargs['env']=dict(kwargs.get('env',os.environ),GIT_TEST_ASSUME_DIFFERENT_OWNER='1');return real(*args,**kwargs)
  with patch.object(subprocess,'Popen',side_effect=foreign):
   with self.assertRaises(subprocess.SubprocessError):runner.provenance()
   result=runner.provenance(startup_admission=self.admission,expected_commit=self.head)
  self.assertEqual(result,dict(candidate_sha=self.head,tree=self.tree,source_clean=True));self.assertTrue(self.calls);self.assertEqual((self.root/'.git/config').read_bytes(),self.config)
 def test_revoked_json_wrong_scope_head_tree_and_git_pin_block(self):
  for change in ('revoked','json','scope','head','tree','git'):
   admission=SimpleNamespace(**vars(self.admission));expected=self.head
   if change=='revoked':admission.require_current=lambda:1
   elif change=='json':admission={'authorized':True}
   elif change=='scope':admission.source_scope=lambda *args:self.root.parent
   elif change=='head':expected='f'*40
   elif change=='tree':admission.source_identity=lambda module:dict(commit=self.head,tree='f'*40)
   else:admission.git_sha256='f'*64
   with self.subTest(change=change):
    with self.assertRaises(ValueError):runner.provenance(startup_admission=admission,expected_commit=expected)
 def test_main_passes_expected_sha_and_admission_before_constructing_server(self):
  admission=object();calls=[]
  def provenance(**kwargs):calls.append(kwargs);raise ValueError('fixed before effects')
  with patch.object(runner,'provenance',side_effect=provenance),patch.object(runner,'UnifiedServer') as server:
   self.assertEqual(runner.main(['--expected-sha',self.head],startup_admission=admission),50);server.assert_not_called()
  self.assertEqual(calls,[dict(startup_admission=admission,expected_commit=self.head)])

if __name__=='__main__':unittest.main()
