# -*- coding: utf-8 -*-
import copy
import csv
import json
from typing import List, Dict

from enhance.enhance_history_tree.model.models import Dialogue
from enhance.enhance_main.model.models import EnhanceParas
from enhance.qwen.qwen import Qwen



class KeyWordExtraction:
    def __init__(self,model_name:str="qwen-plus"):
        self.prompt = self.get_prompt()
        self.qwen = Qwen(model_name)

    def get_prompt(self):
        Q1 = "请你帮我进行表格的增强操作，增强时采取连接的增强方式。我希望表格增强后大约有8列左右，对于缺失值，使用平均值填充。这是我的表格列的名称：['name', 'address', 'website']。"
        A1 = json.dumps(
        {
                "type":"JOIN",
                "columns":[],
                "number":8,
                "fill":"AVERAGE"
            },
            ensure_ascii=False
        )
        Q2 = "同时使用 JOIN 和 UNION 的方式做表格增强。请在增强时重点关注导演名和电影名称，对于缺失值，使用模型预测填充。这是我的表格列的名称：['director name', 'movie name', 'province', 'country']。"
        A2 = json.dumps(
        {
                "type":"BOTH",
                "columns":['director name','movie name'],
                "number":6,
                "fill":"MODEL"
            },
            ensure_ascii=False
        )
        Q3 = "主要使用 UNION 操作进行表格增强。增强后列的数量大约在10列左右，使用随机数填充缺失值。这是我的表格列的名称：['card_id', 'student_name', 'school', 'country']"
        A3 = json.dumps(
        {
                "type":"UNION",
                "columns":[],
                "number":6,
                "fill":"MODEL"
            },
            ensure_ascii=False
        )
        prompt = f"""你是一个参数提取专家，请结合对话上下文，从用户所有的的自然语言描述中，提取出表格增强的关键词，输出一个包含type、columns、number和fill四个属性的json对象。用户可能对关键词有新增或修改操作。
以下是四个参数的相关信息{EnhanceParas.model_json_schema()}。
示例：
Q1：{Q1}
A1：{A1}
Q2：{Q2}
A2：{A2}
Q3：{Q3}
A3：{A3}"""
        return prompt

    def ask(self,chat_history:List[Dict],user_input:str):
        try:
            system_prompt = {"role": "system", "content": self.prompt}
            history = copy.deepcopy(chat_history)
            assert len(history) > 0
            if 'assistant' in history[0]['role']:
                del history[0]
            history.insert(0, system_prompt)
            return self.qwen.long_chat(history,user_input)
        except Exception as e:
            raise e

    def get_csv_headers(self, csv_path):
        with open(csv_path, mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            headers = next(reader)
        return headers

    def query(self,chat_history:List[Dict],user_input:str,table_path:str):
        try:
            csv_headers = self.get_csv_headers(table_path)
            u_input = user_input.strip()+f"这是这是我的表格列的名称：{str(csv_headers)}。"
            query_result = json.loads(self.ask(chat_history,u_input)[0])
            history = copy.deepcopy(chat_history)
            history.append({"role":"user","content":user_input})
            history.append({"role":"assistant","content":query_result})
            return history
        except Exception as e:
            raise e

    def trans_json_to_text(self,json_obj:Dict)->str:
        if json_obj["type"] == "JOIN":
            type = "连接"
        elif json_obj["type"] == "UNION":
            type = "联合"
        else:
            type = "连接和联合"
        columns = str(json_obj["columns"])
        columns = columns[1:-1]
        number = str(json_obj["number"])
        if json_obj["fill"] == "AVERAGE":
            fill = "平均值"
        elif json_obj["fill"] == "MEAN":
            fill = "均值"
        else:
            fill = "模型预测的方式"
        result = "提取的关键词如下：\n"
        result += f"增强方式：{type}\n"
        result += f"重点关注列：{columns}\n"
        result += f"期望列数：{number}\n"
        result += f"填充方式：{fill}\n"
        return result

    def parse_text_to_json(self, text: str)->Dict:
        lines = text.strip().split('\n')
        data = {}
        for line in lines:
            if "增强方式：" in line:
                type_str = line.split("：")[1].strip()
                if type_str == "连接":
                    data["type"] = "JOIN"
                elif type_str == "联合":
                    data["type"] = "UNION"
                else:
                    data["type"] = "BOTH"
            elif "重点关注列：" in line:
                columns_str = line.split("：")[1].strip()
                # 处理字符串形式的列表，例如 "col1, col2" -> ["col1", "col2"]
                data["columns"] = [col.strip().strip("'\"") for col in columns_str.split(',')]
                data["columns"] = [column for column in data["columns"] if column.strip() != ""]
            elif "期望列数：" in line:
                data["number"] = int(line.split("：")[1].strip())
            elif "填充方式：" in line:
                fill_str = line.split("：")[1].strip()
                if fill_str == "平均值":
                    data["fill"] = "AVERAGE"
                elif fill_str == "均值":
                    data["fill"] = "MEAN"
                else:
                    data["fill"] = "MODEL"

        return json.loads(EnhanceParas(**data).model_dump_json())

    def trans_front_to_back(self, dialogue:List[Dialogue]):
        backend_dialogue = copy.deepcopy(dialogue)
        for one_dialogue in backend_dialogue:
            if one_dialogue["role"] == "assistant" and ("提取的关键词如下：" in one_dialogue["content"] and "增强完成" not in one_dialogue["content"]):
                one_dialogue["content"] = self.parse_text_to_json(one_dialogue["content"])
        return backend_dialogue

    def trans_back_to_front(self, dialogue:List[Dialogue]):
        front_dialogue = copy.deepcopy(dialogue)
        for one_dialogue in front_dialogue:
            if one_dialogue["role"] == "assistant" and isinstance(one_dialogue["content"],Dict):
                one_dialogue["content"] = self.trans_json_to_text(one_dialogue["content"])
        return front_dialogue