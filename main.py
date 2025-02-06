from fastapi import FastAPI, Depends, Path
from fastapi.staticfiles import StaticFiles
from starlette import status
from starlette.responses import RedirectResponse

from database import engine, SessionLocal
from models import Base
from routers.auth import router as auth_router
from routers.todo import router as todo_router

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_root():
    return RedirectResponse(url="/todo/todo-page",status_code=status.HTTP_302_FOUND)


app.include_router(auth_router)
app.include_router(todo_router)


Base.metadata.create_all(bind=engine)
