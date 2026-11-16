#pragma once

#include <hwloc.h>
#include <cstdlib>
#include <cstring>
#include <stdexcept>

namespace kt_loading {
inline bool socket_local() {
  const char* value = std::getenv("KT_CPUINFER_SOCKET_LOCAL");
  return value && std::strcmp(value, "1") == 0;
}

inline hwloc_obj_t socket_for_node(hwloc_topology_t topology, unsigned node_id) {
  hwloc_obj_t node = nullptr;
  while ((node = hwloc_get_next_obj_by_type(topology, HWLOC_OBJ_NUMANODE, node))) {
    if (node->os_index != node_id) continue;
    hwloc_obj_t package = nullptr;
    while ((package = hwloc_get_next_obj_by_type(topology, HWLOC_OBJ_PACKAGE, package))) {
      if (hwloc_bitmap_isincluded(node->cpuset, package->cpuset)) return package;
    }
  }
  throw std::runtime_error("Cannot resolve the CPU socket for the requested NUMA node");
}

inline void bind_socket(int node_id, bool bind_cpu) {
  hwloc_topology_t topology;
  if (hwloc_topology_init(&topology) || hwloc_topology_load(topology)) {
    throw std::runtime_error("Cannot load the socket-local hwloc topology");
  }
  try {
    auto package = socket_for_node(topology, node_id);
    if (bind_cpu) {
      auto allowed = hwloc_bitmap_dup(package->cpuset);
      hwloc_bitmap_and(allowed, allowed, hwloc_topology_get_allowed_cpuset(topology));
      int code = hwloc_bitmap_iszero(allowed) ? -1 : hwloc_set_cpubind(topology, allowed, HWLOC_CPUBIND_THREAD);
      hwloc_bitmap_free(allowed);
      if (code) throw std::runtime_error("Cannot bind CPU workers to their requested socket");
    }
    // MPOL_BIND over one package's nodes permits local-first fallback within
    // that package. This is deliberately not a machine-wide interleave policy.
    if (hwloc_set_membind(topology, package->nodeset, HWLOC_MEMBIND_BIND,
                         HWLOC_MEMBIND_THREAD | HWLOC_MEMBIND_STRICT | HWLOC_MEMBIND_BYNODESET)) {
      throw std::runtime_error("Cannot bind worker memory to its CPU socket");
    }
  } catch (...) {
    hwloc_topology_destroy(topology);
    throw;
  }
  hwloc_topology_destroy(topology);
}
}  // namespace kt_loading
