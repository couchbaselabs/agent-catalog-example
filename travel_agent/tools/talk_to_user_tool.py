import rosetta


@rosetta.tool
def talk_to_user(message: str, to_user_queue, from_user_queue, get_response: bool = True) -> str:
    """
    Send a message to the human user and optionally wait for a response. If `get_response` is True, the function
    will return the user's response, otherwise it will return a simple confirmation. Do not send the user
    concurrent messages that require responses, as this will cause confusion.

    You may need to ask the human about multiple tasks at once. Consolidate your questions into a single message.
    For example, if Task 1 requires information X and Task 2 needs information Y, send a single message that
    naturally asks for both X and Y.
    """
    to_user_queue.join()
    to_user_queue.put(message)
    if get_response:
        response = from_user_queue.get()
        from_user_queue.task_done()
        return response
    return "Message sent to user."
