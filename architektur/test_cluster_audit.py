import copy
from pathlib import Path
import unittest

from cluster_audit import compare, declared_inventory, within


class ClusterAuditTests(unittest.TestCase):
    def setUp(self):
        self.declared = {
            "nodes": [{"node": "node-a", "management_ip": "192.0.2.1"}],
            "guests": [{"vmid": 101, "node": "node-a", "type": "qemu"}],
        }
        self.observed = {
            "nodes": {"node-a": {"ip": "192.0.2.1"}},
            "resources": [{"vmid": 101, "node": "node-a", "type": "qemu"}],
            "backup_jobs": [],
        }

    def test_actual_manifests_are_consistent(self):
        inventory = declared_inventory(Path(__file__).resolve().parent.parent)
        self.assertGreater(len(inventory["nodes"]), 0)
        self.assertEqual(len({guest["vmid"] for guest in inventory["guests"]}), len(inventory["guests"]))

    def test_placement_and_missing_guest_drift(self):
        observed = copy.deepcopy(self.observed)
        observed["resources"][0]["node"] = "node-b"
        self.assertEqual(compare(self.declared, observed)["drift"][0]["issue"], "placement")
        observed["resources"] = []
        self.assertEqual(compare(self.declared, observed)["drift"][0]["issue"], "missing_live")

    def test_unmanaged_guest_and_node_address(self):
        observed = copy.deepcopy(self.observed)
        observed["resources"].append({"vmid": 102, "node": "node-a", "type": "lxc"})
        observed["nodes"]["node-a"]["ip"] = "192.0.2.2"
        self.assertEqual({item["issue"] for item in compare(self.declared, observed)["drift"]}, {"undeclared", "management_ip"})

    def test_backup_scope_and_disabled_jobs(self):
        observed = copy.deepcopy(self.observed)
        observed["backup_jobs"] = [{"all": 1, "enabled": 0}, {"all": 1, "node": "node-b"}]
        self.assertEqual(compare(self.declared, observed)["not_in_enabled_backup_jobs"], [101])
        observed["backup_jobs"].append({"enabled": 1, "vmid": "101"})
        self.assertEqual(compare(self.declared, observed)["not_in_enabled_backup_jobs"], [])
        observed["backup_jobs"] = [{"all": 1, "exclude": "101"}]
        self.assertEqual(compare(self.declared, observed)["not_in_enabled_backup_jobs"], [101])

    def test_path_escape_rejected(self):
        with self.assertRaises(ValueError):
            within(Path(__file__).resolve().parent, "../../outside")


if __name__ == "__main__":
    unittest.main()