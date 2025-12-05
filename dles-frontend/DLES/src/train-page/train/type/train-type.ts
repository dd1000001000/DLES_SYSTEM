export interface DeleteForm {
  folderName: string;
  fileName: string;
}

export interface EvaluateParas {
  training_set_percentage: number;
  text_features_max: number;
  target_text_keywords: number;
  predict_column: string;
}
