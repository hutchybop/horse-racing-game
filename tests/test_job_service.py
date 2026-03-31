import unittest
from pathlib import Path

from jobs.service import get_job_command


class JobServiceTests(unittest.TestCase):
    def setUp(self):
        self.repo_root = Path("/tmp/test-repo")

    def test_get_job_command_scrape(self):
        cmd = get_job_command("scrape_races", repo_root=self.repo_root)
        self.assertEqual(cmd, ["/tmp/test-repo/races_scraper/races_scraper.py"])

    def test_get_job_command_move(self):
        cmd = get_job_command("move_races", repo_root=self.repo_root)
        self.assertEqual(cmd, ["/tmp/test-repo/races_scraper/util/move_races.py"])

    def test_get_job_command_rejects_unknown(self):
        with self.assertRaises(ValueError):
            get_job_command("bad_job", repo_root=self.repo_root)


if __name__ == "__main__":
    unittest.main()
