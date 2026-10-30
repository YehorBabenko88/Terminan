"""Read-only Grid fleet telemetry; no local machine probing or writes."""
import math
from datetime import datetime, timezone
from .data import grid_query


def _percent(value):
    if value is None:
        return None
    if type(value) not in (int, float):
        # Decimal returned by database drivers is accepted via float conversion.
        try:
            value = float(value)
        except (TypeError, ValueError, OverflowError):
            raise ValueError("invalid telemetry percentage") from None
    value = float(value)
    if not math.isfinite(value) or not 0 <= value <= 100:
        raise ValueError("invalid telemetry percentage")
    return value


def fleet_snapshot():
    rows = grid_query(
        "SELECT node_id,hostname,last_seen,cpu_pct,ram_pct,disk_free,assigned_symbols "
        "FROM nodes ORDER BY node_id LIMIT 200", ()
    )
    now = datetime.now(timezone.utc)
    nodes = []
    for node_id, hostname, last_seen, cpu, ram, disk, symbols in rows:
        if last_seen is not None:
            if not isinstance(last_seen, datetime):
                raise ValueError("invalid node timestamp")
            if last_seen.tzinfo is None:
                last_seen = last_seen.replace(tzinfo=timezone.utc)
            else:
                last_seen = last_seen.astimezone(timezone.utc)
            age = (now - last_seen).total_seconds()
            # Future timestamps cannot establish node liveness.
            if not math.isfinite(age) or age < 0:
                age = None
        else:
            age = None
        if disk is not None and (type(disk) is bool or int(disk) < 0):
            raise ValueError("invalid disk telemetry")
        if type(symbols) is bool or int(symbols or 0) < 0:
            raise ValueError("invalid symbol count")
        nodes.append(dict(
            node_id=node_id, hostname=hostname,
            last_seen=last_seen.isoformat() if last_seen else None,
            age_seconds=round(age, 1) if age is not None else None,
            online=age is not None and age <= 120,
            cpu_pct=_percent(cpu), ram_pct=_percent(ram),
            disk_free_bytes=int(disk) if disk is not None else None,
            assigned_symbols=int(symbols or 0)
        ))
    return dict(
        source="cluster-grid.nodes", nodes=nodes,
        online=sum(node["online"] for node in nodes), total=len(nodes),
        database_sizes=dict(state="NOT_EXPOSED_BY_SOURCE"),
        auxiliary_services=dict(state="NOT_EXPOSED_BY_SOURCE")
    )
