"""Read-only Grid fleet telemetry; no local machine probing or database writes."""
from datetime import datetime, timezone
from .data import grid_query

def fleet_snapshot():
    from .g0_sources import snapshot
    view=snapshot('health','BTCUSDT')
    if view['state'] in ('INVALID_DATA','SCHEMA_MISMATCH','UNAVAILABLE'):raise RuntimeError('source unavailable')
    nodes=[]
    for row in view['rows']:
        nodes.append(dict(node_id=row['node_id'],hostname=None,last_seen=datetime.fromtimestamp(row['t']/1000,timezone.utc).isoformat(),age_seconds=row['age_seconds'],online=row['online'],cpu_pct=row['cpu'],ram_pct=row['ram'],disk_free_bytes=row['disk'],assigned_symbols=row['symbols']))
    return dict(source='cluster-grid.nodes',state=view['state'],provenance=view['provenance'],nodes=nodes,online=sum(n['online'] for n in nodes),total=len(nodes),database_sizes=dict(state='NOT_EXPOSED_BY_SOURCE'),auxiliary_services=dict(state='NOT_EXPOSED_BY_SOURCE'))
