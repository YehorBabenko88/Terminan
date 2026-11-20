import os,sys,re
PYTHON=os.path.normcase(os.path.realpath(sys.executable))
def safe_launch(event,args):
    if event=='os.system':raise RuntimeError('NATIVE_SHELL_FORBIDDEN')
    if event=='subprocess.Popen':
        executable=args[0]
        if executable is None:
            command=args[1]
            if isinstance(command,(tuple,list)):executable=command[0]
            else:
                match=re.match(r'^(?:"([^"\r\n]+)"|([^\s]+))',command)
                if match is None:raise RuntimeError('UNRECOGNIZED_CHILD_COMMAND')
                executable=match[1] or match[2]
        if os.path.normcase(os.path.realpath(executable))!=PYTHON:
            raise RuntimeError('ONLY_REVIEWED_PYTHON_CHILD_ALLOWED')
sys.addaudithook(safe_launch)
import pytest
sys.exit(pytest.main(['-q','tests','-p','pytest_asyncio.plugin']))
