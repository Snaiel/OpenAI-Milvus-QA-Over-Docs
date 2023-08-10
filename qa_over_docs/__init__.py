from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
import os, json


UPLOAD_FOLDER = 'uploads/'
ALLOWED_EXTENSIONS = {'pdf', 'csv'}
CONTEXT_FILE = "context.json"
SOURCES_FILE = "sources.txt"


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = 'a super secret key'
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///project.db"
app.debug = True

r_db = SQLAlchemy(app)
socketio = SocketIO(app)


if not os.path.exists(UPLOAD_FOLDER):
    os.mkdir(UPLOAD_FOLDER)

context: dict

if os.path.exists(CONTEXT_FILE):
    with open(CONTEXT_FILE) as file:
        context = json.load(file)

        if os.path.exists(SOURCES_FILE):
            with open(SOURCES_FILE) as sources_file:
                # print(list(map(lambda e: e.strip(), sources_file.readlines())))
                context["sources"] = list(map(lambda e: e.strip(), sources_file.readlines()))
else:
    context = {
        "chat_items": [],
        "waiting": False,
        "response_time": None,
        "collection_exists": False,
        "sources_to_add": [],
        "sources": [],
        "processing_sources": False
    }

def save_context():
    with open(CONTEXT_FILE, 'w' if os.path.exists(CONTEXT_FILE) else 'x') as file:
        new_context = context.copy()
        new_context["chat_items"] = []
        new_context["response_time"] = None
        new_context["waiting"] = False
        json.dump(new_context, file, indent=4)
    with open(SOURCES_FILE, 'w' if os.path.exists(SOURCES_FILE) else 'x') as file:
        file.write("\n".join(context["sources"]))


from qa_over_docs.apis.base import BaseAPI
from qa_over_docs.apis.openai import OpenAI

api: BaseAPI = OpenAI()


from qa_over_docs.views import chat, sources