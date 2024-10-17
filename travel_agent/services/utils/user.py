import agent_catalog.auditor
import queue


# Below, we have a function that will use the `to_user_queue` and `from_user_queue` to communicate with the user.
def build_interaction_tool(
    to_user_queue: queue.Queue, from_user_queue: queue.Queue, auditor: agent_catalog.Auditor, thread_id: str
):
    def talk_to_user(message: str, get_response: bool = True) -> str:
        """
        Send a message to the human user and optionally wait for a response. If `get_response` is True, the function
        will return the user's response, otherwise it will return a simple confirmation. Do not send the user
        concurrent messages that require responses, as this will cause confusion.

        You may need to ask the human about multiple tasks at once. Consolidate your questions into a single message.
        For example, if Task 1 requires information X and Task 2 needs information Y, send a single message that
        naturally asks for both X and Y.
        """
        to_user_queue.join()
        auditor.accept(kind=agent_catalog.auditor.Kind.Assistant, content=message, session=thread_id)
        to_user_queue.put(message)
        if get_response:
            response = from_user_queue.get()
            auditor.accept(kind=agent_catalog.auditor.Kind.Human, content=response, session=thread_id)
            from_user_queue.task_done()
            return response
        return "Message sent to user."

    return talk_to_user
