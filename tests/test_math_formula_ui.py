import unittest
from importlib.resources import files
class FormulaUITests(unittest.TestCase):
    def test_formula_is_delegated_to_math_and_marked_untrusted(self):
        html=files("terminan").joinpath("math_lab.html").read_text(encoding="utf-8")
        for needle in ('/api/math/formula','math.formula.v1','dimensionless','attested:false','INVALID_FORMULA_OR_SOURCE','runFormula'):
            self.assertIn(needle,html)
if __name__=='__main__':unittest.main()
