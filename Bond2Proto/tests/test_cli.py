import os
from pathlib import Path
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from bond2proto import cli


class CliTests(unittest.TestCase):
    @patch("bond2proto.cli.subprocess.run")
    def test_sets_include_path_and_forwards_arguments(self, run):
        run.return_value.returncode = 7
        schema = Path(__file__).with_name("import_core.bond").resolve()

        with patch.dict(os.environ, {}, clear=False):
            result = cli.main([str(schema)])
            command = run.call_args.args[0]

            self.assertEqual(result, 7)
            self.assertTrue(Path(command[0]).is_absolute())
            self.assertEqual(Path(command[0]).name, "gbc.exe")
            self.assertEqual(command[1:4], ["protobuf", "-i", str(cli._PACKAGE_DIR)])
            self.assertEqual(command[4:], [str(schema)])
            self.assertEqual(os.environ["BOND_INCLUDE_PATH"], str(cli._BOND_CORE_DIR))

    @patch("bond2proto.cli.subprocess.run")
    def test_parses_all_forwarded_options(self, run):
        run.return_value.returncode = 0
        schema = Path(__file__).with_name("import_core.bond").resolve()

        result = cli.main([
            "-i", "first",
            "--import-dir=second",
            "-o", "out",
            "-n", "bond.one=proto.one",
            "--namespace=bond.two=proto.two",
            "-j",
            str(schema),
        ])

        self.assertEqual(result, 0)
        self.assertEqual(run.call_args.args[0], [
            str(cli._GBC_EXE),
            "protobuf",
            "-i", str(cli._PACKAGE_DIR),
            "-i", "first",
            "-i", "second",
            "-o", "out",
            "-n", "bond.one=proto.one",
            "-n", "bond.two=proto.two",
            "--jobs=0",
            str(schema),
        ])

    @patch("bond2proto.cli.subprocess.run")
    def test_expands_directory_recursively_and_ignores_other_files(self, run):
        run.return_value.returncode = 0

        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            nested = root / "nested"
            nested.mkdir()
            first = root / "first.bond"
            second = nested / "second.BOND"
            first.write_text("namespace test", encoding="utf-8")
            second.write_text("namespace test", encoding="utf-8")
            (root / "ignored.txt").write_text("ignored", encoding="utf-8")

            result = cli.main([str(root)])
            command = run.call_args.args[0]

            self.assertEqual(result, 0)
            self.assertEqual(command[-2:], [str(first.resolve()), str(second.resolve())])

    @patch("bond2proto.cli.subprocess.run")
    def test_help_is_generated_by_argparse(self, run):
        output = StringIO()
        with redirect_stdout(output), self.assertRaises(SystemExit) as raised:
            cli.main(["--help"])

        self.assertEqual(raised.exception.code, 0)
        help_text = output.getvalue()
        self.assertIn("usage: b2p", help_text)
        self.assertIn("--output-dir", help_text)
        self.assertNotIn("--no-banner", help_text)
        self.assertIn("--open-skill", help_text)
        self.assertIn("examples:", help_text)
        self.assertIn("b2p -o proto-output schema.bond", help_text)
        self.assertNotIn("--numeric-version", help_text)
        run.assert_not_called()

    @patch("bond2proto.cli.subprocess.run")
    def test_removed_no_banner_option_is_rejected(self, run):
        schema = Path(__file__).with_name("import_core.bond").resolve()
        error = StringIO()

        with redirect_stderr(error), self.assertRaises(SystemExit) as raised:
            cli.main(["--no-banner", str(schema)])

        self.assertEqual(raised.exception.code, 2)
        self.assertIn("unrecognized arguments: --no-banner", error.getvalue())
        run.assert_not_called()

    @patch("bond2proto.cli.subprocess.run")
    @patch("bond2proto.cli.os.startfile")
    def test_open_skill_opens_bundled_skill_directory(self, startfile, run):
        result = cli.main(["--open-skill"])

        self.assertEqual(result, 0)
        startfile.assert_called_once_with(str(cli._SKILL_DIR))
        run.assert_not_called()

    @patch("bond2proto.cli.subprocess.run")
    def test_version_prints_package_and_compiler_versions(self, run):
        run.return_value.returncode = 0
        run.return_value.stdout = "0.13.0.1\n"
        run.return_value.stderr = ""
        output = StringIO()

        with redirect_stdout(output):
            result = cli.main(["--version"])

        self.assertEqual(result, 0)
        self.assertEqual(
            run.call_args.args[0],
            [str(cli._GBC_EXE), "--numeric-version"],
        )
        self.assertIn("Bond2Proto 0.0.1", output.getvalue())
        self.assertIn("Bond Compiler 0.13.0.1", output.getvalue())


if __name__ == "__main__":
    unittest.main()
