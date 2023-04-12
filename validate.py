import os
import argparse
import json

def directory(directory):
    if not os.path.isdir(directory):
        os.makedirs(directory)
    return directory

def data_source(source):
    valid_sources = ["redcap", "qualtrics"]
    if source in valid_sources:
        return source
    else:
        raise argparse.ArgumentTypeError("\n{} is not a valid datasource. Please choose from {}".format(source, valid_sources))
    
def instrument_json(file):
    expected_keys = ["instrument_name", "instrument_name_loris", "metadata_fields", "validity_enabled", "validity_required", "pages", "fields", "groups"]
    try:
        assert os.access(file, os.R_OK)
        path = os.path.abspath(file)

        with open(path) as json_file:
            json_dict = json.load(json_file)
            
        for key in expected_keys:
            if not key in json_dict:
                raise argparse.ArgumentTypeError(f"\nInvalid instrument JSON:\nmissing key: {key}")

        for field in json_dict["fields"]:
            validate_field(field, json_dict["fields"][field])

        return path
    except (AssertionError):
        raise argparse.ArgumentTypeError(f"\nCannot read file at {file}")
    
def validate_field(field_name, field_values):
    required_keys = [
        "field_name_loris",
        "field_front_text_php",
        "field_type_loris"
    ]

    # field_defaults = {
    #     "field_include_not_answered": False,
    #     "field_default_value": False,
    #     "associated_status_field": False,
    #     "page_php": 0,
    #     "hidden_on_php": False,
    #     "group_php": False,
    #     "rule_php": False,
    #     "note_php": False
    # }

    for key in required_keys:
        if not key in field_values:
            raise argparse.ArgumentTypeError(f"\nInvalid field '{field_name}' in instrument JSON:\nmissing key: {key}")

    # for field in field_defaults.keys():
    #     if field not in field_values:
    #         field_values[field] = field_defaults[field]

    if field_values["field_type_loris"] == "enum":
        if not "enum_values_loris" in field_values.keys():
            raise argparse.ArgumentTypeError(f"\nInvalid field '{field_name}' in instrument JSON\nmissing key 'enum_values_loris'")
        if not "enum_values_php" in field_values.keys():
            raise argparse.ArgumentTypeError(f"\nInvalid field '{field_name}' in instrument JSON:\nmissing key 'enum_values_php'")
        if len(field_values["enum_values_loris"]) != len(field_values["enum_values_php"]):
            raise argparse.ArgumentTypeError(f"\nInvalid Field '{field_name}' in instrument JSON:\n'enum_values_php' must be same length as 'enum_values_loris'")