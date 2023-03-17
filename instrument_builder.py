#!/usr/bin/env python

import argparse
import os
import json

from validate import valid_readable_file, DataSource, Directory
from generate_instrument import generate_instrument_from_template
from redcap import all_metadata_to_instrument_jsons

def main():
    args = parse_args()
    path = args.path
    source = args.source.__str__()

    # Make output directories
    output_dir = args.output_dir.directory
    if not os.path.exists(os.path.join(output_dir, "php")):
        os.makedirs(os.path.join(output_dir, "php"))
    if not os.path.exists(os.path.join(output_dir, "sql")):
        os.makedirs(os.path.join(output_dir, "sql"))

    # Generate instrument(s)
    if path:
        print(f"Generating instrument from file: {path}")
        with open(path) as json_file: 
            instrument_json = json.load(json_file)
        generate_instrument_from_template(instrument_json, output_dir)
    elif source:
        print(f"Generating instruments from '{source}'")
        if source == "redcap":
            instruments = all_metadata_to_instrument_jsons()
            for instrument in instruments:
                generate_instrument_from_template(instrument, output_dir)
    else:
        print(f"No inputs defined. Please include --path or --source")

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