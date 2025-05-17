import math
import argparse
import os
import time
import logging
import sys
from collections import Counter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)

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
    type=str,
    default="average",
    help="Working mode.",
)

args = parser.parse_args()


class Files:
    @staticmethod
    def entropy(bytecount: Counter):
        """
        Computes the entropy value of a byte count, which ranges in 0 to 8 bits per byte.

        Args:
            bytecount (str): Frequency of each byte value.

        Returns:
            float: Entropy value
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
        Returns the bytecount of a file

        Args:
            path (str): File location

        Returns:
            float: Entropy value
        """
        with open(path, "rb") as f:
            return Counter(f.read())

    @staticmethod
    def allfiles(path: str, recursion_level: int, ignored: list):
        """
        Recursively computes the average entropy value (sum of file entropies)
        for the current directory.

        Args:
            path (str): Working directory path.
            recursion_level (int): Maximum recursion depth.
            ignored (list): List of ignored directories or files.

        Returns:
            list: Files in the directory
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


"""
- ficheros individuales
- directorio (recursivo)
- subdirectorio (sin recursion)
"""


def individual(path: str, recursion_level: int, ignored: list):
    old = {}
    curr = {}
    try:
        while True:
            files = Files.allfiles(
                path=path,
                recursion_level=recursion_level,
                ignored=ignored,
            )
            curr = {f: round(Files.entropy(Files.bytecount(f)), 2) for f in files}
            
            for name, entropy in curr.items():
                oentropy = old.get(name)
                if not oentropy:
                    logging.info(f"[NEW]\t{name}: {entropy} bits per byte")
                elif abs(oentropy - entropy) > 1.0:
                    logging.warn(f"\t{name}: entropy changed from {oentropy} to {entropy}")
                elif entropy > 7.0:
                    logging.warn(f"\t{name}: high entropy level")
                

                pass
            time.sleep(3)
    except KeyboardInterrupt:
        print()
        logging.info("Process interrupted. Exiting...")

def directory():
    pass


def subdirectory():
    pass


def file_entropy(path: str):
    """
    Computes the entropy value of a file.

    Args:
        path (str): File location

    Returns:
        float: Entropy value
    """
    with open(path, "rb") as f:
        data = f.read()

    return entropy_value(Counter(data))


def average_entropy(name: str, path: str, recursion_level: int, ignored: list):
    """
    Recursively computes the average entropy value (sum of file entropies)
    for the current directory.

    Args:
        name (str): Working directory.
        path (str): Working directory path.
        recursion_level (int): Maximum recursion depth.
        ignored (list): List of ignored directories or files.

    Returns:
        list: Files in the directory
    """
    entropy, files = {name: 0}, 0

    fnames = [f for f in os.listdir(path) if f not in ignored]

    if recursion_level < 0:
        return {}

    for fname in fnames:
        fpath = f"{path}/{fname}"

        if os.path.isdir(fpath):
            entropy.update(
                average_entropy(f"{name}->{fname}", fpath, recursion_level - 1, ignored)
            )
        elif os.path.isfile(fpath):
            entropy[name] += file_entropy(fpath)
            files += 1

    entropy[name] = entropy[name] / files if files else entropy[name]

    return entropy


def total_entropy(name: str, path: str, recursion_level: int, ignored: list):
    """
    Recursively computes the average entropy value (sum of total byte
    entropies)  for the current directory.

    Args:
        name (str): Working directory.
        path (str): Working directory path.
        recursion_level (int): Maximum recursion depth.
        ignored (list): List of ignored directories or files.

    Returns:
        list: Files in the directory
    """
    entropy, files = {name: 0}, 0
    data = Counter()

    fnames = [f for f in os.listdir(path) if f not in ignored]

    if recursion_level < 0:
        return {}

    for fname in fnames:
        fpath = f"{path}/{fname}"

        if os.path.isdir(fpath):
            entropy.update(
                total_entropy(f"{name}->{fname}", fpath, recursion_level - 1, ignored)
            )
        elif os.path.isfile(fpath):
            with open(fpath, "rb") as f:
                data += Counter(f.read())

    entropy[name] = entropy_value(data)

    return entropy


individual(args.workdir, args.recursion_level, [".git", "node_modules", ".vscode"])

# try:
#     while True:
#         files = average_entropy(
#             name="root",
#             path=args.workdir,
#             recursion_level=args.recursion_level,
#             ignored=[".git", "node_modules", ".vscode"],
#         )

#         logging.info(f"Entropy level: {files}")
#         time.sleep(3)

# except KeyboardInterrupt:
#     print()
#     logging.info("Process interrupted. Exiting...")
