import importlib.util,unittest
class MathNamespaceTests(unittest.TestCase):
 def test_only_canonical_math_namespace_is_available(self):
  import market_math
  self.assertTrue(callable(market_math.paper_fill_metrics));self.assertTrue(callable(market_math.candle_ohlcv_valid))
  self.assertIsNone(importlib.util.find_spec('market_profile_math'))
