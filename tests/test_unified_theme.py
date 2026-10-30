import unittest
from importlib.resources import files

class UnifiedThemeTests(unittest.TestCase):
    def test_theme_asset_and_safe_scope(self):
        server=files("terminan").joinpath("unified_server.py").read_text(encoding="utf-8")
        js=files("terminan").joinpath("unified.js").read_text(encoding="utf-8")
        css=files("terminan").joinpath("unified_theme.css").read_text(encoding="utf-8")
        self.assertIn("'/unified_theme.css':'unified_theme.css'",server)
        self.assertIn("link[data-terminan-theme]",js)
        self.assertIn("theme.href='/unified_theme.css'",js)
        self.assertIn("doc.head.append(theme)",js)
        self.assertIn("--terminan-accent:",css)
        self.assertNotIn("canvas{",css)
        self.assertNotIn("svg{",css)
        self.assertNotIn(".price-cluster-level{",css)

if __name__=="__main__":
    unittest.main()
