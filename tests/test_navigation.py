import unittest
from importlib.resources import files

class NavigationTests(unittest.TestCase):
    def test_main_and_monitor_have_matching_navigation(self):
        for name, active in (("index.html", "/"), ("monitor.html", "/monitor")):
            with self.subTest(name=name):
                page=files("terminan").joinpath(name).read_text(encoding="utf8")
                self.assertIn('aria-label="Разделы Terminan"',page)
                self.assertIn('href="/"',page)
                self.assertIn('href="/monitor"',page)
                self.assertIn('href="'+active+'" aria-current="page"',page)
                self.assertIn('История / Кластеры · скоро',page)
                self.assertIn('Исследования · скоро',page)
                self.assertIn('Кэш · скоро',page)
                self.assertNotIn('href="/saved"',page)
                self.assertNotIn('href="/science"',page)
                self.assertNotIn('href="/cache"',page)

if __name__=="__main__":
    unittest.main()
