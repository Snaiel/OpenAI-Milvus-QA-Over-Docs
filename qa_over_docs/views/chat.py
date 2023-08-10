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
        context["waiting"] = True

        thread = Thread(target=response, args=(user_input,))
        thread.start()

    return render_template("index.html", **context, response_comments=RESPONSE_COMMENTS)


def response(user_input: str, force_generate_new: bool = False, previous_response: relational_db.Response  = None):
    time_start = time()

    context["time_intervals"] = {}

    answer_message = message.Answer()

    if force_generate_new:
        relevant_q = {}
    else:
        relevant_q = vector_db.query_most_relevant_question(user_input)

    time_query_relevant_question = time()
    if relevant_q:
        context["time_intervals"]["query for any relevant questions"] = time_query_relevant_question - time_start

    # pprint(relevant_qa)

    if "distance" in relevant_q:
        print("Relevant question distance: " + str(relevant_q["distance"]))
        distance = relevant_q["distance"]
        if distance < 0.4:
            # since there is a question with small distance,
            # retrieve relevant response
            answer_message = retrieve_relevant_response(answer_message, user_input, relevant_q, distance)
        else:
            # no similar questions (distance >= 0.4)
            force_generate_new = True
    else:
        force_generate_new = True

    time_retrieve_relevant_question = time()
    if not force_generate_new:
        context["time_intervals"]["retrieve relevant question"] = time_retrieve_relevant_question - time_query_relevant_question


    if force_generate_new:
        # make a call to the api and generate an answer
        answer_message = generate_answer(answer_message, user_input, previous_response)
        time_generate_answer = time()
        context["time_intervals"]["generate answer"] = time_generate_answer - time_retrieve_relevant_question

            
    context["chat_items"].append(answer_message)
    context["waiting"] = False

    sleep(0.001)
    time_end = time()

    response_time = time_end - time_start
    print(f"Response time: {response_time}")

    context["time_intervals"]["total time"] = response_time
    socketio.emit('response_received')


def retrieve_relevant_response(answer_message: message.Answer, user_input: str, relevant_q: dict, distance: float) -> message.Answer:
    question: relational_db.Question
    answer: relational_db.Answer
    with app.app_context():

        # retrieve previous question and answer from relational database
        relevant_response: relational_db.Response = r_db.session.query(relational_db.Response)\
            .filter(relational_db.Response.question_id == relevant_q["question_id"])\
            .first()
        
        question = relevant_response.question
        answer = relevant_response.answer

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
                question_id=new_question.id,
                answer_id=answer.id
            )
            r_db.session.add(new_response)
            r_db.session.commit()

        # assign the message to be shown in the chat interface
        answer_message.id = answer.id
        answer_message.saved_question = question.question
        answer_message.message = answer.answer
        answer_message.sources = [vector_db.query_source_metadata(response_source.source_id) for response_source in relevant_response.sources]

    return answer_message


def generate_answer(answer_message: message.Answer, user_input: str, previous_response: relational_db.Response) -> message.Answer:
    answer_message.comment = "new"

    relevant_docs = vector_db.retrieve_relevant_docs(user_input)
    response = api.retrieve_response(user_input, relevant_docs)

    answer_message.message = response["answer"]

    sources_metadata = []
    for source_id in response["relevant_source_ids"]:
        sources_metadata.append(vector_db.query_source_metadata(source_id))
    answer_message.sources = sources_metadata

    with app.app_context():
        if previous_response:
            # retrieve previous question
            question = r_db.session.query(relational_db.Question)\
                .join(relational_db.Response, relational_db.Response.question_id == relational_db.Question.id)\
                .filter(relational_db.Question.id == previous_response.question_id)\
                .first()
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
        answer = relational_db.Answer(answer=answer_message.message)
        r_db.session.add(answer)

        r_db.session.commit()            

        # add response to relational database
        new_response = relational_db.Response(
            question_id=question.id,
            answer_id=answer.id
        )

        r_db.session.add(new_response)
        r_db.session.commit()

        answer_message.id = answer.id

        # link sources to sources in relational database
        for source_id in response["relevant_source_ids"]:
            response_source = relational_db.ResponseSource(
                response_id=new_response.id,
                source_id=source_id
            )
            r_db.session.add(response_source)
        r_db.session.commit()

    return answer_message


@app.route("/generate_new_answer/<int:index>")
def generate_new_answer(index: int):
    question: message.Question = context["chat_items"][index - 1]
    answer: message.Answer = context["chat_items"][index]

    context["response_time"] = None
    context["chat_items"].append(question)

    r_response: relational_db.Response = r_db.session.query(relational_db.Response)\
        .filter(relational_db.Response.question_id == question.id)\
        .filter(relational_db.Response.answer_id == answer.id)\
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
            .filter_by(answer_id=answer.id)
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
            .filter_by(answer_id=answer.id)
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

        answer = relational_db.Answer(answer_id=answer_message.message)
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
            question_id=question.id,
            answer_id=answer.id
        )
        r_db.session.add(response)
        r_db.session.commit()

        flash("Successfully created new response that maps answer to given question", "success")

    return redirect("/")