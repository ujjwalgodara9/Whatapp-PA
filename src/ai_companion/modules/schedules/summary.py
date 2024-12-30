class ConversationSummary:
    def __init__(self):
        self.summary = ""

    def update(self, message: str):
        self.summary += message
