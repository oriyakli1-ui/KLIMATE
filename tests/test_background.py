import time

import background


def test_background_job_runs_shares_and_survives_errors():
    background.clear()
    calls = []

    def work(progress):
        calls.append(1)
        progress(1, 2)
        progress(2, 2)
        return 42

    job = background.start("k", work)
    for _ in range(100):
        if job.status != "running":
            break
        time.sleep(0.02)
    assert job.status == "done" and job.result == 42 and job.fraction == 1.0
    assert background.start("k", work) is job and len(calls) == 1       # same key: shared, not repeated

    def boom(progress):
        raise ValueError("x")

    bad = background.start("bad", boom)
    for _ in range(100):
        if bad.status != "running":
            break
        time.sleep(0.02)
    assert bad.status == "error" and "ValueError" in bad.error
    assert background.start("bad", lambda p: 1) is not bad                # a failed job may be retried
    background.clear()
