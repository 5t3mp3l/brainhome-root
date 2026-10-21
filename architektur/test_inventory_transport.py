import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


LIBRARY = Path(__file__).resolve().parent.parent / "tools/lib"
sys.path.insert(0, str(LIBRARY))
SPEC = importlib.util.spec_from_file_location("inventory_manager", LIBRARY / "inventory-manager.py")
MANAGER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MANAGER)


class InventoryTransportTests(unittest.TestCase):
    def test_local_pvesh_is_preserved(self):
        command = ["pvesh", "get", "/nodes", "--output-format", "json"]
        with patch.dict(MANAGER.os.environ, {"BRAINHOME_PROXMOX_SSH": ""}), patch.object(MANAGER.shutil, "which", return_value="/usr/bin/pvesh"), patch.object(MANAGER, "run_cmd", return_value=(0, "[]", "")) as run:
            self.assertTrue(MANAGER.run_json(command)[0])
            run.assert_called_once_with(command, timeout=12)

    def test_missing_pvesh_uses_known_ssh_host(self):
        with patch.dict(MANAGER.os.environ, {"BRAINHOME_PROXMOX_SSH": ""}), patch.object(MANAGER.shutil, "which", return_value=None), patch.object(MANAGER, "run_cmd", return_value=(0, "[]", "")) as run:
            self.assertTrue(MANAGER.run_json(["pvesh", "get", "/nodes"])[0])
            command = run.call_args.args[0]
            self.assertEqual(command[-2:], ["proxmox-ug", "pvesh get /nodes"])
            self.assertIn("StrictHostKeyChecking=yes", command)
            self.assertIn("BatchMode=yes", command)

    def test_explicit_host_and_remote_argument_quoting(self):
        with patch.dict(MANAGER.os.environ, {"BRAINHOME_PROXMOX_SSH": "root@192.0.2.1"}), patch.object(MANAGER, "run_cmd", return_value=(0, "[]", "")) as run:
            self.assertTrue(MANAGER.run_json(["pvesh", "get", "/nodes", "--test", "a;b"])[0])
            self.assertEqual(run.call_args.args[0][-2:], ["root@192.0.2.1", "pvesh get /nodes --test 'a;b'"])

    def test_bad_host_and_remote_writes_rejected(self):
        for host, command in (
            ("-oProxyCommand=bad", ["pvesh", "get", "/nodes"]),
            ("proxmox-ug", ["pvesh", "set", "/nodes"]),
        ):
            with self.subTest(host=host), patch.dict(MANAGER.os.environ, {"BRAINHOME_PROXMOX_SSH": host}), patch.object(MANAGER, "run_cmd") as run:
                self.assertFalse(MANAGER.run_json(command)[0])
                run.assert_not_called()

    def test_transport_and_json_failures_remain_errors(self):
        with patch.dict(MANAGER.os.environ, {"BRAINHOME_PROXMOX_SSH": "proxmox-ug"}):
            for result in ((255, "", "SSH denied"), (0, "not json", "")):
                with self.subTest(result=result), patch.object(MANAGER, "run_cmd", return_value=result):
                    self.assertFalse(MANAGER.run_json(["pvesh", "get", "/nodes"])[0])

    def test_override_addresses_match_manifests(self):
        from cluster_audit import declared_inventory
        declared = declared_inventory(LIBRARY.parent.parent)
        overrides = json.loads(MANAGER.OVERRIDES_JSON.read_text())
        for guest in declared["guests"]:
            if guest.get("address"):
                self.assertEqual(overrides["guests"][str(guest["vmid"])]["ip"], guest["address"])
        for node in declared["nodes"]:
            self.assertEqual(overrides["nodes"][node["node"]]["ip"], node["management_ip"])


if __name__ == "__main__":
    unittest.main()