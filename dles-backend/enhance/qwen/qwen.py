import copy
import json
from typing import List, Dict

from openai import OpenAI


class Qwen:
    def __init__(self,model_name:str="qwen-plus"):
        self.model_name = model_name
        self.api_key = "sk-af004499793b414b850149e572e056ad"
        self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        self.client = OpenAI(api_key=self.api_key,base_url=self.base_url)

    def ask_one(self, prompt: str, user_input: str, output_json=True):
        try:
            message = [
                {'role': 'system', 'content': prompt},
                {'role': 'user', 'content': user_input}]

            create_params = {
                'model': self.model_name,
                'messages': message
            }
            if output_json:
                create_params['response_format'] = {"type": "json_object"}

            completion = self.client.chat.completions.create(**create_params)

            result = json.loads(completion.model_dump_json())
            assistant_output = result["choices"][0]["message"]["content"]
            message.append({'role': 'assistant', 'content': assistant_output})
            return assistant_output, message, result
        except Exception as e:
            raise e

    def long_chat(self,chat_history:List[Dict],user_input,output_json=True):
        try:
            history = copy.deepcopy(chat_history)
            history.append({'role': 'user', 'content': user_input})
            history = [{'role':h['role'],'content':str(h['content'])} for h in history]
            create_params = {
                'model': self.model_name,
                'messages': history
            }
            if output_json:
                create_params['response_format'] = {"type": "json_object"}
            completion = self.client.chat.completions.create(**create_params)
            result = json.loads(completion.model_dump_json())
            assistant_output = result["choices"][0]["message"]["content"]
            history.append({'role': 'assistant', 'content': assistant_output})
            return assistant_output, history, result
        except Exception as e:
            raise e