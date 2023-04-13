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
    expected_keys = ["instrument_name", "instrument_name_sql", "metadata_fields", "validity_enabled", "validity_required", "pages", "fields", "groups"]
    try:
        assert os.access(file, os.R_OK)
        path = os.path.abspath(file)

        with open(path) as json_file:
            json_dict = json.load(json_file)

        for key in expected_keys:
            if not key in json_dict:
                raise argparse.ArgumentTypeError(f"\nInvalid instrument JSON:\nmissing key: {key}")
            
        pages = [ json_dict["pages"][page]["order"] for page in json_dict["pages"] ]
        pages.append(0)

        for field in json_dict["fields"]:
            validate_field(field, json_dict["fields"][field], pages)

        return path
    except (AssertionError):
        raise argparse.ArgumentTypeError(f"\nCannot read file at {file}")
    
def validate_field(field_name, field_values, pages):
    # checks for requried keys
    required_keys = [
        "field_name_sql",
        "field_type_sql",
        "page_php"
    ]
    for key in required_keys:
        if not key in field_values:
            raise argparse.ArgumentTypeError(f"\nInvalid field '{field_name}' in instrument JSON:\nmissing key: '{key}'")

    # field must have a php front text if its not hidden
    if "hidden_on_php" in field_values:
        if not field_values["hidden_on_php"]:
            if "field_front_text_php" not in field_values:
                raise argparse.ArgumentTypeError(f"\nInvalid field '{field_name}' in instrument JSON:\nmissing key: 'field_front_text_php'")

    # if it's an enum field, it must list its values.
    if field_values["field_type_sql"] == "enum":
        if not "enum_values_sql" in field_values.keys():
            raise argparse.ArgumentTypeError(f"\nInvalid field '{field_name}' in instrument JSON\nmissing key 'enum_values_sql'")
        # Reuses sql values as php values if php values not defined. otherwise they must be the same length.
        if "enum_values_php" in field_values.keys():
            if len(field_values["enum_values_sql"]) != len(field_values["enum_values_php"]):
                raise argparse.ArgumentTypeError(f"\nInvalid Field '{field_name}' in instrument JSON:\n'enum_values_php' must be same length as 'enum_values_sql'")
            
    if field_values["page_php"] not in pages:
        raise argparse.ArgumentTypeError(f"\nInvalid field '{field_name}' in instrument JSON\ninvalid page number: {field_values['page_php']}")
