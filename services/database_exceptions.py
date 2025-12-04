class AlreadyExistsError(Exception):
    def __init__(self, message, item_id=None):
        super().__init__(message)
        self.item_id = item_id

class ItemNotExistsError(KeyError):
    ...

class UnexpectedBehavior(Exception):
    ...