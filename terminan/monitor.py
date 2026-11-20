"""Read-only Unified infrastructure view; no SQL or local host probes."""

def fleet_snapshot():
    return dict(source='unified_system',status='SOURCE_ADAPTER_NOT_CONNECTED',
        nodes=[],online=0,total=0,database_sizes=dict(state='UNAVAILABLE'),
        auxiliary_services=dict(state='UNAVAILABLE'))
