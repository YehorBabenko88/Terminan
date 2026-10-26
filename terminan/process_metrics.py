"""Read-only per-process resident memory. No environment, command lines or paths emitted."""
import json,os,sys

def resident_bytes(pid):
    if type(pid) is not int or pid<=0:raise ValueError()
    if os.name=='nt':
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)]+[(name,ctypes.c_size_t) for name in ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]
        kernel=ctypes.WinDLL('kernel32',use_last_error=True);psapi=ctypes.WinDLL('psapi',use_last_error=True)
        kernel.OpenProcess.restype=wintypes.HANDLE;kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
        kernel.CloseHandle.argtypes=[wintypes.HANDLE]
        psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.c_void_p,wintypes.DWORD]
        handle=kernel.OpenProcess(0x410,False,pid)
        if not handle:raise OSError()
        try:
            counters=Counters();counters.cb=ctypes.sizeof(counters)
            if not psapi.GetProcessMemoryInfo(handle,ctypes.byref(counters),counters.cb):raise OSError()
            return counters.WorkingSetSize
        finally:kernel.CloseHandle(handle)
    with open(f'/proc/{pid}/statm',encoding='ascii') as stream:return int(stream.read().split()[1])*os.sysconf('SC_PAGE_SIZE')

def sample(pids):
    if not isinstance(pids,list) or not 1<=len(pids)<=64 or len(set(pids))!=len(pids):raise ValueError()
    try:return dict(state='AVAILABLE',scope='SUM_PROCESS_RSS_SHARED_PAGES_MAY_DOUBLE_COUNT',rss_bytes=sum(resident_bytes(pid) for pid in pids),process_count=len(pids))
    except (OSError,ValueError):return dict(state='UNAVAILABLE',reason='PROCESS_MEMORY_UNAVAILABLE')
if __name__=='__main__':
    try:print(json.dumps(sample([int(p) for p in sys.argv[1:]])))
    except (ValueError,TypeError):print('{"state":"UNAVAILABLE","reason":"INVALID_PROCESS_SAMPLE"}');raise SystemExit(50)
