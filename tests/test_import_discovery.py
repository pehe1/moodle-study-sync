import json
from contextlib import closing
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest


class ImportDiscoveryTest(unittest.TestCase):
    def test_new_resources_are_discovered_and_removed_resources_preserve_receipts(self):
        project = Path(__file__).resolve().parents[1]
        scratch = project / "tests" / ".tmp"
        scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as temporary:
            root = Path(temporary).resolve()
            collector = root / "collector"
            collector.mkdir()
            database = collector / "moodle_state.db"
            with closing(sqlite3.connect(database)) as connection, connection:
                connection.execute("CREATE TABLE files (course_id INTEGER,module_id INTEGER,saved_to TEXT,"
                                   "time_stamp INTEGER,module_name TEXT,section_name TEXT,module_modname TEXT,deleted INTEGER)")
                for identifier in (10, 11):
                    path = collector / f"aula-{identifier}.pdf"
                    path.write_bytes(f"synthetic material {identifier}".encode())
                    connection.execute("INSERT INTO files VALUES (?,?,?,?,?,?,?,?)",
                                       (12, identifier, str(path), 1, f"Aula {identifier}", "Unidade", "resource", 0))
            inventory = root / "inventory.json"
            inventory.write_text(json.dumps({"course_id": "12", "local_name": "Matéria", "resources": [
                {"resource_id": "10", "title": "Aula anterior", "section": "Unidade",
                 "google_source_id": "existing-receipt", "uploaded_sha256": "prior-version"}]}), encoding="utf-8")
            command = [sys.executable, str(project / "tools" / "import_moodle_dl.py"),
                       "--state-dir", str(collector), "--inventory", str(inventory),
                       "--root", str(root), "--semester", "Semestre", "--discover-new"]
            first = subprocess.run(command, capture_output=True, text=True, check=True, timeout=30)
            self.assertEqual(json.loads(first.stdout)["discovered_resources"], 1)
            manifest = json.loads(inventory.read_text(encoding="utf-8"))
            self.assertEqual(len(manifest["resources"]), 2)
            self.assertEqual(manifest["resources"][0]["google_source_id"], "existing-receipt")
            preserved = root / manifest["resources"][0]["local_path"]
            with closing(sqlite3.connect(database)) as connection, connection:
                connection.execute("UPDATE files SET deleted=1 WHERE module_id=10")
            subprocess.run(command, capture_output=True, text=True, check=True, timeout=30)
            manifest = json.loads(inventory.read_text(encoding="utf-8"))
            self.assertTrue(manifest["resources"][0]["moodle_removed"])
            self.assertTrue(preserved.is_file())
            self.assertEqual(manifest["resources"][0]["google_source_id"], "existing-receipt")
            self.assertEqual(manifest["resource_count"], 1)
            self.assertEqual(manifest["resource_download_count"], 1)

            # Uma publicação pode trazer exercício e gabarito. O arquivo
            # anterior conserva seu recibo e o segundo ganha identidade própria.
            manifest['resources'][1]['google_source_id'] = 'lecture-receipt'
            inventory.write_text(json.dumps(manifest), encoding='utf-8')
            answer = collector / 'gabarito.pdf'
            answer.write_bytes(b'synthetic answer sheet')
            with closing(sqlite3.connect(database)) as connection, connection:
                connection.execute('INSERT INTO files VALUES (?,?,?,?,?,?,?,?)',
                    (12, 11, str(answer), 1, 'Aula 11', 'Unidade', 'resource', 0))
            check = subprocess.run(command, capture_output=True, text=True, check=True, timeout=30)
            self.assertEqual(json.loads(check.stdout)['discovered_resources'], 1)
            manifest = json.loads(inventory.read_text(encoding='utf-8'))
            active = [i for i in manifest['resources'] if not i.get('moodle_removed')]
            self.assertEqual(len(active), 2)
            self.assertEqual(len({i['moodle_file_key'] for i in active}), 2)
            self.assertEqual(sum(i.get('google_source_id') == 'lecture-receipt' for i in active), 1)
            self.assertTrue(any('gabarito.pdf' in i['title'] for i in active))
            check = subprocess.run(command, capture_output=True, text=True, check=True, timeout=30)
            self.assertEqual(json.loads(check.stdout)['discovered_resources'], 0)
            with closing(sqlite3.connect(database)) as connection, connection:
                connection.execute('UPDATE files SET deleted=1 WHERE saved_to=?', (str(answer),))
            subprocess.run(command, capture_output=True, text=True, check=True, timeout=30)
            manifest = json.loads(inventory.read_text(encoding='utf-8'))
            self.assertEqual(manifest['resource_count'], 1)
            self.assertTrue(next(i for i in manifest['resources'] if 'gabarito.pdf' in i['title'])['moodle_removed'])


if __name__ == "__main__":
    unittest.main()
