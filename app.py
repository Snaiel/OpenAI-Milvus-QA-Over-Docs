from flask import Flask, render_template, request, redirect, flash
from time import sleep
from flask_socketio import SocketIO
from threading import Thread
from time import time
import os

from api import retrieve_response
import db

CURRENT_SOURCES_FILE = "data/current_sources.json"

class Message():
    def __init__(self, message: str, type: str) -> None:
        self.message = message
        self.type = type

    def __str__(self) -> str:
        return self.message

app = Flask(__name__)
app.config['SECRET_KEY'] = 'a super secret key'
app.debug = True
socketio = SocketIO(app)

context = {
    "chat_items": [],
    "waiting": False,
    "response_time": None,
    "collection_exists": False
}

@app.route("/", methods=['GET', 'POST'])
def home():
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

@app.route("/delete_collection")
def delete_collection():
    db.delete_collection()
    if os.path.exists(CURRENT_SOURCES_FILE):
        os.remove(CURRENT_SOURCES_FILE)
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