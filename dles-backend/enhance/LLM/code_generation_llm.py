# -*- coding: utf-8 -*-
from enhance.qwen.qwen import Qwen


class CodeGenerationLLM:
    def __init__(self,model_name:str="qwen-coder-plus"):
        self.qwen = Qwen(model_name)
        self.prompt = self.get_prompt()

    def get_prompt(self):
        prompt = """你是一个代码编写专家，请根据用户的代码和要求给出正确的代码，除了代码之外，不要给出任何其它内容以及包含解释性文本。"""
        return prompt

    def ask(self,user_code:str,user_require:str):
        user_input = user_require
        if user_code.strip() != "":
            user_input += f"这是我的代码：\n{user_code}"
        result = self.qwen.ask_one(self.prompt,user_input,False)[0]
        result_list = result.split("\n")
        result_list = [line for line in result_list if '```' not in line]
        result = '\n'.join(result_list)
        return result