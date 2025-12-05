from pydantic import BaseModel


class GeneCode(BaseModel):
    userCode: str
    userInput: str