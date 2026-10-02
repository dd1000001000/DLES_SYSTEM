# -*- coding: utf-8 -*-
"""
增强模块的回归测试。运行（在 dles-backend 目录下）：
  python -m unittest discover -s tests -v
"""
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from enhance.LLM.llm_client import LLMClient, LLMConfig
from enhance.enhance_main.service import enhance_main_service as ems
from enhance.enhance_main.service.enhance_main_service import EnhanceMainService
from utils.read_config.read_config import resolve_data_path


class EnhanceLogicTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 不走构造函数（它要查数据库），这里测的都是纯表格逻辑
        cls.svc = object.__new__(EnhanceMainService)
        cls.svc._filler = None

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def csv(self, name, df):
        path = os.path.join(self.tmp, name)
        df.to_csv(path, index=False)
        return path

    # ---------- 读取 ----------
    def test_leading_zeros_survive_read(self):
        path = os.path.join(self.tmp, 'zip.csv')
        with open(path, 'w') as f:
            f.write('zip,n,price\n02134,1,1.5\n00501,2,\n')
        df = ems.read_table_csv(path)
        self.assertEqual(df['zip'].tolist(), ['02134', '00501'])
        self.assertTrue(pd.api.types.is_numeric_dtype(df['n']))
        self.assertTrue(pd.api.types.is_numeric_dtype(df['price']))

    # ---------- JOIN ----------
    def test_join_does_not_match_empty_keys(self):
        user = pd.DataFrame({'id': ['a', None, 'c'], 'x': [1, 2, 3]})
        rel = self.csv('rel.csv', pd.DataFrame({'id': ['a', None, 'z'], 'info': ['A', 'NULL-ROW', 'Z']}))
        out = self.svc.apply_join_operations(user, [['id', '1.id', 'info']], [rel])
        self.assertEqual(len(out), 3)
        self.assertEqual(out['info'].tolist()[0], 'A')
        self.assertTrue(out['info'].iloc[1:].isna().all())

    def test_join_numeric_key_with_text_key(self):
        user = pd.DataFrame({'id': [1, 2, 3], 'x': [1, 2, 3]})
        rel = self.csv('rel.csv', pd.DataFrame({'id': ['1', ' 2 ', 'x'], 'info': ['i1', 'i2', 'ix']}))
        out = self.svc.apply_join_operations(user, [['id', '1.id', 'info']], [rel])
        self.assertEqual(out['info'].tolist()[:2], ['i1', 'i2'])
        self.assertTrue(pd.isna(out['info'].iloc[2]))

    def test_join_keeps_column_order_and_all_rows(self):
        user = pd.DataFrame({'id': [1, 2], 'x': [1, 2]})
        rel = self.csv('rel.csv', pd.DataFrame({'id': [1, 1, 2], 'a': ['a1', 'dup', 'a2'], 'b': ['b1', 'b2', 'b3'], 'c': [1, 2, 3]}))
        out = self.svc.apply_join_operations(user, [['id', '1.id', 'c', 'a', 'b']], [rel])
        self.assertEqual(len(out), 2)  # 相关表里键重复也不会让用户表的行变多
        self.assertEqual(list(out.columns), ['id', 'x', 'c', 'a', 'b'])

    # ---------- UNION ----------
    def test_chain_join_matches_rows_by_key(self):
        t1 = self.csv('t1.csv', pd.DataFrame({'k1': [1, 2, 3], 'a': ['a1', 'a2', 'a3']}))
        t2 = self.csv('t2.csv', pd.DataFrame({'k1': [1, 2, 3], 'k2': [10, 20, 30]}))
        t3 = self.csv('t3.csv', pd.DataFrame({'k2': [30, 10, 20], 'c': ['c30', 'c10', 'c20']}))
        res = self.svc.get_join_table_df(['1.a', '1.k1+2.k1', '2.k2+3.k2', '3.c'], ['a', 'key1', 'key2', 'c'], [t1, t2, t3])
        got = {(r.a, r.key2, r.c) for r in res.itertuples()}
        self.assertEqual(got, {('a1', 10, 'c10'), ('a2', 20, 'c20'), ('a3', 30, 'c30')})

    def test_unconnected_tables_are_stacked_not_glued_by_row_number(self):
        t4 = self.csv('t4.csv', pd.DataFrame({'p': ['p1', 'p2', 'p3', 'p4']}))
        t5 = self.csv('t5.csv', pd.DataFrame({'q': ['q1', 'q2']}))
        res = self.svc.get_join_table_df(['1.p', '2.q'], ['col', 'col'], [t4, t5])
        self.assertEqual(res['col'].tolist(), ['p1', 'p2', 'p3', 'p4', 'q1', 'q2'])  # 同名目标列：各表的行上下接在一起
        res = self.svc.get_join_table_df(['1.p', '2.q'], ['col_p', 'col_q'], [t4, t5])
        self.assertEqual(len(res), 6)
        self.assertEqual(res['col_p'].notna().sum(), 4)
        self.assertEqual(res['col_q'].notna().sum(), 2)
        self.assertFalse((res['col_p'].notna() & res['col_q'].notna()).any())

    def test_union_ignores_unknown_target_columns(self):
        user = pd.DataFrame({'name': ['a'], 'city': ['x']})
        rel = self.csv('rel.csv', pd.DataFrame({'n': ['b', 'c'], 'z': ['zz', 'yy']}))
        out = self.svc.apply_union_operations(user, [['1.n', '1.z'], ['name', 'made_up_column']], [rel])
        self.assertEqual(list(out.columns), ['name', 'city'])
        self.assertEqual(out['name'].tolist(), ['a', 'b', 'c'])

    def test_union_row_cap_and_dedupe_of_new_rows_only(self):
        user = pd.DataFrame({'name': ['a', 'a']})  # 用户自己的重复行不动
        rel = self.csv('rel.csv', pd.DataFrame({'n': ['a'] + [f'r{i}' for i in range(ems.UNION_MAX_ROWS + 50)]}))
        out = self.svc.apply_union_operations(user, [['1.n'], ['name']], [rel])
        self.assertEqual(out['name'].tolist()[:2], ['a', 'a'])
        self.assertEqual(len(out), 2 + ems.UNION_MAX_ROWS)  # 'a' 已存在，不再追加；其余最多追加 UNION_MAX_ROWS 行

    def test_bad_operations_are_skipped(self):
        user = pd.DataFrame({'name': ['a']})
        out = self.svc.apply_union_operations(user, [['9.n'], ['name']], [])
        self.assertEqual(out['name'].tolist(), ['a'])
        out = self.svc.apply_join_operations(user, [['nope', '1.id', 'x'], 'garbage'], [])
        self.assertEqual(out['name'].tolist(), ['a'])

    # ---------- 填充 ----------
    def test_model_fill_with_mixed_str_and_number_column(self):
        user = pd.DataFrame({'name': ['a', 'b'], 'score': [1.0, None], 'code': ['x', 'y']})
        union = pd.DataFrame({'name': ['c', 'd'], 'score': [3.0, 4.0], 'code': [5, 6]})
        df = pd.concat([user, union], ignore_index=True)
        self.svc._filler = lambda queries, **kwargs: [[{'token_str': 'word'}] for _ in queries]  # 不依赖 BERT
        self.svc.fill_vacancy_values(df, 'MODEL')
        self.assertFalse(df.isna().any().any())

    def test_average_fill_of_all_empty_numeric_column(self):
        df = pd.DataFrame({'x': [1.0, 3.0], 'joined': [np.nan, np.nan]})
        self.svc.fill_vacancy_values(df, 'AVERAGE')
        self.assertEqual(df['joined'].tolist(), [0, 0])
        df = pd.DataFrame({'x': [1.0, 3.0, np.nan]})
        self.svc.fill_vacancy_values(df, 'AVERAGE')
        self.assertEqual(df['x'].tolist(), [1.0, 3.0, 2.0])

    @unittest.skipUnless(os.path.isdir(resolve_data_path(ems.config['bert_model_path'])), '没有下载 BERT 模型')
    def test_bert_fill_with_very_long_text(self):
        svc = object.__new__(EnhanceMainService)
        svc._filler = None
        df = pd.DataFrame({'desc': ['word ' * 300 if i % 2 == 0 else None for i in range(6)]})
        svc.fill_vacancy_values(df, 'MODEL')
        self.assertFalse(df['desc'].isna().any())

    # ---------- 列数 ----------
    def test_trim_columns_drops_emptiest_added_columns_only(self):
        df = pd.DataFrame({'a': [1, 2, 3, 4], 'b': [1, 2, 3, 4], 'new1': [1, 2, 3, 4],
                           'new2': [1, None, None, None], 'new3': [1, 2, None, None], 'focus': [None] * 4})
        out = EnhanceMainService.trim_columns(df, ['a', 'b'], 4, ['focus'])
        self.assertEqual(list(out.columns), ['a', 'b', 'new1', 'focus'])
        # 期望列数比原表还少时，不删用户自己的列
        out = EnhanceMainService.trim_columns(df, ['a', 'b'], 1, [])
        self.assertEqual(list(out.columns), ['a', 'b'])
        self.assertIs(EnhanceMainService.trim_columns(df, ['a', 'b'], 20, []), df)

    # ---------- 发给大模型的样本 ----------
    def test_sample_rows_are_truncated(self):
        wide = pd.DataFrame({f'c{i}': ['x' * 500] * 3 for i in range(ems.SAMPLE_MAX_COLUMNS + 10)})
        sample = self.svc.read_csv_random_rows(self.csv('wide.csv', wide))
        self.assertEqual(len(sample[0]), ems.SAMPLE_MAX_COLUMNS)
        self.assertTrue(all(len(cell) <= ems.SAMPLE_CELL_CHARS + 1 for row in sample for cell in row))
        path = os.path.join(self.tmp, 'ragged.csv')
        with open(path, 'wb') as f:
            f.write('a,b,c\n1,2\n\xe4\xb8\xad,\xff,3\n'.encode('latin-1'))  # 行列数不齐、含非 UTF-8 字节
        sample = self.svc.read_csv_random_rows(path)
        self.assertTrue(all(len(row) == 3 for row in sample))


class LongChatTest(unittest.TestCase):
    def test_dict_history_is_sent_as_json(self):
        os.environ['DLES_ALLOW_PRIVATE_LLM_ENDPOINTS'] = '1'
        client = LLMClient(LLMConfig(base_url='http://localhost:1/v1', api_key='k', chat_model='m'))
        sent = {}

        class Msg:
            content = '{}'

        class Choice:
            message = Msg()

        class Completion:
            choices = [Choice()]

            def model_dump(self):
                return {}

        def fake_create(messages, output_json, max_tokens):
            sent['messages'] = messages
            return Completion()

        client._create = fake_create
        client.long_chat([{'role': 'assistant', 'content': {'type': 'JOIN', 'columns': ['名称']}}], 'hi')
        content = sent['messages'][0]['content']
        self.assertEqual(content, '{"type": "JOIN", "columns": ["名称"]}')


if __name__ == '__main__':
    unittest.main()
