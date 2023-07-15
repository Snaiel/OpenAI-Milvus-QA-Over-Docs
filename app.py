from flask import Flask, render_template, request
from time import sleep
from flask_socketio import SocketIO
from threading import Thread
from api import retrieve_response
from time import time

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

chat_items = [

]

waiting = False
response_time = None

def response(user_input: str):
    global waiting, response_time
    st = time()
    sleep(0.1)
    chat_items.append(Message(retrieve_response(user_input), "response"))
    waiting = False
    sleep(0.2)
    socketio.emit('response_received')
    et = time()
    response_time = et - st
    print(f"Response time: {response_time}")

@app.route("/", methods=['GET', 'POST'])
def interface():
    global waiting, response_time
    if request.method == 'POST':
        response_time = None
        user_input = request.form['user_input']
        chat_items.append(Message(user_input, "user"))
        thread = Thread(target=response, args=(user_input,))
        thread.start()
        waiting = True
    return render_template("index.html", chat_items=chat_items, waiting=waiting, response_time=response_time)

if __name__ == '__main__':
    socketio.run(app)