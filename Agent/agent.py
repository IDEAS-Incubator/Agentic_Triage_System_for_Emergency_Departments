import json
import copy
import inspect

from pydantic import BaseModel
from typing_extensions import Literal
from typing import Union, Callable, List, Optional
from langchain_ollama import OllamaLLM


def pretty_print_messages(messages) -> None:
    for message in messages:
        if message["role"] != "assistant":
            continue

        # print agent name in blue
        sender = message.get("sender", "Assistant")  # Default to "Assistant" if sender not found
        print(f"\033[94m{sender}\033[0m:", end=" ")

        # print response, if any
        if message["content"]:
            print(message["content"])

        # print tool calls in purple, if any
        tool_calls = message.get("tool_calls") or []
        if len(tool_calls) > 1:
            print()
        for tool_call in tool_calls:
            f = tool_call["function"]
            name, args = f["name"], f["arguments"]
            arg_str = json.dumps(json.loads(args)).replace(":", "=")
            print(f"\033[95m{name}\033[0m({arg_str[1:-1]})")

def function_to_json(func) -> dict:
    """
    Sample Input:
    def add_two_numbers(a: int, b: int) -> int:
        # Adds two numbers together
        return a + b
    
    Sample Output:
    {
        'type': 'function',
        'function': {
            'name': 'add_two_numbers',
            'description': 'Adds two numbers together',
            'parameters': {
                'type': 'object',
                'properties': {
                    'a': {'type': 'integer'},
                    'b': {'type': 'integer'}
                },
                'required': ['a', 'b']
            }
        }
    }
    """
    type_map = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
        type(None): "null",
    }

    try:
        signature = inspect.signature(func)
    except ValueError as e:
        raise ValueError(
            f"Failed to get signature for function {func.__name__}: {str(e)}"
        )

    parameters = {}
    for param in signature.parameters.values():
        try:
            param_type = type_map.get(param.annotation, "string")
        except KeyError as e:
            raise KeyError(
                f"Unknown type annotation {param.annotation} for parameter {param.name}: {str(e)}"
            )
        parameters[param.name] = {"type": param_type}

    required = [
        param.name
        for param in signature.parameters.values()
        if param.default == inspect._empty
    ]

    return {
        "type": "function",
        "function": {
            "name": func.__name__,
            "description": func.__doc__ or "",
            "parameters": {
                "type": "object",
                "properties": parameters,
                "required": required,
            },
        },
    }

AgentFunction = Callable[[], Union[str, "Agent", dict]]

class Agent(BaseModel):
    # Just a simple class. Doesn't contain any methods out of the box
    name: str = "Agent"
    model: str = "llama3.2"
    instructions: Union[str, Callable[[], str]] = "You are a helpful agent."
    functions: List[AgentFunction] = []
    tool_choice: str = None
    parallel_tool_calls: bool = True

class Response(BaseModel):
    # Response is used to encapsulate the entire conversation output
    messages: List = []
    agent: Optional[Agent] = None
    
class Function(BaseModel):
    arguments: str
    name: str

class ChatCompletionMessageToolCall(BaseModel):
    id: str # The ID of the tool call
    function: Function # The function that the model called
    type: Literal["function"] # The type of the tool. Currently, only `function` is supported

class Result(BaseModel):
    # Result is used to encapsulate the return value of a single function/tool call
    value: str = "" # The result value as a string.
    agent: Optional[Agent] = None # The agent instance, if applicable.

class Swarm:
    # Implements the core logic of orchestrating a single/multi-agent system
    def __init__(
        self,
        model: str = "llama3.2",
        base_url: str = "http://localhost:11434"
    ):
        self.client = OllamaLLM(
            model=model,
            base_url=base_url
        )
        
    def get_chat_completion(
        self,
        agent: Agent,
        history: List,
        model_override: str
    ):
        messages = [{"role": "system", "content": agent.instructions}] + history
        
        # Convert messages to prompt format
        prompt = ""
        for msg in messages:
            if msg["role"] == "system":
                prompt += f"System: {msg['content']}\n"
            elif msg["role"] == "user":
                prompt += f"Human: {msg['content']}\n"
            elif msg["role"] == "assistant":
                prompt += f"Assistant: {msg['content']}\n"
            elif msg["role"] == "tool":
                prompt += f"Tool response: {msg['content']}\n"
        
        # Get response from Ollama
        response = self.client.invoke(prompt)
        
        # Convert response to OpenAI-like format
        class MockMessage:
            def __init__(self, content):
                self.content = content
                self.tool_calls = None
                self.model_dump_json = lambda: json.dumps({
                    "role": "assistant",
                    "content": content,
                    "sender": agent.name  # Add sender field
                })
        
        return type('obj', (object,), {
            'choices': [type('obj', (object,), {'message': MockMessage(response)})]
        })

    def handle_function_result(self, result) -> Result:
        if isinstance(result, Result):
            return result
        if isinstance(result, Agent):
            return Result(
                value=json.dumps({"assistant": result.name}),
                agent=result
            )
        try:
            return Result(value=str(result))
        except Exception as e:
            raise TypeError(e)

    def handle_tool_calls(
        self,
        tool_calls: List[ChatCompletionMessageToolCall],
        functions: List[AgentFunction]
    ) -> Response:
        function_map = {f.__name__: f for f in functions}
        partial_response = Response(messages=[], agent=None)
        for tool_call in tool_calls:
            name = tool_call.function.name
            # handle missing tool case, skip to next tool
            if name not in function_map:
                partial_response.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "tool_name": name,
                        "content": f"Error: Tool {name} not found.",
                    }
                )
                continue
            args = json.loads(tool_call.function.arguments)
            raw_result = function_map[name](**args)
            print(f'Called function {name} with args: {args} and obtained result: {raw_result}')
            print('#############################################')
            result: Result = self.handle_function_result(raw_result)
            partial_response.messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "tool_name": name,
                    "content": result.value,
                }
            )
            if result.agent:
                partial_response.agent = result.agent

        return partial_response
    
    def run(
        self,
        agent: Agent,
        messages: List,
        model_override: str = None,
        max_turns: int = float("inf"),
        execute_tools: bool = True,
    ) -> Response:
        active_agent = agent
        history = copy.deepcopy(messages)
        init_len = len(messages)

        print('#############################################')
        print(f'history: {history}')
        print('#############################################')
        while len(history) - init_len < max_turns and active_agent:
            completion = self.get_chat_completion(
                agent=active_agent,
                history=history,
                model_override=model_override
            )
            message = completion.choices[0].message
            message.sender = active_agent.name
            print(f'Active agent: {active_agent.name}')
            print(f"message: {message}")
            print('#############################################')
            
            
            history.append(json.loads(message.model_dump_json()))

            if not message.tool_calls or not execute_tools:
                print('No tool calls hence breaking')
                print('#############################################')
                break
            
            partial_response = self.handle_tool_calls(message.tool_calls, active_agent.functions)
            history.extend(partial_response.messages)
            
            if partial_response.agent:
                active_agent = partial_response.agent
                message.sender = active_agent.name
        return Response(
            messages=history[init_len:],
            agent=active_agent,
        )
