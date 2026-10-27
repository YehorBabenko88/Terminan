"""Opt-in Supervisor read-only status consumer; no execution authority."""
import http.client
import json
import os
import socket
import threading
import time

def supervisor_status():
    unavailable={"state":"UNAVAILABLE","reason":"SUPERVISOR_NOT_CONFIGURED",
                 "provenance":"UNVERIFIED","trading_authorized":False}
    raw=os.environ.get("TERMINAN_SUPERVISOR_CONTRACT_PORT","")
    if not raw:
        return unavailable
    if not raw.isascii() or not raw.isdecimal() or len(raw)>5 or not 1<=int(raw)<=65535:
        return dict(unavailable,reason="INVALID_LOOPBACK_PORT")
    connection=None
    timer=None
    try:
        deadline=time.monotonic()+5.0
        connection=http.client.HTTPConnection("127.0.0.1",int(raw),timeout=0.25)
        def expire():
            sock=connection.sock
            if sock is not None:
                try:sock.shutdown(socket.SHUT_RDWR)
                except OSError:pass
                try:sock.close()
                except OSError:pass
        timer=threading.Timer(max(0,deadline-time.monotonic()),expire)
        timer.daemon=True
        timer.start()
        connection.request("GET","/internal/v1/health",headers={"Accept":"application/json"})
        if time.monotonic()>=deadline:raise ValueError("deadline")
        response=connection.getresponse()
        if time.monotonic()>=deadline:raise ValueError("deadline")
        if response.status not in (200,503):
            raise ValueError("invalid status")
        if response.getheader("Content-Length") and int(response.getheader("Content-Length"))>8192:
            raise ValueError("oversized")
        body=bytearray()
        while True:
            remaining=deadline-time.monotonic()
            if remaining<=0:raise ValueError("deadline")
            if connection.sock is not None:connection.sock.settimeout(min(0.25,remaining))
            chunk=response.read1(min(4096,8193-len(body)))
            if not chunk:break
            body.extend(chunk)
            if len(body)>8192:raise ValueError("oversized")
        if len(body)>8192:
            raise ValueError("oversized")
        payload=json.loads(body,parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        version=payload.get("api_version")
        if not isinstance(version,dict) or type(version.get("major")) is not int or type(version.get("minor")) is not int or version!={"major":1,"minor":0}:
            raise ValueError("version mismatch")
        if payload.get("producer")!="unified-system" or payload.get("read_only") is not True or payload.get("trading_authorized") is not False or payload.get("physical_acceptance")!="NOT_RUN":
            raise ValueError("identity or authority mismatch")
        if payload.get("status") not in ("AVAILABLE","UNAVAILABLE") or (response.status==503 and payload["status"]!="UNAVAILABLE"):
            raise ValueError("status mismatch")
        state=payload.get("state","UNAVAILABLE")
        if (response.status==200 and payload["status"]!="AVAILABLE") or (response.status==503 and state!="UNAVAILABLE"):\n            raise ValueError("HTTP status/state mismatch")\n        if state not in ("INSTALLED","INFRA_READY","HANDOFF_VERIFIED","OBSERVING","DEGRADED","BLOCKED","UNAVAILABLE"):
            raise ValueError("unknown state")
        return {"state":state if response.status==200 else "UNAVAILABLE",
                "reason":"SOURCE_PROVENANCE_UNVERIFIED",
                "provenance":"UNVERIFIED","trading_authorized":False}
    except (OSError,ValueError,TypeError,AttributeError,http.client.HTTPException):
        return dict(unavailable,reason="SUPERVISOR_CONTRACT_INVALID_OR_UNAVAILABLE")
    finally:
        if timer is not None:
            timer.cancel()
            timer.join()
        if connection is not None:connection.close()
