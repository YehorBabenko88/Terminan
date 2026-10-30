"""Disposable contract-only server. Never enables an engine, DB or trading."""
import os
for key in list(os.environ):
    if key.startswith('TERMINAN_'):del os.environ[key]
os.environ['TERMINAN_UNIFIED_CONTRACT_IMPORT']='1'
exec(compile(open('scripts/math_lab_test_server.py',encoding='utf-8').read(),'scripts/math_lab_test_server.py','exec'))
