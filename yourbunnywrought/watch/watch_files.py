from __future__ import annotations

import asyncio
from dataclasses import dataclass
from fnmatch import fnmatch
import json
from pathlib import Path

from watchfiles import Change, awatch

from ..argtypes import ArgTypes
from ..scripts import run_line

__all__ = ['init_cli', 'invoke_cli', 'watch_files', 'handle_updates']


@dataclass
class FileChangeHandler:
    patterns: list[str]
    script: list[str]
    expects_file: bool = False

    def __post_init__(self):
        self.expects_file = any(token == ':file' for token in self.script)

    def script_for_path(self, path: str):
        if not self.expects_file:
            return self.script

        return [token if token != ':file' else path for token in self.script]


_updates = asyncio.Queue()


async def watch_files(paths: list[Path], handlers: list[FileChangeHandler]):
    async for changes in awatch(*paths):
        for change, path in changes:
            for handler in handlers:
                if change is Change.deleted and handler.expects_file:
                    continue

                if not any(fnmatch(path, p) for p in handler.patterns):
                    continue

                _updates.put_nowait(handler.script_for_path(path))
                break


async def handle_updates():
    while True:
        script = await _updates.get()
        run_line(script)


def _load_handlers_file(infile: Path) -> tuple[list[Path], list[FileChangeHandler]]:
    obj = json.loads(infile.read_text(encoding='utf-8'))

    paths = [ArgTypes.existing_directory_type(path) for path in obj['paths']]
    handlers = [FileChangeHandler(handler['patterns'], handler['script']) for handler in obj['handlers']]

    return paths, handlers


def init_cli(parent):
    parser = parent.add_parser('watch_files', aliases=['watch'], add_help=False)

    parser.add_argument('handlers_file', type=ArgTypes.existing_file_type)

    return ['watch_files', 'watch']


def invoke_cli(args):
    match args.command:
        case 'watch_files' | 'watch':
            paths, handlers = _load_handlers_file(args.handlers_file)

            loop = asyncio.get_event_loop()

            try:
                loop.create_task(watch_files(paths, handlers))
                loop.create_task(handle_updates())
                loop.run_forever()
            except KeyboardInterrupt:
                pass
            finally:
                loop.close()
