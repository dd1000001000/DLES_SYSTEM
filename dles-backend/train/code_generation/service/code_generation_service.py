from enhance.LLM.code_generation_llm import CodeGenerationLLM
from settings.service.llm_config_service import get_llm_config


class CodeGenerationService:
    def __init__(self, username: str):
        self.llm = CodeGenerationLLM(get_llm_config(username))

    def ask(self,user_code:str,user_require:str) -> str:
        return self.llm.ask(user_code,user_require)