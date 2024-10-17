import agent_catalog
import controlflow
import controlflow.tasks.task
import typing


class Task(controlflow.Task):
    _accept_status: typing.Callable = None

    def __init__(self, node_name: str, auditor: agent_catalog.Auditor, session: str, **kwargs):
        super(Task, self).__init__(**kwargs)
        self._accept_status = lambda status, direction: auditor.move(
            node_name=node_name, direction=direction, session=session, content={"status": status.value}
        )

    def set_status(self, status: controlflow.tasks.task.TaskStatus):
        if status in controlflow.tasks.task.INCOMPLETE_STATUSES:
            direction = "enter"
        elif status in controlflow.tasks.task.COMPLETE_STATUSES:
            direction = "exit"
        else:
            raise ValueError(f"Invalid status encountered: {status}")
        super(Task, self).set_status(status)
        self._accept_status(status, direction)


class TaskFactory:
    def __init__(
        self,
        provider: agent_catalog.Provider,
        auditor: agent_catalog.Auditor,
        session: str,
        tools: list[typing.Any] = None,
        agent: controlflow.Agent = None,
    ):
        self.provider: agent_catalog.Provider = provider
        self.auditor: agent_catalog.Auditor = auditor
        self.session: str = session
        self.tools: list[typing.Any] = tools if tools is not None else list()
        self.agent: controlflow.Agent = agent

    def build(self, prompt_name: str, **kwargs) -> controlflow.Task:
        # Rosetta manages prompts and the tools assigned to these prompts.
        prompt: agent_catalog.provider.Prompt = self.provider.get_prompt_for(name=prompt_name)
        if prompt is None:
            raise RuntimeError(f"Prompt not found with the name {prompt_name}!")
        tools = prompt.tools + self.tools if prompt.tools is not None else self.tools

        # The remainder of this function is dependent on ControlFlow (the agent framework).
        kwargs_copy = kwargs.copy()
        if "tools" in kwargs_copy:
            del kwargs_copy["tools"]
        if "objective" in kwargs_copy:
            del kwargs_copy["objective"]
        if "agents" not in kwargs_copy and self.agent is not None:
            kwargs_copy["agents"] = [self.agent]
        return Task(
            node_name=prompt_name,
            auditor=self.auditor,
            session=self.session,
            objective=prompt.prompt,
            tools=tools,
            **kwargs_copy,
        )

    def run(self, prompt_name: str, **kwargs):
        return self.build(prompt_name=prompt_name, **kwargs).run()
