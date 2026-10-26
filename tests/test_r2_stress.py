import gc
import json
from pathlib import Path
import tracemalloc
import unittest
from terminan.synthetic import frame

class BoundedStress(unittest.TestCase):
    def test_golden_frame_and_fixed_replay_horizon(self):
        golden=json.loads(Path('terminan/fixtures/r2-golden-v1.json').read_text())
        for entry in golden:
            self.assertEqual(frame(**entry['request'])['frame_sha256'],entry['sha256'])

    def test_repeated_maximum_replay_does_not_retain_history(self):
        frame(step=600,scenario='mixed',timeframe='1h')
        gc.collect();tracemalloc.start()
        try:
            baseline=tracemalloc.get_traced_memory()[0]
            for i in range(12):
                value=frame(seed=17+i,step=600,scenario='mixed')
                self.assertLessEqual(len(value['events']),20)
                self.assertLessEqual(len(value['candles']),240)
            del value;gc.collect()
            current,peak=tracemalloc.get_traced_memory()
            self.assertLess(current-baseline,1024*1024)
            self.assertLess(peak,8*1024*1024)
        finally:tracemalloc.stop()
