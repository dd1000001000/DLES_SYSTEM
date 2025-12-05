from enhance.LLM.code_generation_llm import CodeGenerationLLM


class CodeGenerationService:
    def __init__(self, model:str = "qwen-coder-plus"):
        self.llm = CodeGenerationLLM(model)

    def ask(self,user_code:str,user_require:str) -> str:
        return self.llm.ask(user_code,user_require)