import contextlib,http.client,io,os,socket,struct,threading,time,unittest
from unittest.mock import patch
from terminan.r2_server import R2Server,R2Handler

class Reliability(unittest.TestCase):
    def test_reset_while_headers_are_flushed_does_not_write_stderr(self):
        errors=io.StringIO();entered=threading.Event();release=threading.Event();original=R2Handler.end_headers
        def headers(handler):
            if handler.path.startswith('/api/synthetic/frame'):entered.set();release.wait(5)
            return original(handler)
        with contextlib.redirect_stderr(errors),patch.object(R2Handler,'end_headers',headers):
            server=R2Server(('127.0.0.1',0),R2Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                client=socket.create_connection(('127.0.0.1',server.server_port),timeout=5)
                client.sendall(f'GET /api/synthetic/frame?step=100 HTTP/1.1\r\nHost: 127.0.0.1:{server.server_port}\r\n\r\n'.encode())
                self.assertTrue(entered.wait(5))
                client.setsockopt(socket.SOL_SOCKET,socket.SO_LINGER,struct.pack('hh' if os.name=='nt' else 'ii',1,0));client.close();release.set()
                c=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=5);c.request('GET','/api/status');r=c.getresponse();r.read();c.close();self.assertEqual(r.status,200)
            finally:release.set();server.shutdown();server.server_close();thread.join(3)
        self.assertFalse(bool(errors.getvalue()))
    def test_request_workers_are_joined_before_interpreter_shutdown(self):
        self.assertFalse(R2Server.daemon_threads)
        self.assertTrue(R2Server.block_on_close)

