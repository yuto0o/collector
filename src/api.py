from fastapi import FastAPI

from .worker import main_loop

app = FastAPI()


@app.post("/trigger/fetch")
def trigger_fetch():
    # For simplicity, run fetch in background (sync)
    main_loop()
    return {"status": "ok"}
