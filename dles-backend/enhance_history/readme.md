这个文件夹存储用户的所有用例，只是一个存储文件夹

用户的一个用例里面应该有以下几个文件：
- table.csv：原始表格的 csv 文件
- pure_embedding.npy：直接由 jina_embedding 处理得到的原始 embedding 文件
- processed_embedding.npy：由 transformer 模型处理后的列相关的 embedding 文件
- dialogue.json：当前用例的对话 json 文件