from qa_over_docs import r_db
from sqlalchemy import Column, Integer, String, ForeignKey

class Question(r_db.Model):
    id = r_db.Column(Integer, primary_key=True)
    question = r_db.Column(String, nullable=False)
    count = r_db.Column(Integer, default=1)

class Answer(r_db.Model):
    id = r_db.Column(Integer, primary_key=True)
    answer = r_db.Column(String, nullable=False)

class Response(r_db.Model):
    id = r_db.Column(Integer, primary_key=True)
    question = r_db.Column(Integer, ForeignKey("question.id"), nullable=False)
    answer = r_db.Column(Integer, ForeignKey("answer.id"), nullable=False)
    likes = r_db.Column(Integer, default=0)
    dislikes = r_db.Column(Integer, default=0)