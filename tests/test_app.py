import io
import unittest

import pandas as pd
from streamlit.testing.v1 import AppTest

from app import csv_bytes, load_csv, review


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.terms = pd.DataFrame([{"zh": "钻石", "ko": "다이아몬드"}])

    def test_valid_translation(self):
        self.assertEqual(review("{n}个钻石", "{n}개의 다이아몬드", self.terms), [])

    def test_missing_term_and_placeholder(self):
        issues = review("{n}个钻石", "보석", self.terms)
        self.assertTrue(any("용어" in issue for issue in issues))
        self.assertIn("플레이스홀더/태그 불일치", issues)

    def test_placeholder_multiplicity(self):
        self.assertIn("플레이스홀더/태그 불일치", review("{n}{n}", "{n}", self.terms))

    def test_empty_and_chinese(self):
        self.assertIn("번역 누락", review("你好", "", self.terms))
        self.assertTrue(any("한자" in x for x in review("你好", "你好", self.terms)))

    def test_csv(self):
        frame = load_csv(io.BytesIO(b'id,zh,ko\n001,hello,NA\n'), ["id", "zh", "ko"])
        self.assertEqual(frame.iloc[0].tolist(), ["001", "hello", "NA"])
        with self.assertRaises(ValueError):
            load_csv(io.BytesIO(b'wrong\nx\n'), ["zh", "ko"])
        self.assertIn("'=SUM", csv_bytes(pd.DataFrame({"ko": ["=SUM(1)"]})).decode("utf-8-sig"))

    def test_streamlit(self):
        app = AppTest.from_file("app.py").run(timeout=20)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.metric[0].value, "0")
        app.checkbox[0].check().run()
        self.assertEqual(len(app.exception), 0)


if __name__ == "__main__":
    unittest.main()