class TransportAndFailures(unittest.TestCase):
    def test_only_IO_boundaries_classify_disconnects(self):
        from terminan.r2_diagnostics import Diagnostics,TransportIO,PeerDisconnected
        class Stream:
            def write(self,value):raise ConnectionResetError('PRIVATE_DSN_SECRET')
        d=Diagnostics()
        with self.assertRaises(PeerDisconnected):TransportIO(Stream(),d).write(b'abc')
        self.assertEqual(d.snapshot()['counters']['HTTP_PEER_RESET'],1)
        self.assertNotIn('PRIVATE_DSN_SECRET',str(d.snapshot()))
        class Broken:
            def write(self,value):raise OSError(22,'PRIVATE_DSN_SECRET')
        with self.assertRaises(OSError):TransportIO(Broken(),d).write(b'abc')
    def test_handler_errors_are_fatal_and_never_raw(self):
        from terminan.r2_diagnostics import FATAL
        for exception in (RuntimeError,ConnectionResetError):
            class Bad(R2Handler):
                def do_GET(self):raise exception('PRIVATE_DSN_SECRET')
            errors=io.StringIO()
            with contextlib.redirect_stderr(errors):
                server=R2Server(('127.0.0.1',0),Bad);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
                try:
                    c=socket.create_connection(('127.0.0.1',server.server_port),timeout=3);c.sendall(b'GET / HTTP/1.0\r\n\r\n');c.recv(1024);c.close()
                finally:server.shutdown();server.server_close();thread.join(3)
            self.assertEqual(errors.getvalue(),'R2_DIAGNOSTIC HTTP_HANDLER_FAILURE\n')
            self.assertEqual(server.diagnostics.snapshot()['counters']['HTTP_HANDLER_FAILURE'],1)
    def test_incomplete_requests_are_joined_at_shutdown(self):
        server=R2Server(('127.0.0.1',0),R2Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        sockets=[]
        try:
            for _ in range(4):
                c=socket.create_connection(('127.0.0.1',server.server_port),timeout=3);c.sendall(b'GET / HTTP/1.1\r\nHost: ');sockets.append(c)
            deadline=time.monotonic()+3
            while server.diagnostics.snapshot()['active_workers']<4 and time.monotonic()<deadline:time.sleep(.01)
            self.assertEqual(server.diagnostics.snapshot()['active_workers'],4)
            for c in sockets:c.close()
            server.shutdown();server.server_close();thread.join(3)
            self.assertEqual(server.diagnostics.snapshot()['active_workers'],0)
        finally:
            for c in sockets:c.close()
            if thread.is_alive():server.shutdown();server.server_close();thread.join(3)
    def test_stderr_tokens_are_diagnostic_never_waivers(self):
        import subprocess,sys
        from terminan.r2_harness import OwnedChild
        code="import os;os.write(2,b'PRIVATE_SECRET Fatal Python error: _enter_buffered_busy')"
        process=subprocess.Popen([sys.executable,'-c',code],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE);child=OwnedChild(process)
        process.wait(timeout=5);self.assertTrue(child.close())
        data=child.diagnostics();self.assertIn('PYTHON_BUFFERED_IO_SHUTDOWN_FATAL',data['stderr_classes']);self.assertNotIn('PRIVATE_SECRET',str(data));self.assertGreater(child.stderr_bytes,0)
    def test_any_stderr_still_fails_health(self):
        from test_harness_failclosed import FakeRuntime,SHA
        from terminan.r2_harness import Harness
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            runtime=FakeRuntime();runtime.child.stderr_bytes=1
            h=Harness(expected_sha=SHA,evidence_root=Path(td),runtime=runtime)
            self.assertEqual(h.run(),33);self.assertEqual(h.error_class,'CHILD_STDERR')
    def test_metrics_have_fixed_bounded_schema(self):
        from terminan.r2_diagnostics import Diagnostics,validate
        d=Diagnostics()
        for _ in range(1000):d.event('HTTP_PEER_RESET','write')
        self.assertEqual(len(validate(d.snapshot())['events']),16)
        data=d.snapshot();data['events'][0]['elapsed_ms']=float('nan')
        with self.assertRaises(ValueError):validate(data)
    def test_workers_held_open_are_drained_before_close_returns(self):
        class Quick(R2Server):
            def get_request(self):
                client,address=super().get_request();client.settimeout(.3);return client,address
        server=Quick(('127.0.0.1',0),R2Handler);thread=threading.Thread(target=lambda:server.serve_forever(poll_interval=.01),daemon=True);thread.start()
        sockets=[]
        try:
            for _ in range(4):
                c=socket.create_connection(('127.0.0.1',server.server_port),timeout=3);c.sendall(b'GET / HTTP/1.1\r\nHost: ');sockets.append(c)
            deadline=time.monotonic()+2
            while server.diagnostics.snapshot()['active_workers']<4 and time.monotonic()<deadline:time.sleep(.005)
            self.assertEqual(server.diagnostics.snapshot()['active_workers'],4)
            start=time.monotonic();server.shutdown();server.server_close();thread.join(3)
            self.assertGreater(time.monotonic()-start,.1);self.assertLess(time.monotonic()-start,2)
            self.assertEqual(server.diagnostics.snapshot()['active_workers'],0)
            self.assertEqual(server.diagnostics.snapshot()['counters']['HTTP_IO_TIMEOUT'],4)
        finally:
            for client in sockets:client.close()
            if thread.is_alive():server.shutdown();server.server_close();thread.join(3)
    def test_admission_reset_and_failed_thread_start_do_not_leak_slots(self):
        class Socket:
            closed=False
            def sendall(self,body):raise ConnectionResetError('PRIVATE_DSN')
            def shutdown(self,*args):pass
            def close(self):self.closed=True
        server=R2Server(('127.0.0.1',0),R2Handler)
        try:
            for _ in range(16):self.assertTrue(server.slots.acquire(blocking=False))
            client=Socket();server.process_request(client,('127.0.0.1',1));self.assertTrue(client.closed)
            self.assertEqual(server.diagnostics.snapshot()['counters']['HTTP_PEER_RESET'],1)
            for _ in range(16):server.slots.release()
            with patch('threading.Thread.start',side_effect=RuntimeError('PRIVATE_DSN')):
                with self.assertRaises(RuntimeError):server.process_request(Socket(),('127.0.0.1',1))
            self.assertEqual(server.diagnostics.snapshot()['active_workers'],0)
            for _ in range(16):self.assertTrue(server.slots.acquire(blocking=False))
            self.assertFalse(server.slots.acquire(blocking=False))
            for _ in range(16):server.slots.release()
        finally:server.server_close()
    def test_new_runner_requires_final_diagnostics_and_tamper_fails(self):
        from test_harness_failclosed import FakeRuntime,SHA
        from terminan.r2_harness import Harness,inspect_run
        from terminan.r2_diagnostics import Diagnostics
        import tempfile,json,hashlib
        from pathlib import Path
        class Diagnosed(FakeRuntime):
            def spawn(self,repo,ready):
                child=super().spawn(repo,ready);data=json.loads(ready.read_text());data['diagnostics_version']=1;ready.write_text(json.dumps(data))
                old=child.quit
                def quit(timeout):
                    code=old(timeout)
                    self.write_json(ready.with_name('child-diagnostics.json'),dict(version=1,mode='SYNTHETIC',candidate_sha=SHA,shutdown_complete=True,shutdown_elapsed_ms=1,diagnostics=Diagnostics().snapshot()))
                    return code
                child.quit=quit;return child
            def fetch(self,url):
                status,body=super().fetch(url)
                if url.endswith('/api/status'):
                    data=json.loads(body);data['diagnostics']=Diagnostics().snapshot();body=json.dumps(data).encode()
                return status,body
        with tempfile.TemporaryDirectory() as td:
            h=Harness(expected_sha=SHA,evidence_root=Path(td),runtime=Diagnosed());self.assertEqual(h.run(),0)
            self.assertEqual(inspect_run(h.final_dir,SHA),0)
            (h.final_dir/'child-diagnostics.json').unlink()
            entries=[]
            for p in sorted(h.final_dir.iterdir()):
                if p.name!='manifest.json':entries.append(dict(file=p.name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
            (h.final_dir/'manifest.json').write_text(json.dumps(entries))
            self.assertEqual(inspect_run(h.final_dir,SHA),50)
