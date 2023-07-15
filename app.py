from flask import Flask, render_template, request, redirect, flash, url_for
from flask_socketio import SocketIO
from threading import Thread
from time import time, sleep
from werkzeug.utils import secure_filename
import os, json

from api import retrieve_response
import db

UPLOAD_FOLDER = 'uploads/'
ALLOWED_EXTENSIONS = {'pdf', 'csv'}
CONTEXT_FILE = "context.json"

class Message():
    def __init__(self, message: str, type: str) -> None:
        self.message = message
        self.type = type

    def __str__(self) -> str:
        return self.message

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = 'a super secret key'
app.debug = True
socketio = SocketIO(app)

if os.path.exists(CONTEXT_FILE):
    with open(CONTEXT_FILE) as file:
        context = json.load(file)
else:
    context = {
        "chat_items": [],
        "waiting": False,
        "response_time": None,
        "collection_exists": False,
        "sources_to_add": []
    }

def save_context():
    with open(CONTEXT_FILE, 'w' if os.path.exists(CONTEXT_FILE) else 'x') as file:
        saved_context = context.copy()
        saved_context["sources_to_add"] = []
        json.dump(context, file, indent=4)

@app.route("/", methods=['GET', 'POST'])
def home():
    save_context()
    if request.method == 'POST':
        context["response_time"] = None
        user_input = request.form['user_input']
        context["chat_items"].append(Message(user_input, "user"))
        thread = Thread(target=response, args=(user_input,))
        thread.start()
        context["waiting"] = True
    return render_template("index.html", **context)

@app.route('/create_collection')
def create_collection():
    if not db.collection_exists():
        db.create_collection()
    context["collection_exists"] = True
    flash("Collection successfully created", "success")
    return redirect("/")

def allowed_file(filename):
    return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/include_source", methods=['GET', 'POST'])
def include_source():
    if request.method == 'POST':
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            context["sources_to_add"].append(request.form["include-url"])
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            context["sources_to_add"].append(filename)
    return redirect("/")

@app.route("/delete_collection")
def delete_collection():
    db.delete_collection()
    if os.path.exists(CONTEXT_FILE):
        os.remove(CONTEXT_FILE)
    context["collection_exists"] = False
    flash("Collection successfully deleted", "primary")
    return redirect("/")

def response(user_input: str):
    st = time()
    sleep(0.1)

    context["chat_items"].append(Message(retrieve_response(user_input), "response"))

    context["waiting"] = False

    sleep(0.2)
    et = time()

    response_time = et - st
    print(f"Response time: {response_time}")

    context["response_time"] = response_time
    socketio.emit('response_received')

if __name__ == '__main__':
    socketio.run(app)