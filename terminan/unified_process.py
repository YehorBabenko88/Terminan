"""Own only the test subprocess group/job, including Chromium descendants."""
import os,signal,subprocess,sys

def windows_job():
    import ctypes
    from ctypes import wintypes as W
    class Basic(ctypes.Structure):
        _fields_=[('process_time',ctypes.c_int64),('job_time',ctypes.c_int64),('flags',W.DWORD),('min_ws',ctypes.c_size_t),('max_ws',ctypes.c_size_t),('active',W.DWORD),('affinity',ctypes.c_size_t),('priority',W.DWORD),('scheduling',W.DWORD)]
    class Extended(ctypes.Structure):
        _fields_=[('basic',Basic),('io',ctypes.c_uint64*6),('process_memory',ctypes.c_size_t),('job_memory',ctypes.c_size_t),('peak_process',ctypes.c_size_t),('peak_job',ctypes.c_size_t)]
    api=ctypes.WinDLL('kernel32',use_last_error=True)
    api.CreateJobObjectW.argtypes=[ctypes.c_void_p,W.LPCWSTR];api.CreateJobObjectW.restype=W.HANDLE
    api.SetInformationJobObject.argtypes=[W.HANDLE,ctypes.c_int,ctypes.c_void_p,W.DWORD];api.SetInformationJobObject.restype=W.BOOL
    api.AssignProcessToJobObject.argtypes=[W.HANDLE,W.HANDLE];api.AssignProcessToJobObject.restype=W.BOOL
    api.CloseHandle.argtypes=[W.HANDLE];api.CloseHandle.restype=W.BOOL
    handle=api.CreateJobObjectW(None,None)
    if not handle:raise ValueError('BROWSER_CONTAINMENT_FAILED')
    info=Extended();info.basic.flags=0x2000 # KILL_ON_JOB_CLOSE, only owned test job
    if not api.SetInformationJobObject(handle,9,ctypes.byref(info),ctypes.sizeof(info)):
        api.CloseHandle(handle);raise ValueError('BROWSER_CONTAINMENT_FAILED')
    return api,handle

def run_browser(argv,env,timeout=300):
    # Wrapper waits for GO: descendants cannot start before containment assignment.
    api=handle=None;process=None
    try:
        if os.name=='nt':api,handle=windows_job()
        process=subprocess.Popen([sys.executable,'-m','terminan.unified_process',*argv],env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=os.name!='nt')
        if handle and not api.AssignProcessToJobObject(handle,int(process._handle)):raise ValueError('BROWSER_CONTAINMENT_FAILED')
        out,err=process.communicate(b'GO\n',timeout=timeout)
        return subprocess.CompletedProcess(argv,process.returncode,out,err)
    finally:
        if handle:api.CloseHandle(handle)
        elif process:
            try:os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:pass
        if process and process.poll() is None:process.kill();process.wait(timeout=5)

if __name__=='__main__':
    if sys.stdin.buffer.readline(4)!=b'GO\n':raise SystemExit(50)
    raise SystemExit(subprocess.call(sys.argv[1:]))
