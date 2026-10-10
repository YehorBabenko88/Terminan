"""Read-only Grid fleet telemetry; no local machine probing or database writes."""
from datetime import datetime, timezone
from .data import grid_query

def fleet_snapshot():
    rows=grid_query("SELECT node_id,hostname,last_seen,cpu_pct,ram_pct,disk_free,assigned_symbols FROM nodes ORDER BY node_id LIMIT 200",())
    now=datetime.now(timezone.utc)
    nodes=[]
    for node_id,hostname,last_seen,cpu,ram,disk,symbols in rows:
        if last_seen is not None and last_seen.tzinfo is None:
            last_seen=last_seen.replace(tzinfo=timezone.utc)
        age=max(0,(now-last_seen).total_seconds()) if last_seen else None
        nodes.append(dict(node_id=node_id,hostname=hostname,last_seen=last_seen.isoformat() if last_seen else None,age_seconds=round(age,1) if age is not None else None,online=age is not None and age<=120,cpu_pct=float(cpu) if cpu is not None else None,ram_pct=float(ram) if ram is not None else None,disk_free_bytes=int(disk) if disk is not None else None,assigned_symbols=int(symbols or 0)))
    return dict(source='cluster-grid.nodes',nodes=nodes,online=sum(n['online'] for n in nodes),total=len(nodes),database_sizes=dict(state='NOT_EXPOSED_BY_SOURCE'),auxiliary_services=dict(state='NOT_EXPOSED_BY_SOURCE'))
