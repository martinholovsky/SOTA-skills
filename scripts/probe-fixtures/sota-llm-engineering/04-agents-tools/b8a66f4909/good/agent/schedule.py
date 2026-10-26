def register(scheduler):
    scheduler.add_job(authorize_trigger(run_triage_agent, "nightly-triage"), "cron", hour=3)
