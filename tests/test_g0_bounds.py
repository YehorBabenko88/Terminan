import unittest
from terminan.dom import BookEngine, Snapshot, Delta, Level
from terminan.dom_stream import BoundedFeed, FeedEnvelope

class Bounds(unittest.TestCase):
    def test_iterable_stops_at_batch_bound(self):
        consumed=[]
        def levels():
            for n in range(100010):
                consumed.append(n)
                yield Level('bid',n,1)
        with self.assertRaises(ValueError): BookEngine().snapshot(Snapshot('e',1,levels()))
        self.assertEqual(len(consumed),100001)

    def test_book_size_bound_is_atomic(self):
        book=BookEngine(max_levels=2)
        book.snapshot(Snapshot('e',1,(Level('bid',1,1),Level('ask',2,1))))
        before=book.view
        with self.assertRaises(ValueError):book.delta(Delta('e',2,1,(Level('ask',3,1),)))
        self.assertEqual(book.view,before)

    def test_symbol_cache_bound_rejects_without_queue_growth(self):
        feed=BoundedFeed(4,max_symbols=1)
        feed.publish(FeedEnvelope('BTC',Snapshot('e',1,())))
        with self.assertRaises(ValueError):feed.publish(FeedEnvelope('ETH',Snapshot('e',1,())))
        self.assertEqual(feed.queued,1)
