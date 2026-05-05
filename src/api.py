from fastapi import FastAPI, BackgroundTasks

from .worker import main_loop

app = FastAPI()


@app.post("/trigger/fetch")
def trigger_fetch(background_tasks: BackgroundTasks, fast_filter: bool = False):
    # Run fetch in background to avoid API timeout
    background_tasks.add_task(main_loop, fast_filter=fast_filter)
    return {"status": "ok", "message": f"Fetch process started in background (fast_filter={fast_filter})."}
