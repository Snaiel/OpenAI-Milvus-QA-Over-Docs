from flask import Flask, render_template, request, redirect, flash, url_for
from flask_socketio import SocketIO
from threading import Thread
from time import time, sleep
from werkzeug.utils import secure_filename
from pprint import pprint
import os, json, shutil, validators

from api import retrieve_response
import db


UPLOAD_FOLDER = 'uploads/'
ALLOWED_EXTENSIONS = {'pdf', 'csv'}
CONTEXT_FILE = "context.json"
SOURCES_FILE = "sources.txt"


class Message():
    def __init__(self, message: str, type: str, saved_question: int = None) -> None:
        self.message = message
        self.type = type
        self.saved_question = saved_question

    def __str__(self) -> str:
        return self.message
    
    def lines(self) -> list[str]:
        return self.message.splitlines()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = 'a super secret key'
app.debug = True
socketio = SocketIO(app)


if not os.path.exists(UPLOAD_FOLDER):
    os.mkdir(UPLOAD_FOLDER)

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


def response(user_input: str, force_generate_new: bool = False):
    st = time()
    sleep(0.1)

    if force_generate_new:
        relevant_qa = {}
    else:
        relevant_qa = db.query_most_relevant_question(user_input)
    # pprint(relevant_qa)

    if "distance" in relevant_qa and relevant_qa["distance"] < 0.4:
        print("Relevant question distance: " + str(relevant_qa["distance"]))
        context["chat_items"].append(Message(relevant_qa["answer"], "response", relevant_qa["pk"]))
    else:
        relevant_docs = db.retrieve_relevant_docs(user_input)
        pprint(relevant_docs)
        response = retrieve_response(user_input, relevant_docs)
        context["chat_items"].append(Message(response, "response"))

    context["waiting"] = False

    sleep(0.2)
    et = time()

    response_time = et - st
    print(f"Response time: {response_time}")

    context["response_time"] = response_time
    socketio.emit('response_received')


@app.route("/generate_new_answer/<int:index>")
def generate_new_answer(index: int):
    question = context["chat_items"][index - 1].message

    context["response_time"] = None
    context["chat_items"].append(Message(question, "user"))

    thread = Thread(target=response, args=(question,True))
    thread.start()

    context["waiting"] = True
    
    return redirect("/")


@app.route('/create_collection')
def create_collection():
    if not db.collection_exists():
        db.create_collections()
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
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(path)

            context["sources_to_add"].append(filename)

    return redirect("/")


@app.route("/clear_sources_to_add")
def clear_sources_to_add():
    context["sources_to_add"] = []
    shutil.rmtree(UPLOAD_FOLDER)
    os.mkdir(UPLOAD_FOLDER)
    return redirect("/")


@app.route("/add_sources", methods=['GET', 'POST'])
def add_sources():
    if request.method == 'POST':
        if context["sources_to_add"]:
            valid_sources = []
            
            for source in context["sources_to_add"]:
                if validators.url(source) or os.path.exists(os.path.join(UPLOAD_FOLDER, source)):
                    valid_sources.append(source)
            if valid_sources:
                db.add_sources(valid_sources)
                context["sources"].extend(valid_sources)
                clear_sources_to_add()
                flash("Successfully added sources", "success")
            else:
                flash("No valid sources provided", "warning")
        else:
            flash("No sources to add", "warning")
    return redirect("/")


@app.route("/remove_source/<int:index>")
def remove_source(index: int):
    source = context["sources"][index]
    db.remove_source(source)
    flash(f"Successfully removed {source}", "primary")
    context["sources"].pop(index)
    return redirect("/")


@app.route("/like_answer/<int:index>")
def like_answer(index: int):
    question = context["chat_items"][index - 1]
    answer = context["chat_items"][index]
    db.add_question_answer(question.message, answer.message)
    flash("Answer saved as a response", "success")
    return redirect("/")


@app.route("/dislike_answer/<int:index>")
def dislike_answer(index: int):
    answer = context["chat_items"][index] # type: Message
    if answer.saved_question:
        db.remove_answer(answer.saved_question)
        flash("Answer removed from saved responses", "primary")
    return redirect("/")


@app.route("/delete_collection")
def delete_collection():
    db.delete_collection()

    if os.path.exists(CONTEXT_FILE):
        os.remove(CONTEXT_FILE)
    if os.path.exists(SOURCES_FILE):
        os.remove(SOURCES_FILE)

    context["collection_exists"] = False
    context["sources"] = []
    context["response_time"] = None
    context["chat_items"] = []

    flash("Collection successfully deleted", "primary")
    return redirect("/")


if __name__ == '__main__':
    socketio.run(app)