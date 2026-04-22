import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".roxy"))

from citadel_contracts import build_citadel_registry


def test_registry_adds_endpoint_reachability_metadata():
    registry = build_citadel_registry(current_hostname="macpro-linux")
    machines = {machine["machine_id"]: machine for machine in registry["machines"]}

    roxy_machine = machines["roxy-macpro"]
    roxy_core_meta = roxy_machine["control_endpoint_meta"]["roxy_core"]
    assert roxy_core_meta["url"] == "http://127.0.0.1:8766"
    assert roxy_core_meta["bind_scope"] == "localhost"
    assert roxy_core_meta["reachable_from"] == ["same_machine"]

    mac_machine = machines["mac-studio"]
    operator_meta = mac_machine["control_endpoint_meta"]["operator_briefing"]
    assert operator_meta["url"] == "http://127.0.0.1:3847/api/operator/briefing"
    assert operator_meta["scheme"] == "http"
    assert operator_meta["host"] == "127.0.0.1"
    assert operator_meta["port"] == 3847
    assert operator_meta["bind_scope"] == "localhost"
