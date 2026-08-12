from setuptools import setup
from setuptools.command.bdist_wheel import bdist_wheel as _bdist_wheel


class WindowsWheel(_bdist_wheel):
    """Tag the wheel for Windows without tying it to one Python ABI."""

    def finalize_options(self):
        super().finalize_options()
        self.root_is_pure = False

    def get_tag(self):
        return "py3", "none", "win_amd64"


setup(cmdclass={"bdist_wheel": WindowsWheel})
