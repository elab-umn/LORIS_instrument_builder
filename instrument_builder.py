#!/usr/bin/env python

import argparse
import os
import json

from validate import valid_readable_file, DataSource, Directory, valid_config_parameter
from generate_instrument import generate_instrument_from_template
from redcap import all_metadata_to_instrument_jsons
from qualtrics import get_metadata_from_survey

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
        if source == "qualtrics": 
            if ((args.project != None)): 
            #check they specified project, in which case assume survey information is stored in config files 
                token = valid_config_parameter("config/qualtrics_config.ini", args.project, "api-token")
                datacenter = valid_config_parameter("config/qualtrics_config.ini", args.project, "data-center")
                surveylabel = args.survey if (args.survey != None) else input("Which survey do you want to create? (should match label in 'config/qualtrics_survey_import_config.ini')")
                survey = valid_config_parameter("config/qualtrics_survey_import_config.ini", args.project, surveylabel)
            else: 
            #if not using config files check if they specified the specific survey as inputs, and if not prompt user for values.
                token = args.apitoken if (args.apitoken != None) else input("Enter Qualtrics API token: ")
                datacenter = args.datacenter if (args.datacenter != None) else input("Enter Qualtrics Datacenter: ")
                survey = args.survey if (args.survey != None) else input("Enter Qualtrics Survey ID: ")
                    
            instrument = get_metadata_from_survey(token, datacenter, survey)
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
    parser.add_argument(
        "--apitoken",
        type=str,
        default=None,
        help="String of API access token."
    )
    parser.add_argument(
        "--datacenter",
        type=str,
        default=None,
        help="String of datacenter for qualtrics account."
    )
    parser.add_argument(
        "--survey",
        type=str,
        default=None,
        help="String of survey to generate. If using config files, string should match the option label in the 'config/qualtrics_survey_import_config.ini' configuration file. If specifying a single survey, this should be the full survey ID."
    )
    parser.add_argument(
        "--project",
        type=str,
        default=None,
        help="String of project name. Should match the section in the 'config/redcap_config.ini' or 'config/qualtrics_config.ini' configuration file."
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()