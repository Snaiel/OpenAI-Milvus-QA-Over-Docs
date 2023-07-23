class Message():
    def __init__(self, message: str = "") -> None:
        self.message = message # the user's question or the answer

    def __str__(self) -> str:
        return self.message

class Question(Message):
    def __init__(self, message: str = "") -> None:
        super().__init__(message)

class Answer(Message):
    def __init__(self,message: str = "", id: int = None,  saved_question: str = None, comment: str = None) -> None:
        super().__init__(message)
        self.id = id # the id of the answer in the relational database
        self.saved_question = saved_question # the primary key of the previous question
        self.comment = comment # whether the answer is from a `new`, `similar`, or `identical` question

    def lines(self) -> list[str]:
        return self.message.splitlines()