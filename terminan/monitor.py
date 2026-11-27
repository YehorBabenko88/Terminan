"""Read-only Grid fleet telemetry; no local machine probing or database writes."""
from datetime import datetime, timezone
from os import environ

from .data import read_source

def fleet_snapshot():
    gateway = environ.get('TERMINAN_GRID_URL')
    rows = []
    if gateway:
        snapshot = read_source(gateway, '/v1/nodes', {})
        if not isinstance(snapshot, dict) or snapshot.get('version') != 1 or not isinstance(snapshot.get('nodes'), list):
            raise RuntimeError('Unexpected Grid nodes DTO')
        rows = snapshot['nodes']
    now=datetime.now(timezone.utc)
    nodes=[]
    for row in rows:
        last_seen = datetime.fromisoformat(row['last_seen']) if row['last_seen'] else None
        if last_seen is not None and last_seen.tzinfo is None:
            raise RuntimeError('Grid node timestamp has no timezone')
        age=max(0,(now-last_seen).total_seconds()) if last_seen else None
        nodes.append({**row, 'last_seen': last_seen.astimezone(timezone.utc).isoformat() if last_seen else None,
                      'age_seconds': round(age, 1) if age is not None else None,
                      'online': age is not None and age <= 120, 'assigned_symbols': row['assigned_symbols'] or 0})
    return dict(source='cluster-grid.nodes',nodes=nodes,online=sum(n['online'] for n in nodes),total=len(nodes),database_sizes=dict(state='NOT_EXPOSED_BY_SOURCE'),auxiliary_services=dict(state='NOT_EXPOSED_BY_SOURCE'))
