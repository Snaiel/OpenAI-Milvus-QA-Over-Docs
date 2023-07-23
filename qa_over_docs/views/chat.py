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


def response(user_input: str, force_generate_new: bool = False, previous_response: relational_db.Response  = None):
    st = time()
    sleep(0.1)

    answer_message = message.Answer()

    if force_generate_new:
        relevant_q = {}
    else:
        relevant_q = vector_db.query_most_relevant_question(user_input)
    # pprint(relevant_qa)

    question: relational_db.Question
    answer: relational_db.Answer

    if "distance" in relevant_q:
        print("Relevant question distance: " + str(relevant_q["distance"]))
        distance = relevant_q["distance"]
        if distance < 0.4:
            with app.app_context():

                # retrieve previous question and answer from relational database
                question, answer = r_db.session.query(relational_db.Question, relational_db.Answer)\
                    .join(relational_db.Response, relational_db.Response.question == relational_db.Question.id)\
                    .join(relational_db.Answer, relational_db.Response.answer == relational_db.Answer.id)\
                    .filter(relational_db.Question.id == relevant_q["question_id"])\
                    .order_by(relational_db.Response.timestamp.desc())\
                    .first()

                context["chat_items"][-1].id = question.id

                if distance < 0.1:
                    # treat the user's input and the retrieved question as the same
                    answer_message.comment = "identical"
                    question.count += 1
                    r_db.session.commit()
                else:
                    # create a new question from the user's input but
                    # assign the response to the question to be the
                    # similar question's answer
                    answer_message.comment = "similar"

                    # add the new question to the relational database
                    new_question = relational_db.Question(question=user_input)
                    r_db.session.add(new_question)
                    r_db.session.commit()

                    # add the new question to vector collection
                    vector_db.add_question(
                        new_question.id,
                        user_input
                    )
                    
                    # add the new response to the relational database
                    new_response = relational_db.Response(
                        question=new_question.id,
                        answer=answer.id
                    )
                    r_db.session.add(new_response)
                    r_db.session.commit()

                # assign the message to be shown in the chat interface
                answer_message.id = answer.id
                answer_message.saved_question = question.question
                answer_message.message = answer.answer
        else:
            # no similar questions (distance >= 0.4)
            force_generate_new = True
    else:
        force_generate_new = True

    if force_generate_new:
        answer_message.comment = "new"
        relevant_docs = vector_db.retrieve_relevant_docs(user_input)
        text_answer = api.retrieve_response(user_input, relevant_docs)

        answer_message.message = text_answer

        with app.app_context():
            if previous_response:
                # retrieve previous question
                question = r_db.session.query(relational_db.Question)\
                    .join(relational_db.Response, relational_db.Response.question == relational_db.Question.id)\
                    .filter(relational_db.Question.id == previous_response.question)\
                    .first()
                pass
            else:
                # create new question
                question = relational_db.Question(question=user_input)
                r_db.session.add(question)

                r_db.session.commit()            

                # add question to vector collection
                vector_db.add_question(
                    question.id,
                    user_input
                )

            context["chat_items"][-1].id = question.id

            # create new answer
            answer = relational_db.Answer(answer=text_answer)
            r_db.session.add(answer)

            r_db.session.commit()            

            # add response to relational database
            response = relational_db.Response(
                question=question.id,
                answer=answer.id
            )

            r_db.session.add(response)
            r_db.session.commit()

            answer_message.id = answer.id

            
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
    question: message.Question = context["chat_items"][index - 1]
    answer: message.Answer = context["chat_items"][index]

    context["response_time"] = None
    context["chat_items"].append(question)

    print(question.id, answer.id)

    r_response: relational_db.Response = r_db.session.query(relational_db.Response)\
        .filter(relational_db.Response.question == question.id)\
        .filter(relational_db.Response.answer == answer.id)\
        .first()

    thread = Thread(target=response, args=(question.message,True,r_response))
    thread.start()

    context["waiting"] = True
    
    return redirect("/")


@app.route("/like_answer/<int:index>")
def like_answer(index: int):
    answer: message.Answer = context["chat_items"][index]
    response: relational_db.Response = r_db.session.execute(
        sa.select(relational_db.Response)
            .filter_by(answer=answer.id)
    ).first()[0]
    response.likes += 1
    r_db.session.commit()
    flash("Answer liked", "success")
    return redirect("/")


@app.route("/dislike_answer/<int:index>")
def dislike_answer(index: int):
    answer: message.Answer = context["chat_items"][index]
    response: relational_db.Response = r_db.session.execute(
        sa.select(relational_db.Response)
            .filter_by(answer=answer.id)
    ).first()[0]
    response.dislikes += 1
    r_db.session.commit()
    flash("Answer disliked", "primary")
    return redirect("/")


@app.route("/suggest_question/", methods=['GET', 'POST'])
def suggest_question():
    if request.method == 'POST':
        context["response_time"] = None
        suggested_question: str = request.form['suggested-question']
        answer_message: message.Answer = context["chat_items"][int(request.form['answer-index'])]

        answer = relational_db.Answer(answer=answer_message.message)
        r_db.session.add(answer)
        r_db.session.commit()

        relevant_q = vector_db.query_most_relevant_question(suggested_question)

        question: relational_db.Question
        if "distance" in relevant_q and relevant_q["distance"] < 0.1:
            question = r_db.session.query(relational_db.Question)\
                    .filter(relational_db.Question.id == relevant_q["question_id"])\
                    .first()
        else:
            question = relational_db.Question(question=suggested_question)
            r_db.session.add(question)
            r_db.session.commit()

            vector_db.add_question(question.id, suggested_question)

        response = relational_db.Response(
            question=question.id,
            answer=answer.id
        )
        r_db.session.add(response)
        r_db.session.commit()

        flash("Successfully created new response that maps answer to given question", "success")

    return redirect("/")