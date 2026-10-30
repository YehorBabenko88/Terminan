import unittest
from importlib.resources import files

class MathGraphCompositionTests(unittest.TestCase):
    def test_dragged_graph_is_checked_before_math_execution(self):
        page=files("terminan").joinpath("math_lab.html").read_text(encoding="utf-8")
        for token in ("series-a","series-b","difference","energy","INVALID_GRAPH_COMPONENTS",
                      "/api/math/ports","math.port-graph.v1","trading_authorized:false"):
            self.assertIn(token,page)
        self.assertIn("necessary.some(v=>selected.filter(x=>x===v).length!==1)",page)
        self.assertIn("source_attested:false",page)
        for token in ("terminan.math.composition.v1", "INVALID_COMPOSITION", "GRAPH_IMPORT_REJECTED", "SCHEMA_IMPORTED_UNATTESTED", "INVALID_EDGES"):
            self.assertIn(token,page)
        for token in ("diffInput1","diffInput2","energyInput","INVALID_PORT_CONNECTIONS","edges:[{from:input1"):
            self.assertIn(token,page)

if __name__=="__main__":
    unittest.main()
