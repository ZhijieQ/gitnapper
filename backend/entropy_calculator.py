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
    default=1,
    help="The level of recursion for searching subdirectories. Default is 1 (only the specified directory).",
)

args = parser.parse_args()


def file_entropy(filepath: str):
    """
    Computes the entropy value of a file, which ranges in 0 to 8 bits per byte.

    Args:
        filepath (str): File location

    Returns:
        float: Entropy value
    """
    with open(filepath, "rb") as f:
        data = f.read()

    entropy = 0
    for count in Counter(data).values():
        probability = count / len(data)
        entropy -= probability * math.log2(probability)

    return entropy


def get_files(path: str, recursion_level: int, ignored: list):
    """
    Get all the files in the specified directory, up to a certain
    recursion level.

    Args:
        path (str): Working directory.
        recursion_level (int): Maximum recursion depth.
        ignored (list): List of ignored directories or files.

    Returns:
        list: Files in the directory
    """
    files = []
    if recursion_level == 0:
        return files

    filenames = [f for f in os.listdir(path) if f not in ignored]

    for filename in filenames:
        filepath = f"{path}/{filename}"
        if os.path.isdir(filepath):
            files += get_files(filepath, recursion_level - 1, ignored)
        elif os.path.isfile(filepath):
            files.append(filepath)

    return files


try:
    while True:
        files = get_files(
            path=args.workdir,
            recursion_level=args.recursion_level,
            ignored=[".git", "node_modules", ".vscode"],
        )

        entropy = sum(file_entropy(file) / len(files) for file in files)
        logging.info(f"Entropy level: {entropy} bits per byte")
        time.sleep(3)

except KeyboardInterrupt:
    print()
    logging.info("Process interrupted. Exiting...")
