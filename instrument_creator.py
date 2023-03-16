#!/usr/bin/env python

import argparse
import os

from validate import valid_readable_file, DataSource, Directory
from generate_instrument import generate_instrument_from_template

def main():
    args = parse_args()
    print("output_dir: ", args.output_dir)
    print("path: ", args.path)
    print("source: ", args.source)
    output_dir = args.output_dir.directory
    if not os.path.exists(os.path.join(output_dir, "php")):
        os.makedirs(os.path.join(output_dir, "php"))
    if not os.path.exists(os.path.join(output_dir, "sql")):
        os.makedirs(os.path.join(output_dir, "sql"))

    generate_instrument_from_template(args.path, output_dir)

def parse_args():
    parser = argparse.ArgumentParser("instrument_creator")

    parser.add_argument(
        "-o", "--output_dir",
        dest="output_dir",
        default="outputs",
        type=Directory,
        help="Valid file path to output directory."
    )
    parser.add_argument(
        "--path",
        type=valid_readable_file,
        help=("Valid path to instrument details json file. "
              "See EXAMPLE_instrument_details.json")
    )
    parser.add_argument(
        "--source",
        type=DataSource,
        help="A supported data source."
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()