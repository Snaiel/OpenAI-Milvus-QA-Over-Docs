import validators

class Message():
    def __init__(self, message: str = "", id: int = None) -> None:
        self.id = id # the id in the relational database
        self.message = message # the user's question or the answer

    def __str__(self) -> str:
        return self.message

class Question(Message):
    def __init__(self, message: str = "", id: int = None) -> None:
        super().__init__(message, id)

class Answer(Message):
    def __init__(
            self,
            message: str = "",
            sources: list[dict] = [],
            id: int = None,
            saved_question: str = None,
            comment: str = None
        ) -> None:
        super().__init__(message, id)
        self.sources: list[dict] = sources # the metadata of sources used to answer the question
        self.saved_question: str = saved_question # the primary key of the previous question
        self.comment: str = comment # whether the answer is from a `new`, `similar`, or `identical` question

    def lines(self) -> list[str]:
        return self.message.splitlines()
    
    def get_sources(self) -> dict[str, dict]:
        output = {}

        # the value of the source key is "uploads/file.csv"
        # this just removes "uploads/"
        for source in self.sources:
            source["source"] = source["source"].replace("uploads/", "")

        # sort the list based on the 'source' value
        sources: list[dict] = sorted(self.sources, key=lambda x: x["source"])

        # group duplicate sources together
        for source_metadata in sources:
            source = source_metadata["source"].replace("uploads/", "")

            if validators.url(source)and source not in output:
                output[source] = {"title": source_metadata["title"]}
            else:
                filetype = source_metadata["source"].split(".")[-1].lower().strip()
                if filetype == "csv":
                    row_num = source_metadata["row"] + 2
                    if source not in output:
                        output[source] = {"rows_list": [row_num]}
                    else:
                        output[source]["rows_list"].append(row_num)
                if filetype == "pdf":
                    page = source_metadata["page"]
                    if source not in output:
                        output[source] = {"pages_list": [page], "title": source_metadata["Title"], "author": source_metadata["Author"]}
                    else:
                        output[source]["pages_list"].append(page)

        # represent the list of rows/pages as a string
        for source, metadata in output.items():
            for key in metadata.keys():
                if '_list' in key:
                    num_list = [str(num) for num in output[source][key]]
                    output[source][key.replace("_list", "")] = ", ".join(num_list)
                    output[source].pop(key)
                    break

        return output