def register(scheduler):
    scheduler.add_job(run_triage_agent, "cron", hour=3)
