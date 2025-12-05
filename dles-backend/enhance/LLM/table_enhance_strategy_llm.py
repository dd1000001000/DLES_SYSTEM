# -*- coding: utf-8 -*-
import json
from typing import List, Dict

from enhance.enhance_main.model.models import EnhanceParas
from enhance.qwen.qwen import Qwen

class TableEnhanceStrategyLLM:
    def __init__(self,model_name:str="deepseek-v3"):
        self.qwen = Qwen(model_name)
        self.prompt = self.get_prompt()

    def get_prompt(self):
        table_example = json.dumps([['column1 header', 'column2 header', 'column3 header'],
                         ['line1 column1', 'line1 column2', 'line1 column3'],
                         ['line2 column1', 'line2 column2', 'line2 column3']],ensure_ascii=False)
        json_output = str({"join_operations":[],"union_operations":[]}).replace("'",'"')
        join_output = str([['查询表列a','相关表编号.相关表列b','相关表保留列b','相关表保留列c']]).replace("'",'"')
        join_output_explain = ("列表中的每一项都是列表，分别代表一个连接操作。"
                               "子列表的第一项和第二项代表被用作JOIN操作的两列，即使用用户查询表列a与相关表列b（由相关表编号确定相关表，按照自然数编号）进行JOIN操作。"
                               "子列表的剩下几项代表相关表的保留列，示例同时相关表保留列b和列c，相关表被用作JOIN操作的列必须出现在列表中，保留列必须来自被连接的相关表。")
        union_output = str([['1.相关表列a','1.相关表列b+1.相关表列a','2.相关表列b','2.相关表列c+3.相关表列d','3.相关表列a'],['column1','column3','column2','column4','column5']]).replace("'",'"')
        union_output_explain = ("联合增强操作是一个长度为偶数的列表，列表中的每连续两项代表一个联合增强操作。"
                                "连续两项中的第一个列表代表与了与查询表格进行UNION操作而通过相关表格得到的完整表格，每一项代表这一项由相关表格的哪张表格的哪一列组成。如果这项有'+'，则代表这一列是连接不同相关表格的JOIN列。"
                                "连续两项中的第二个列表的第i列则是代表当前拼接出的表格的第i列与经过JOIN操作后的某列相互对应，输出的名称必须在JOIN后的表格中存在。")
        enhance_para = {"type":"BOTH",
                "columns":['director','date'],
                "number":4,
                "fill":"MODEL"}
        query_table = [['park name','director','date'],['park1','director1','2024-10-11'],['park2','Jimmy','2024-10-12']]
        join_table =[['movie name','data'],['name1','2024-10-11'],['name2','2025-01-01']]
        union_table = [['director name','date','movie name'],['director3','2023-12-31','name2'],['James Cameron','1997-12-19','RMS Titanic']]
        json_enhance_input = json.dumps({"enhance_paras":enhance_para,"query_table":query_table,"related_tables":[join_table,union_table]},ensure_ascii=False)
        join_enhance_output = str({"join_operations":[['date','1.date','date','movie name']],"union_operations":[['2.director name','2.date','2.movie name'],['director','date','movie name']]}).replace("'",'"')

        prompt = f"""你是一个表格增强专家，请结合用户查询表、相关表信息和增强参数给出对用户查询表进行增强的增强建议。
查询表和相关表均为二维数组，首行为列头，相关表编号从1开始（如第一个相关表为表1）。
以下是四个增强参数的相关信息：{EnhanceParas.model_json_schema()}，你不需要考虑其中的fill参数。
以下是用户查询表和相关表格的格式：{table_example}。
以下是你应该输出的json格式：{json_output}。
以下是join_operations的示例和说明：
{join_output}
{join_output_explain}
以下是union_operations的示例和说明：
{union_output}
{union_output_explain}
除此之外，按照以下几点要求给出增强建议：
1.输出格式必须与示例输出格式一致，禁止省略任何括号。
2.默认先进行JOIN操作，再进行UNION操作。
3.增强后的表格列数可以与用户的要求不一致。
4.优先使用重点增强列进行关联。
5.当目标列数不足时，优先保留与查询表关联性强的列。
6.避免在结果中产生重复列。
7.跨表UNION时需保持列语义一致。
示例：
Q：{json_enhance_input}
A：{join_enhance_output}
"""
        return prompt

    def ask(self,query_table:List[List],related_tables:List[List],enhance_paras:Dict):
        try:
            user_input = str({"enhance_paras":enhance_paras,"query_table":query_table,"related_tables":related_tables}).replace("'",'"')
            return json.loads(self.qwen.ask_one(self.prompt,user_input)[0])
        except Exception as e:
            raise e

if __name__ == '__main__':
    obj = TableEnhanceStrategyLLM()
    print(obj.prompt)
    query_table = [['id','name','department'],['001','chen','physics'],['002','ding','math']]
    related_table_one = [['department','established date'],['math','1990-01-03'],['pyhsics','2000-01-01'],['computer','2005-10-01']]
    related_table_two = [['staff name','department'],['li','math'],['wang','math']]
    related_table = [related_table_one,related_table_two]
    enhance_paras = {"type":"BOTH",
                    "columns":['department'],
                    "number":6,
                    "fill":"MODEL"}
    result = obj.ask(query_table,related_table,enhance_paras)
    print(result)