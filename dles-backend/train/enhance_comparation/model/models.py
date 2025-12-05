from pydantic import BaseModel


class DeleteForm(BaseModel):
    folderName: str
    fileName: str

class EvaluateParas(BaseModel):
    training_set_percentage: float
    text_features_max: int
    target_text_keywords: int
    predict_column: str