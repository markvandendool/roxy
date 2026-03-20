import asyncio
import json

import background_scheduler


def test_scheduler_executes_sync_handler():
    scheduler = background_scheduler.BackgroundScheduler()
    task = background_scheduler.ScheduledTask(
        name="sync-test",
        interval_seconds=60,
        handler=lambda: "ok",
        timeout_seconds=5,
    )

    result = asyncio.run(scheduler._execute_task(task))

    assert result.success is True
    assert result.output == "ok"


def test_scheduler_writes_heartbeat_and_lease(tmp_path, monkeypatch):
    monkeypatch.setattr(background_scheduler, "SCHEDULER_HEARTBEAT", tmp_path / "heartbeat.json")
    monkeypatch.setattr(background_scheduler, "SCHEDULER_LEASE", tmp_path / "lease.json")

    scheduler = background_scheduler.BackgroundScheduler()
    scheduler._write_runtime_files(status="running")

    assert background_scheduler.SCHEDULER_HEARTBEAT.exists()
    assert background_scheduler.SCHEDULER_LEASE.exists()

    heartbeat = json.loads(background_scheduler.SCHEDULER_HEARTBEAT.read_text())
    lease = json.loads(background_scheduler.SCHEDULER_LEASE.read_text())

    assert heartbeat["instance_id"] == scheduler.instance_id
    assert lease["instance_id"] == scheduler.instance_id
    assert heartbeat["status"] == "running"


def test_setup_scheduler_registers_skoreq_sync_handler():
    scheduler = background_scheduler.BackgroundScheduler()
    scheduler.tasks["sync_skoreq_status"].enabled = False
    scheduler.tasks["sync_skoreq_status"].error_count = 3
    background_scheduler.setup_scheduler(scheduler)

    assert scheduler.tasks["sync_skoreq_status"].handler is not None
    assert scheduler.tasks["sync_skoreq_status"].enabled is True
    assert scheduler.tasks["sync_skoreq_status"].error_count == 0
