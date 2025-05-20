"""
Watcher process for ransomware detection based on the bit-per-byte entropy
value. All detection schemes assume the attack will not delete original files,
only override them.
"""

import argparse
import os
import time
import logging
import sys
import utils
from collections import Counter


# Logging options
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname).4s] - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)

# Argument parsing
parser = argparse.ArgumentParser(
    prog="entropy_detector",
    description="Background process that analyzes files for sudden entropy spikes",
)

parser.add_argument(
    "-w",
    "--workdir",
    default=os.getcwd(),
    help="The directory where the process will look for files to analyze. Defaults to the current working directory.",
)
parser.add_argument(
    "-r",
    "--recursion-level",
    type=int,
    default=0,
    help="The level of recursion for searching subdirectories. Default is 0 (only the specified directory).",
)
parser.add_argument(
    "-m",
    "--mode",
    type=int,
    default=1,
    help="Working mode, which can be one of the following: 1. Individual 2. Subdirectory Total 3. Subdirectory Average 4. Directory Total 5. Directory Average. Default is 1.",
)

args = parser.parse_args()


class DetectionScheme:

    def __init__(self, path: str, mode: int, rl: int):
        """
        Constructor method for this class.
        """
        schemes = {
            1: (self.individual, "Individual"),
            2: (self.subdirectory_total, "Subdirectory Total"),
            3: (self.subdirectory_average, "Subdirectory Average"),
            4: (self.directory_total, "Directory Total"),
            5: (self.directory_average, "Directory Average"),
        }
        self.mode = mode
        self.path = os.path.abspath(path)
        self.scheme, description = schemes[self.mode]

        print(f"Scanning directory {self.path}")
        print(f"    Mode: {description}")
        print(f"    Recursion level: {rl}")
        print()

    def individual(self, files: list[str]):
        """
        Detection scheme based on individual file entropy.

        Args:
            files (list): Files in the working directory.
        """
        return {f: round(utils.entropy(utils.bytecount(f)), 2) for f in files}

    def subdirectory_total(self, files: list[str]):
        """
        Detection scheme based on the total file bytecount on every directory.

        Args:
            files (list): Files in the working directory.
        """
        dirs = utils.group_by_dir(files)
        curr = {}

        for subdir, filenames in dirs.items():
            curr[subdir] = round(
                utils.entropy(sum([utils.bytecount(f) for f in filenames], Counter())),
                2,
            )

        return curr

    def subdirectory_average(self, files: list[str]):
        """
        Detection scheme based on the average file entropy on every directory.

        Args:
            files (list): Files in the working directory.
        """
        dirs = utils.group_by_dir(files)
        curr = {}

        for subdir, filenames in dirs.items():
            curr[subdir] = round(
                sum(utils.entropy(utils.bytecount(f)) for f in filenames)
                / len(filenames),
                2,
            )

        return curr

    def directory_total(self, files: list[str]):
        """
        Detection scheme based on the total file bytecount on every directory.

        Args:
            files (list): Files in the working directory.
        """
        return {
            self.path: round(
                utils.entropy(sum([utils.bytecount(f) for f in files], Counter())), 2
            )
        }

    def directory_average(self, files: list[str]):
        """
        Detection scheme based on the average file entropy on every directory.

        Args:
            files (list): Files in the working directory.
        """
        return {
            self.path: round(
                sum(utils.entropy(utils.bytecount(f)) for f in files) / len(files),
                2,
            )
        }


# Main Program

old, curr = {}, {}
CHANGE_THRESHOLD = 1.0
ENTROPY_THRESHOLD = 7.0

detector = DetectionScheme(path=args.workdir, mode=args.mode, rl=args.recursion_level)

try:
    while True:

        # Get current files in the directory
        files = utils.allfiles(
            path=os.path.abspath(args.workdir),
            recursion_level=args.recursion_level,
            ignored=[".git", "node_modules", ".vscode", "venv"],
        )

        curr = detector.scheme(files)

        for name, value in curr.items():
            ovalue = old.get(name)
            if not ovalue and value > ENTROPY_THRESHOLD:
                logging.warning(f"{utils.red(value)} bits per byte ({name})")
            elif not ovalue:
                logging.info(f"{utils.green(value)} bits per byte ({name})")
            elif abs(ovalue - value) > CHANGE_THRESHOLD:
                logging.warning(
                    f"{utils.red(value)} bits per byte from {utils.green(ovalue)} ({name}) "
                )
            elif value != ovalue and value > ENTROPY_THRESHOLD:
                logging.warning(f"{utils.red(value)} bits per byte ({name})")

        old = curr
        time.sleep(3)
except KeyboardInterrupt:
    print("\nInterrupted, exiting now...")
    print()
