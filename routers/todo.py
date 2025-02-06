from http.client import HTTPException
from fastapi import  Depends, Path, APIRouter
from numpy.testing.print_coercion_tables import print_new_cast_table
from pydantic import BaseModel,Field
from starlette import status
from fastapi.requests import Request
from starlette.responses import RedirectResponse
from fastapi.exceptions import HTTPException
from database import engine, SessionLocal
from models import Base, Todo
from sqlalchemy.orm import Session
from typing import Annotated
from routers.auth import get_current_user
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv   #.env içindeki api key i diğer yerlerde kullanılabilir yap
import google.generativeai as genai
import os
from langchain_core.messages import HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
import markdown
from bs4 import BeautifulSoup #html i parse eden bir kütüphane


router = APIRouter(
    prefix="/todo",
    tags=["Todo"],
)

templates = Jinja2Templates(directory="templates")

class ToDoRequest(BaseModel):
    title: str = Field( min_length=3, max_length=50)
    description: str = Field( min_length=3, max_length=1000)
    priority: int = Field(ge=1, le= 5)
    complete: bool



def get_db():
    db = SessionLocal()
    try:
        yield db    # kullanıldığı fonk generator func. denir. returndan farkı birden fazla seq döndürebilir.
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]

#ilk sayfaları tanımla

def redirect_to_login():
    redirect_response = RedirectResponse(url="/auth/login-page")
    redirect_response.delete_cookie("access_token")
    return redirect_response



@router.get("/todo-page")
async def render_todo_page(request : Request, db : db_dependency):
   try:
        user = await get_current_user(request.cookies.get("access_token"))
        if user is None:
            return redirect_to_login()
        todos = db.query(Todo).filter(Todo.owner_id == user.get('id')).all
        return templates.TemplateResponse("todo.html", {"request": request, "todos" : todos, "user": user})
   except:
       return redirect_to_login()


@router.get("/add-todo-page")
async def render_add_todo_page(request : Request):
   try:
        user = await get_current_user(request.cookies.get("access_token"))
        if user is None:
            return redirect_to_login()
        return templates.TemplateResponse("todo.html", {"request": request, "user": user})
   except:
       return redirect_to_login()

@router.get("/edit-todo-page/{todo_id}")
async def render_todo_page(request : Request, db : db_dependency, todo_id : int):
   try:
        user = await get_current_user(request.cookies.get("access_token"))
        if user is None:
            return redirect_to_login()
        todos = db.query(Todo).filter(Todo.id == todo_id).first()
        return templates.TemplateResponse("edit-todo.html", {"request": request, "todos" : todos, "user": user})
   except:
       return redirect_to_login()


@router.get("/")
async def read_all(user: user_dependency,db: db_dependency):
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)
    return db.query(Todo).filter(Todo.owner_id == user.get('id')).all

@router.get("/todo/{todo_id}", status_code=status.HTTP_200_OK)
async def read_by_id(user: user_dependency,db: db_dependency, todo_id : int = Path(gt=0)):
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)
    todo = db.query(Todo).filter(Todo.id == todo_id).filter(Todo.owner_id == user.get('id')).first #ekstra güvenlik filtresi
    if todo is not None:
        return  todo
    raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail = "Todo not found")


#post metodu üret
@router.post("/todo", status_code= status.HTTP_201_CREATED)
async def create_todo(user : user_dependency,db: db_dependency, todo_request :ToDoRequest):
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)
    todo = Todo(**todo_request.dict(), owner_id= user.get('id'))
    todo.description = create_todo_with_gemini(todo.description)
    db.add(todo)
    db.commit()
    return {"message": "Todo created successfully"}

@router.put("/todo/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_todo(user: user_dependency,db : db_dependency, todo_request : ToDoRequest, todo_id : int = Path(gt=0)):
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)
    todo = db.query(Todo).filter(Todo.id == todo_id).filter(Todo.owner_id == user.get('id')).first
    if todo is None:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND)

    todo.title = ToDoRequest.title
    todo.description = ToDoRequest.description
    todo.priority = ToDoRequest.priority
    todo.complete = ToDoRequest.complete

    db.add(todo)
    db.commit()


@router.delete("/todo/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo( user: user_dependency,db : db_dependency, todo_id : int = Path(gt=0)):
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)
    todo = db.query(Todo).filter(Todo.id == todo_id).filter(Todo.owner_id == user.get('id')).first
    if todo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    #db.query(Todo).filter(Todo.id == todo_id)
    db.delete(todo)
    db.commit()


def markdown_to_text(markdown_string):   #markdown çıktısı veren her yerde kullanabilirsin
    html = markdown.markdown(markdown_string)
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text()
    return text


def create_todo_with_gemini(todo_string : str):
    load_dotenv()
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    llm = ChatGoogleGenerativeAI(model="gemini-pro")
    response = llm.invoke(
        [
            HumanMessage(content="I will provide you a todo item yo add my to do list.What i want you to do is to create a longer description of that todo item, my next message will be my todo:"),
            HumanMessage(content=todo_string)
        ]
    )
    return  markdown_to_text(response.content)

if __name__ == "__main__":
    print(create_todo_with_gemini("learn python"))

'''
from typing import Annotated
from fastapi import FastAPI,Depends
def hello_world():
    return "Hello, welcome the FastAPI"

HelloDependency = Annotated[str, Depends(hello_world)]


def get_hello_world(hello: str = Depends(hello_world)):
    return f"Hello world service : {hello_world()}"

def get_hello_world_2(hello: str = HelloDependency):
    return f"Hello world service 2 : {hello}"

@app.get("/hello")
def hello(message: str = Depends(get_hello_world)):
    return {"message": message}
'''