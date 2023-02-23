#! /home/glick094/WSL_Documents/python_venvs/venv_loris/bin python
import unittest

from db_connect import connect_to_database

# NOTE: from command line in LORIS_tools directory run: python -m unittest -v tests/test_database_connections.py

class TestDatabaseConnections(unittest.TestCase):
    def test_01_redcap(self):
        """Check if redcap_ro connection to production works"""
        test_cnx, test_cursor = connect_to_database("redcap")
        self.assertEqual(
            test_cnx.user,
            "redcap_ro",
            msg=f"Incorrect user returned: \n\tReturned -- '{test_cnx.user}' \n\tExpected -- 'redcap_ro'",
        )
        self.assertEqual(
            test_cnx.server_host,
            "loris.ahc.umn.edu",
            msg=f"Incorrect server_host returned: \n\tReturned -- '{test_cnx.server_host}' \n\tExpected -- 'loris.ahc.umn.edu'",
        )
        self.assertEqual(
            test_cnx.database,
            "icd",
            msg=f"Incorrect database returned: \n\tReturned -- '{test_cnx.database}' \n\tExpected -- 'icd'",
        )
        test_cnx.close()

    def test_02_prod(self):
        """Check if loris connection to production works"""
        test_cnx, test_cursor = connect_to_database("prod")
        self.assertEqual(
            test_cnx.user,
            "loris",
            msg=f"Incorrect user returned: \n\tReturned -- '{test_cnx.user}' \n\tExpected -- 'loris'",
        )
        self.assertEqual(
            test_cnx.server_host,
            "loris.ahc.umn.edu",
            msg=f"Incorrect server_host returned: \n\tReturned -- '{test_cnx.server_host}' \n\tExpected -- 'loris.ahc.umn.edu'",
        )
        self.assertEqual(
            test_cnx.database,
            "icd",
            msg=f"Incorrect database returned: \n\tReturned -- '{test_cnx.database}' \n\tExpected -- 'icd'",
        )
        test_cnx.close()

    def test_03_dev(self):
        """Check if devloris connection to development works"""
        test_cnx, test_cursor = connect_to_database("dev")
        self.assertEqual(
            test_cnx.user,
            "devloris",
            msg=f"Incorrect user returned: \n\tReturned -- '{test_cnx.user}' \n\tExpected -- 'devloris'",
        )
        self.assertEqual(
            test_cnx.server_host,
            "mphrndb.ahc.umn.edu",
            msg=f"Incorrect server_host returned: \n\tReturned -- '{test_cnx.server_host}' \n\tExpected -- 'mphrndb.ahc.umn.edu'",
        )
        self.assertEqual(
            test_cnx.database,
            "devicd",
            msg=f"Incorrect database returned: \n\tReturned -- '{test_cnx.database}' \n\tExpected -- 'devicd'",
        )
        test_cnx.close()

    def test_04_default(self):
        """Check if default redcap_ro connection to production works"""
        test_cnx, test_cursor = connect_to_database()
        self.assertEqual(
            test_cnx.user,
            "redcap_ro",
            msg=f"Incorrect user returned: \n\tReturned -- '{test_cnx.user}' \n\tExpected -- 'redcap_ro'",
        )
        self.assertEqual(
            test_cnx.server_host,
            "loris.ahc.umn.edu",
            msg=f"Incorrect server_host returned: \n\tReturned -- '{test_cnx.server_host}' \n\tExpected -- 'loris.ahc.umn.edu'",
        )
        self.assertEqual(
            test_cnx.database,
            "icd",
            msg=f"Incorrect database returned: \n\tReturned -- '{test_cnx.database}' \n\tExpected -- 'icd'",
        )
        test_cnx.close()

    def test_05_ValueError_wrongname(self):
        """Check ValueError handling is working when providing the wrong name"""
        self.assertRaisesRegex(ValueError, "Invalid DB connection", connect_to_database, "randomdb")
    
    def test_06_ValueError_notstring(self):
        """Check ValueError handling is working when providing a number"""
        self.assertRaisesRegex(ValueError, "Invalid DB connection", connect_to_database, 101010)

if __name__ == "__main__":
    unittest.main()
