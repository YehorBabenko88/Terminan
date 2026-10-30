import unittest
from importlib.resources import files

class UnifiedWorkspaceNavigationTests(unittest.TestCase):
    def test_all_primary_pages_load_navigation(self):
        for name in ("index.html","monitor.html","math_lab.html","history_overlay.html"):
            with self.subTest(name=name):
                html=files("terminan").joinpath(name).read_text(encoding="utf-8")
                self.assertEqual(html.count('src="/workspace-nav.js"'),1)
    def test_navigation_only_links_existing_primary_routes(self):
        script=files("terminan").joinpath("workspace_nav.js").read_text(encoding="utf-8")
        for route in ("/","/monitor","/math","/history-overlay"):
            self.assertIn("'"+route+"'",script)
        self.assertNotIn("['/saved',",script)
        self.assertIn("отдельный сервер",script)
    def test_server_exposes_nav_script(self):
        source=files("terminan").joinpath("server.py").read_text(encoding="utf-8")
        self.assertIn("url.path == '/workspace-nav.js'",source)
        self.assertIn("application/javascript",source)

if __name__=="__main__":
    unittest.main()
