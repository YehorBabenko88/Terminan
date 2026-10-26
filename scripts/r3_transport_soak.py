"""Real-time owned-child transport soak; synthetic loopback only, no browser/DB sources."""
import argparse,http.client,json,os,socket,struct,sys,threading
from pathlib import Path
REPO=Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:sys.path.insert(0,str(REPO))
from terminan.r2_harness import Harness,Fault,inspect_run

class TransportHarness(Harness):
    def __init__(self,**kwargs):
        super().__init__(**kwargs);self.traffic={'resets_sent':0,'valid_frames':0,'failures':0};self.stop=threading.Event()
    def _health(self):
        super()._health()
        if self.traffic['failures']:raise Fault('CHILD_HEALTH_FAILED')
    def _review(self):
        port=int(self.url.rsplit(':',1)[1])
        def traffic():
            index=0
            while not self.stop.is_set():
                try:
                    with socket.create_connection(('127.0.0.1',port),timeout=3) as client:
                        client.sendall(f'GET /api/synthetic/frame?step=600 HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n\r\n'.encode('ascii'))
                        client.setsockopt(socket.SOL_SOCKET,socket.SO_LINGER,struct.pack('hh' if os.name=='nt' else 'ii',1,0))
                    self.traffic['resets_sent']+=1
                    symbol=('BTCUSDT','ETHUSDT','SOLUSDT')[index%3]
                    status,body=self.ops.fetch(self.url+f'/api/synthetic/frame?step={index%601}&symbol={symbol}&scenario=mixed')
                    frame=json.loads(body)
                    if status!=200 or frame.get('mode')!='SYNTHETIC' or frame.get('symbol')!=symbol or frame.get('candidate_sha')!=self.expected or frame.get('execution')!='DISABLED':raise ValueError()
                    self.traffic['valid_frames']+=1;index+=1
                except Exception:self.traffic['failures']+=1;return
                self.stop.wait(.25)
        worker=threading.Thread(target=traffic,daemon=False);worker.start()
        failed=False
        try:super()._review()
        except BaseException:failed=True;raise
        finally:
            self.stop.set();worker.join(8)
            if not failed and (worker.is_alive() or self.traffic['failures']):raise Fault('CHILD_HEALTH_FAILED')
        if self.traffic['resets_sent']<1 or self.traffic['valid_frames']<1:raise Fault('CHILD_HEALTH_FAILED')
    def _summary(self):
        value=super()._summary();value['transport_soak']=self.traffic.copy();return value

def main():
    p=argparse.ArgumentParser();p.add_argument('--expected-sha',required=True);p.add_argument('--seconds',choices=['15','600'],required=True);p.add_argument('--evidence-root',required=True);args=p.parse_args()
    harness=TransportHarness(expected_sha=args.expected_sha,evidence_root=args.evidence_root,review_seconds=args.seconds)
    code=harness.run();evidence=inspect_run(harness.final_dir,args.expected_sha)
    if evidence!=code:code=50
    print(json.dumps(dict(exit_code=code,evidence_exit=evidence,run_id=harness.run_id,error_class=harness.error_class,physical='PENDING')))
    return code
if __name__=='__main__':
    try:raise SystemExit(main())
    except (Exception,KeyboardInterrupt):print('TRANSPORT_SOAK FAIL error_class=DRIVER_FAILURE');raise SystemExit(50)
