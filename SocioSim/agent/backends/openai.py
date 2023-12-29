from typing import List
import os
import re
import time
import logging
from tenacity import retry, stop_after_attempt, wait_random_exponential

from .base import IntelligenceBackend
from ...message import Message, SYSTEM_NAME, MODERATOR_NAME
from ...image import Image

try:
    from openai import OpenAI
except ImportError:
    is_openai_available = False
    # logging.warning("openai package is not installed")
else:
    openai_api_key = os.environ.get("OPENAI_KEY")

    if openai_api_key is None:
        # logging.warning("OpenAI API key is not set. Please set the environment variable OPENAI_API_KEY")
        is_openai_available = False
    else:
        is_openai_available = True

# Default config follows the OpenAI playground
DEFAULT_TEMPERATURE = 0.9
DEFAULT_MAX_TOKENS = 1024
# DEFAULT_MODEL = "gpt-3.5-turbo"
DEFAULT_MODEL = "gpt-4-turbo"

END_OF_MESSAGE = "<EOS>"  # End of message token specified by us not OpenAI
STOP = ("<|endoftext|>", END_OF_MESSAGE)  # End of sentence token
BASE_PROMPT = f"The messages always end with the token {END_OF_MESSAGE}."


class OpenAIChat(IntelligenceBackend):
    """
    Interface to the ChatGPT style model with system, user, assistant roles separation
    """
    stateful = False
    type_name = "openai-chat"

    def __init__(self, temperature: float = DEFAULT_TEMPERATURE, max_tokens: int = DEFAULT_MAX_TOKENS,
                 model: str = DEFAULT_MODEL, merge_other_agents_as_one_user: bool = False, **kwargs):
        """
        instantiate the OpenAIChat backend
        args:
            temperature: the temperature of the sampling
            max_tokens: the maximum number of tokens to sample
            model: the model to use
            merge_other_agents_as_one_user: whether to merge messages from other agents as one user message
        """
        assert is_openai_available, "openai package is not installed or the API key is not set"
        super().__init__(temperature=temperature, max_tokens=max_tokens, model=model,
                         merge_other_agents_as_one_user=merge_other_agents_as_one_user, **kwargs)

        self.temperature = temperature
        self.max_tokens = max_tokens
        self.model = model
        self.merge_other_agent_as_user = merge_other_agents_as_one_user

    @retry(stop=stop_after_attempt(6), wait=wait_random_exponential(min=1, max=60))
    def _get_response(self, messages):
        client = OpenAI(api_key=openai_api_key)
        completion = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stop=STOP
        )

        response = completion.choices[0].message.content
        response = response.strip()
        return response

    def query(self, agent_name: str, role_desc: str, history_messages: List[Message], global_prompt: str = None,
              images: List[Image] = [], request_msg: Message = None, *args, **kwargs) -> str:
        """
        format the input and call the ChatGPT/GPT-4 API
        args:
            agent_name: the name of the agent
            role_desc: the description of the role of the agent
            env_desc: the description of the environment
            history_messages: the history of the conversation, or the observation for the agent
            request_msg: the request from the system to guide the agent's next response
        """
        messages = []
        
        # System env
        # Merge the role description and the global prompt as the system prompt for the agent
        if global_prompt:  # Prepend the global prompt if it exists
            system_prompt = f"{global_prompt.strip()}\n{BASE_PROMPT}\n\nYour name is {agent_name}.\n\nYour role:{role_desc}"
        else:
            system_prompt = f" Your name is {agent_name}.\n\nYour role:{role_desc}\n\n{BASE_PROMPT}"
        
        system_message = {"role": "system", "content": system_prompt}
        messages.append(system_message)
        
        # Text
        if len(history_messages) > 0:
            user_messages = []
            if len(history_messages) > 8:  # context limit
                history_messages = history_messages[-8:]
            for msg in history_messages:
                user_messages.append((msg.agent_name, f"{msg.content}{END_OF_MESSAGE}"))

            user_prompt = ""
            for _, msg in enumerate(user_messages):
                user_prompt += f"[{msg[0]}]: {msg[1]}\n"
            
            user_message = {"role": "user", "content": user_prompt}
            messages.append(user_message)
        
        # Image
        for image in images:
            image_prompt = [{"type": "text", "text": image.description}]
            image_content = f"data:image/jpeg;base64,{image.content}"
            image_content = {"type": "image_url", "image_url": {"url": image_content}}
            image_prompt.append(image_content)
            image_message = {"role": "user", "content": image_prompt}
            messages.append(image_message)
        
        response = self._get_response(messages, *args, **kwargs)
        # Remove the agent name if the response starts with it
        response = re.sub(rf"^\s*\[.*]:", "", response).strip()
        response = re.sub(rf"^\s*{re.escape(agent_name)}\s*:", "", response).strip()

        # Remove the tailing end of message token
        response = re.sub(rf"{END_OF_MESSAGE}$", "", response).strip()
        
        # time.sleep(10)
        return response
