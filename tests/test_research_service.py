import unittest,asyncio
from decimal import Decimal
from terminan.research_service import ResearchService,ResearchSnapshot
from terminan.paper import PaperEngine

class ResearchServiceTests(unittest.TestCase):
    def test_view_service_uses_single_paper_engine_and_fail_closed_source(self):
        service=ResearchService(lambda value:None)
        self.assertIs(type(service.engine),PaperEngine)
        asyncio.run(service.refresh())
        self.assertEqual(service.snapshot().symbols,())
        self.assertIn('unavailable',service.snapshot().status)
        with self.assertRaises(RuntimeError):asyncio.run(service.configure_paper(enabled=True))
        self.assertFalse(service.engine.enabled)
    def test_historical_orderflow_presenter_keeps_quality_unverified(self):
        service=ResearchService(lambda value:None)
        service.load_orderflow_records([dict(timestamp_ms=1,price='2',volume='3',side='buy')])
        snapshot=service.snapshot()
        self.assertIsInstance(snapshot,ResearchSnapshot)
        self.assertEqual(snapshot.orderflow_rows[0].buy,'3')
        self.assertEqual(snapshot.orderflow_rows[0].quality,'UNVERIFIED')
