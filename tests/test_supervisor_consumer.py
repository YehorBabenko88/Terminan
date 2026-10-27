import unittest
from unittest.mock import patch
from terminan.supervisor_consumer import supervisor_status

class SupervisorConsumerTests(unittest.TestCase):
    def test_missing(self):
        with patch.dict("os.environ",{},clear=True):
            self.assertEqual(supervisor_status()["state"],"UNAVAILABLE")
    def test_invalid_port(self):
        with patch.dict("os.environ",{"TERMINAN_SUPERVISOR_CONTRACT_PORT":"not-a-port"}):
            self.assertEqual(supervisor_status()["reason"],"INVALID_LOOPBACK_PORT")
    def test_no_remote_address(self):
        with patch.dict("os.environ",{"TERMINAN_SUPERVISOR_CONTRACT_PORT":"99999"}):
            self.assertEqual(supervisor_status()["state"],"UNAVAILABLE")
if __name__=="__main__":unittest.main()
