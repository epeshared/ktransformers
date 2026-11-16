"""Placement configuration tests that do not import the native extension."""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("loading", Path(__file__).parents[1] / "python/utils/loading.py")
loading = importlib.util.module_from_spec(spec)
spec.loader.exec_module(loading)


class PlacementTests(unittest.TestCase):
    def test_socket_leaders_use_package_ids(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for node, socket in enumerate([0, 0, 0, 1, 1, 1]):
                p = root / "node" / f"node{node}"
                p.mkdir(parents=True)
                (p / "cpulist").write_text(f"{node*8}-{node*8+7}")
                p = root / "cpu" / f"cpu{node*8}" / "topology"
                p.mkdir(parents=True)
                (p / "physical_package_id").write_text(str(socket))
            self.assertEqual(loading.socket_numa_leaders(root), [0, 3])

    def test_opt_in_and_conflicting_configuration(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(loading.configured_numa_nodes(2, [0, 1]), [0, 1])
        with patch.dict(os.environ, {"KT_CPUINFER_SOCKET_LOCAL": "1"}), patch.object(loading, "socket_numa_leaders", return_value=[0, 3]):
            self.assertEqual(loading.configured_numa_nodes(2, None), [0, 3])
            self.assertEqual(loading.configured_numa_nodes(2, [0, 3]), [0, 3])
            with self.assertRaises(ValueError):
                loading.configured_numa_nodes(6, None)
            with self.assertRaises(ValueError):
                loading.configured_numa_nodes(2, [0, 1])


if __name__ == "__main__":
    unittest.main()
