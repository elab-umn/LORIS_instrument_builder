import requests
import json
import configparser
import pandas as pd
import os

def get_metadata(redcap_config = os.path.join('config','redcap_config.ini'), db = 'redcap'):
    '''
    Gets REDCap metadata from the API. See get_data

    Returns
    ----------
    result: dictionary
        metadata from the REDCap API call
    '''

    # Read config file for database connections
    config = configparser.ConfigParser()
    try:
        with open(redcap_config) as f:
            config.read_file(f)
    except IOError:
        raise FileNotFoundError(
            "database config file ({dbconfig}) not found. Check script directory or path to {dbconfig}"
        )

    # check config information is available, and connect to the databse selected
    if config.has_section(db):
        token = config.get(db, "token")
        api_route = config.get(db, "api_route")

    else:
        # failsafe is config doesn't have expecated connection information
        raise RuntimeError("CONFIG ERROR -- Something went wrong. DB connection not found in {dbconfig} file.")    

    data = {
        'token': f'{token}',
        'content': 'metadata',
        'format': 'json',
        'returnFormat': 'json',
    }
    name = data['content']
    r = requests.post(api_route, data=data)
    result = r.json()
    print(f'Get {name} HTTP Status: ' + str(r.status_code), flush=True)

    return result

def metadata_to_dict(metadata):
    """
    transforms metadata from REDCap into a dictionary with a key for each form.
  
    Returns
    ----------
    sorted_metadata: dictionary
        a dictionary where the keys are instrument names and values are field and their metadata
    """
    include = generate_filtered_data_dict(metadata)

    filtered_metadata = [metadata for metadata in metadata if metadata["field_name"] in include]
    sorted_metadata = {metadata["form_name"]: {field["field_name"]: field for field in filtered_metadata if field["form_name"] == metadata["form_name"]} for metadata in filtered_metadata}

    # if verbose:
    #     with open(f'outputs/json/sortedMetadata.json', 'w+') as file:
    #         json.dump(sorted_metadata, file, indent=4)
    return sorted_metadata

def generate_filtered_data_dict(metadata):
    """
    Generates a dataframe that excludes data marked as identifying in REDCap

    Key Word Arguments
    ----------
    exclude: list of strings
        a list of instruments to exclude from the data transfer

    Returns
    ----------
    fields_to_include: list of strings
        a list of the fields that should be pulled from REDCap.
    """

    include = ["date_mdy", "datetime_mdy", "integer", "number", "time"]

    metadata_df = pd.read_json(json.dumps(metadata))

    metadata_df.drop(metadata_df.loc[metadata_df['field_type']=='descriptive'].index, inplace=True)
    metadata_df.drop(metadata_df.loc[metadata_df['field_type']=='notes'].index, inplace=True)
    metadata_df.drop(metadata_df.loc[metadata_df['identifier']=='y'].index, inplace=True)

    metadata_df.drop(metadata_df.loc[(metadata_df['field_type']=='text') & (~metadata_df['text_validation_type_or_show_slider_number'].isin(include))].index, inplace=True)

    # if verbose:
    #     metadata_df.to_csv("outputs/filtered_data_dictionary.csv", index=False)
    
    fields_to_include = metadata_df['field_name'].to_list()

    return fields_to_include

def field_type_lookup(question):
    """
    parses a single metadata field and maps the REDCap data type to a SQL datatype

    Arguments
    ----------
    question: dictionary
        a single field's metadata entry

    Returns
    ----------
    field_type: string
        a SQL data type
    """
    field_type = ''
    if (question['text_validation_type_or_show_slider_number'] == 'date_mdy'):
        field_type = 'date'
    elif (question['text_validation_type_or_show_slider_number'] == 'integer'):
        field_type = 'int'
    elif (question['text_validation_type_or_show_slider_number'] == 'number'):
        field_type = 'varchar(255)'
    else:
        field_type_lookup = {
            'radio': 'enum',
            'text': 'varchar(255)',
            'descriptive':'',
            'dropdown':'enum',
            'notes':'text',
            'calc':'int',
            'yesno':'enum',
            'checkbox':'varchar(255)'
            }
        field_type = field_type_lookup[question['field_type']]
    return field_type

def make_enum_array(question):
    """
    parses a single metadata field and if it would be an enum formats the REDCap choices

    Arguments
    ----------
    question: dictionary
        a single field's metadata entry

    Returns
    ----------
    options_sql: list of strings
        a list of enum values for sql
    options_php: list of strings
        a list of descriptions for the front end of LORIS
    """
    options = question['select_choices_or_calculations']
    field_type = question['field_type']

    if field_type_lookup(question) == 'enum':
        options_php = []
        options_sql = []
        if field_type == 'yesno':
            options_sql = [ '', '0', '1' ]
            options_php = [ '', 'No', 'Yes']
        else:
            options_sql = [option.split(',')[0].strip() for option in options.split('|')]
            options_sql.insert(0, "")
            options_php = [option.split(',')[1].strip() for option in options.split('|')]
            options_php.insert(0, "")

        return options_sql, options_php
    else:
        return '', ''

def metadata_to_instrument_json(metadata, form):
    """
    parses a single form's metadata and transforms it into the format accepted by the instrument builder.

    Arguments
    ----------
    metadata: dictionary
        a dictionary where the keys are instrument names and values are field and their metadata
    form: string
        the name of a REDCap form

    Returns
    ----------
    instrument_data: dictionary
        a dictionary that is accepted by the instrument builder
    """
    instrument = metadata[form]

    instrument_data = {
        "instrument_name": form,
        "instrument_name_sql": form,
        "pages": {},
        "fields": {
            f"field{index + 1}": { 
                "field_name_sql": field["field_name"],
                "field_front_text_php": field["field_label"],
                "field_type_sql": field_type_lookup(field),
                "enum_values_sql": make_enum_array(field)[0],
                "enum_values_php": make_enum_array(field)[1],
                "field_include_not_answered": False,
                "field_default_value": False,
                "associated_status_field": False,
                "page_php": 0,
                "hidden_on_php": False,
                "group_php": False,
                "rule_php": False,
                "note_php": False,
                "metadata_fields": False
            } for index, field in enumerate(instrument.values())
        },
        "groups": {}
        }
    
    # print(json.dumps(instrument_data, indent=4))
    return instrument_data

def all_metadata_to_instrument_jsons():
    """
    creates an instrument builder dictionary for all REDCap forms in sorted_metadata

    Returns
    ----------
    instruments: list of dictionaries
        a list of dictionaires accepted by the instrument builder
    """
    metadata = metadata_to_dict(get_metadata())

    instruments = [metadata_to_instrument_json(metadata, instrument) for instrument in metadata.keys()]
    # print(json.dumps(instruments, indent=4))
    return instruments
