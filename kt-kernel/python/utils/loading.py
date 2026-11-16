"""Opt-in placement controls for static BF16 inference."""

import os
from pathlib import Path


def socket_numa_leaders(root=Path("/sys/devices/system")):
    groups = {}
    for path in sorted((root / "node").glob("node[0-9]*")):
        cpus = (path / "cpulist").read_text().strip()
        if not cpus:
            continue
        cpu = int(cpus.split(",")[0].split("-")[0])
        socket = int((root / "cpu" / f"cpu{cpu}" / "topology/physical_package_id").read_text())
        groups.setdefault(socket, []).append(int(path.name[4:]))
    if not groups:
        raise ValueError("No CPU socket topology found")
    return [min(groups[key]) for key in sorted(groups)]


def configured_numa_nodes(threadpool_count, numa_nodes):
    if os.environ.get("KT_CPUINFER_SOCKET_LOCAL") != "1":
        return numa_nodes
    leaders = socket_numa_leaders()
    if len(leaders) != threadpool_count:
        raise ValueError("Socket-local inference requires exactly one subpool per CPU socket")
    if numa_nodes is not None and list(numa_nodes) != leaders:
        raise ValueError("Explicit NUMA leaders conflict with socket-local placement")
    return leaders
