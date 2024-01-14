from functools import cached_property
import re
from shutil import which
from subprocess import check_output

__all__ = ['ExternalExecutable']


class ExternalExecutable:
    def __init__(self, *, executable: str, version_option: str, version_pattern: str):
        self.executable = executable
        self.version_option = version_option
        self.version_pattern = version_pattern
        self.version_string = self.check_available()

    @cached_property
    def executable_path(self) -> str | None:
        return which(self.executable)

    def check_available(self) -> str:
        if self.executable_path is None:
            raise RuntimeError(f'Cannot resolve {self.executable}')

        result = check_output([self.executable_path, self.version_option], encoding='utf-8')

        version = re.match(self.version_pattern, result, re.MULTILINE)
        if version is None:
            raise RuntimeError(f'Cannot understand `{self.executable} {self.version_option}`, got {result!r}')

        return version.group(1)

    def run(self, *args) -> str:
        return check_output([self.executable_path, *args], encoding='utf-8')
