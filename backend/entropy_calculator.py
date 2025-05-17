"""
Watcher process for ransomware detection based on the bit-per-byte entropy
value. All detection schemes assume the attack will not delete original files,
only override them.
"""

import math
import argparse
import os
import time
import logging
import sys
from collections import Counter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname).4s] - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
BOLD = "\033[1m"
END = "\033[0m"
GREEN = "\033[32m"
RED = "\033[31m"
parser = argparse.ArgumentParser(
    prog="Entropy Detection Daemon",
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
    help="The level of recursion for searching subdirectories. Default is 1 (only the specified directory).",
)
parser.add_argument(
    "-m",
    "--mode",
    type=int,
    default=1,
    help="Working mode, which can be one of the following: 1. Individual 2. Subdirectory Total 3. Subdirectory Average 4. Directory Total 5. Directory Average",
)

args = parser.parse_args()


class Files:
    """
    File information dataclass.
    """

    @staticmethod
    def entropy(bytecount: Counter):
        """
        Computes the entropy value of a byte count, which ranges in 0 to 8 bits per byte.

        Args:
            bytecount (str): Frequency of each byte value.

        Returns:
            float: Entropy value.
        """
        value = 0
        size = sum(bytecount.values())

        for count in bytecount.values():
            p = count / size
            value -= p * math.log2(p)

        return value

    @staticmethod
    def bytecount(path: str):
        """
        Returns the bytecount of a file.

        Args:
            path (str): File location

        Returns:
            float: Byte frecuency.
        """
        with open(path, "rb") as f:
            return Counter(f.read())

    @staticmethod
    def allfiles(path: str, recursion_level: int, ignored: list):
        """
        Obtains all file paths derived from PATH.

        Args:
            path (str): Working directory path.
            recursion_level (int): Maximum recursion depth.
            ignored (list): List of ignored directories or files.

        Returns:
            list: Files in the directory.
        """
        fnames = [f for f in os.listdir(path) if f not in ignored]
        files = []
        if recursion_level < 0:
            return files

        for fname in fnames:
            fpath = f"{path}/{fname}"
            if os.path.isdir(fpath):
                files += Files.allfiles(fpath, recursion_level - 1, ignored)
            elif os.path.isfile(fpath):
                files.append(fpath)

        return files

    @staticmethod
    def group_by_dir(files: list):
        """
        Groups all files in a list according to their parent directory.
        """
        directories = {os.path.dirname(file): [] for file in files}

        for file in files:
            directories[os.path.dirname(file)].append(file)

        return directories


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
        return {f: round(Files.entropy(Files.bytecount(f)), 2) for f in files}

    def subdirectory_total(self, files: list[str]):
        """
        Detection scheme based on the total file bytecount on every directory.

        Args:
            files (list): Files in the working directory.
        """
        dirs = Files.group_by_dir(files)
        curr = {}

        for subdir, filenames in dirs.items():
            curr[subdir] = round(
                Files.entropy(sum([Files.bytecount(f) for f in filenames], Counter())),
                2,
            )

        return curr

    def subdirectory_average(self, files: list[str]):
        """
        Detection scheme based on the average file entropy on every directory.

        Args:
            files (list): Files in the working directory.
        """
        dirs = Files.group_by_dir(files)
        curr = {}

        for subdir, filenames in dirs.items():
            curr[subdir] = round(
                sum(Files.entropy(Files.bytecount(f)) for f in filenames)
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
                Files.entropy(sum([Files.bytecount(f) for f in files], Counter())), 2
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
                sum(Files.entropy(Files.bytecount(f)) for f in files) / len(files),
                2,
            )
        }


def red(text: str):
    """Prints a bolded red version of TEXT"""
    return f"{BOLD}{RED}{text}{END}{END}"


def green(text: str):
    """Prints a bolded green version of TEXT"""
    return f"{BOLD}{GREEN}{text}{END}{END}"


old, curr = {}, {}
CHANGE_THRESHOLD = 1.0
ENTROPY_THRESHOLD = 7.0

detector = DetectionScheme(path=args.workdir, mode=args.mode, rl=args.recursion_level)

try:
    while True:

        # Get current files in the directory
        files = Files.allfiles(
            path=os.path.abspath(args.workdir),
            recursion_level=args.recursion_level,
            ignored=[".git", "node_modules", ".vscode", "venv"],
        )

        curr = detector.scheme(files)

        for name, value in curr.items():
            ovalue = old.get(name)
            if not ovalue and value > ENTROPY_THRESHOLD:
                logging.warning(f"{red(value)} bits per byte ({name})")
            elif not ovalue:
                logging.info(f"{green(value)} bits per byte ({name})")
            elif abs(ovalue - value) > CHANGE_THRESHOLD:
                logging.warning(
                    f"{red(value)} bits per byte from {green(ovalue)} ({name}) "
                )
            elif value != ovalue and value > ENTROPY_THRESHOLD:
                logging.warning(f"{red(value)} bits per byte ({name})")

        old = curr
        time.sleep(3)
except KeyboardInterrupt:
    print("\nInterrupted, exiting now...")
    print()
