from flask import render_template, request, redirect, flash
from threading import Thread
from time import time, sleep
from pprint import pprint
import sqlalchemy as sa

from qa_over_docs import app, context, socketio, save_context, r_db
from qa_over_docs import vector_db, relational_db, api, message

RESPONSE_COMMENTS = {
    "new": "This answer is newly generated",
    "similar": "This answer came from a similar question",
    "identical": "This answer came from an identical question"
}


@app.route("/", methods=['GET', 'POST'])
def home():
    save_context()
    if request.method == 'POST':
        context["response_time"] = None
        user_input = request.form['user_input']

        context["chat_items"].append(message.Question(user_input))

        thread = Thread(target=response, args=(user_input,))
        thread.start()

        context["waiting"] = True

    return render_template("index.html", **context, response_comments=RESPONSE_COMMENTS)


def response(user_input: str, force_generate_new: bool = False):
    st = time()
    sleep(0.1)

    answer_message = message.Answer()

    if force_generate_new:
        relevant_qa = {}
    else:
        relevant_qa = vector_db.query_most_relevant_question(user_input)
    # pprint(relevant_qa)

    if "distance" in relevant_qa:
        print("Relevant question distance: " + str(relevant_qa["distance"]))
        distance = relevant_qa["distance"]
        if distance < 0.4:
            with app.app_context():
                question: relational_db.Question
                answer: relational_db.Answer

                question, answer = r_db.session.query(relational_db.Question, relational_db.Answer)\
                    .join(relational_db.Response, relational_db.Response.question == relational_db.Question.id)\
                    .join(relational_db.Answer, relational_db.Response.answer == relational_db.Answer.id)\
                    .filter(relational_db.Question.id == relevant_qa["question_id"])\
                    .first()

                if distance < 0.1:
                    answer_message.comment = "identical"
                    question.count += 1
                    r_db.session.commit()
                else:
                    answer_message.comment = "similar"
                    new_question = relational_db.Question(question=user_input)
                    r_db.session.add(new_question)
                    r_db.session.commit()

                    vector_db.add_question(
                        new_question.id,
                        user_input
                    )
                    
                    new_response = relational_db.Response(
                        question=new_question.id,
                        answer=answer.id
                    )
                    r_db.session.add(new_response)
                    r_db.session.commit()

                answer_message.saved_question = question.question
                answer_message.message = answer.answer
        else:
            force_generate_new = True
    else:
        force_generate_new = True

    if force_generate_new:
        answer_message.comment = "new"
        relevant_docs = vector_db.retrieve_relevant_docs(user_input)
        text_answer = api.retrieve_response(user_input, relevant_docs)

        with app.app_context():
            question = relational_db.Question(question=user_input)
            answer = relational_db.Answer(answer=text_answer)

            r_db.session.add(question)
            r_db.session.add(answer)

            r_db.session.commit()

            vector_db.add_question(
                question.id,
                user_input
            )

            response = relational_db.Response(
                question=question.id,
                answer=answer.id
            )

            r_db.session.add(response)
            r_db.session.commit()

        answer_message.message = text_answer

    context["chat_items"].append(answer_message)

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
    context["chat_items"].append(message.Question(question))

    thread = Thread(target=response, args=(question,True))
    thread.start()

    context["waiting"] = True
    
    return redirect("/")


@app.route("/like_answer/<int:index>")
def like_answer(index: int):
    question = context["chat_items"][index - 1]
    answer = context["chat_items"][index]
    # vector_db.add_question_answer(question.message, answer.message)
    flash("Answer saved as a response", "success")
    return redirect("/")


@app.route("/dislike_answer/<int:index>")
def dislike_answer(index: int):
    answer = context["chat_items"][index] # type: message.Answer
    if answer.saved_question:
        vector_db.remove_answer(answer.saved_question)
        flash("Answer removed from saved responses", "primary")
    return redirect("/")