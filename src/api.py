from fastapi import FastAPI, BackgroundTasks

from .worker import main_loop

app = FastAPI()


@app.post("/trigger/fetch")
def trigger_fetch(background_tasks: BackgroundTasks):
    # Run fetch in background to avoid API timeout
    background_tasks.add_task(main_loop)
    return {"status": "ok", "message": "Fetch process started in background."}
