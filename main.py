from fastapi import FastAPI, HTTPException
from typing import List, Optional
from pydantic import BaseModel, Field
import uuid
from datetime import datetime, timedelta

app = FastAPI()

class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=300)
    status: str = Field("To Do")

class PomodoroSession(BaseModel):
    taskid: str
    start_time: datetime
    end_time: datetime
    completed: bool

tasks: List[Task] = []
pomodoro_timers: List[PomodoroSession] = []
pomodoro_sessions: List[PomodoroSession] = []

@app.post("/tasks")
def create_task(task: Task):
    allowed_statuses = ["To Do", "Doing", "Done"]

    if any(existing_task.title == task.title for existing_task in tasks):
        raise HTTPException(status_code=400, detail="Task title has to be unique")

    if task.status not in allowed_statuses:
        raise HTTPException(status_code=400, detail=f"Status has to be one of: {', '.join(allowed_statuses)}")
    tasks.append(task)
    return task

@app.get("/tasks")
def get_tasks(filter_status: Optional[str] = None):
    if filter_status:
        return [task for task in tasks if task.status == filter_status]
    return tasks

@app.get("/tasks/{task_id}")
def task_info(task_id: str):
    for task in tasks:
        if task.id == task_id:
            return task
    raise HTTPException(status_code=404, detail="Task with given ID doesn't exist")

@app.put("/tasks/{task_id}")
def update_task(task_id: str, title: str, description: str, status: str):
    allowed_statuses = ["To Do", "Doing", "Done"]

    for task in tasks:
        if task.id == task_id:
            if any(existing_task.title == title and existing_task.id != task_id for existing_task in tasks):
                raise HTTPException(status_code=400, detail="Task title has to be unique")

            if status not in allowed_statuses:
                raise HTTPException(status_code=400, detail=f"Status has to be one of: {', '.join(allowed_statuses)}")

            task.title = title
            task.description = description
            task.status = status
            return task

    raise HTTPException(status_code=404, detail="Task with given ID doesn't exist")

@app.delete("/tasks/{task_id}")
def delete_task(task_id: str):
    for task in tasks:
        if task.id == task_id:
            tasks.remove(task)
            return {"message": f"Task {task_id} has been deleted"}

    raise HTTPException(status_code=404, detail="Task with given ID doesn't exist")

@app.post("/pomodoro")
def create_pomodoro_timer(task_id: str, duration: int = 25):
    if any(timer.taskid == task_id for timer in pomodoro_timers):
        raise HTTPException(status_code=400, detail="Task already has an active pomodoro timer")

    for task in tasks:
        if task.id == task_id:
            start_time = datetime.now()
            end_time = start_time + timedelta(minutes=duration)
            session = PomodoroSession(taskid=task_id, start_time=start_time, end_time=end_time, completed=False)
            pomodoro_sessions.append(session)
            pomodoro_timers.append(session)
            return session

    raise HTTPException(status_code=404, detail="Task with given ID doesn't exist")

@app.post("/pomodoro/{task_id}/stop")
def stop_pomodoro_timer(task_id: str):
    for timer in pomodoro_timers:
        if timer.taskid == task_id:
            pomodoro_timers.remove(timer)

    for session in pomodoro_sessions:
        if session.taskid == task_id and not session.completed:
            session.completed = True
            return {"message": "Pomodoro timer has been stopped"}

    raise HTTPException(status_code=404, detail="Active timer for given task doesn't exist")

@app.get("/pomodoro/stats")
def get_pomodoro_stats():
    total_time = 0
    stats = {}

    for session in pomodoro_sessions:
        if session.completed:
            duration = (session.end_time - session.start_time).total_seconds() / 60
            total_time += duration
            stats[session.taskid] = stats.get(session.taskid, 0) + 1

    return {"completed_sessions": stats, "total_time_in_minutes": total_time}