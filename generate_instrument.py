import os
import re
import json
from datetime import datetime
from jinja2 import Template
# import jinja2
# from flask import render_template


def clean_strings_for_php(input: str): 
    '''Clean double quotation marks from string for php
    NOTE: other string cleaning happens with escape character macro in jinja2 templates
    '''
    return re.sub('\n', '<br/>', re.sub('"', '\"', input))

def convert_instrument_template(instrument_information, **kwargs):   
    '''
    create_instrument_php:
        generates php file for instrument 
    Args:
        instrument_json (json): json string with instrument page/field data. Should follow the 
    kwargs:  
    '''
    
    field_type = {
        'text': ['varchar', 'int', 'char', 'tinyint', 'smallint', 'mediumint', 'bigint', 'decimal', 'dec','float', 'double', 'tinytext'], 
        'textarea': ['text', 'mediumtext', 'longtext'], 
        'select': ['enum'], 
        'date': ['date']}
    
    # convert to dictionary of instrument parameters 
    # instrument_information = json.load(instrument_json)
    
    # ============================================================================ #
    #                  parse parameters from instrument json file                  #
    # ============================================================================ #
    
    instrument_parameters = {}
    json_keys_instrument_parameters = ["instrument_name_sql", "instrument_name", "metadata_fields", "validity_enabled", "validity_required", "author"]
    pages_parameters = {}
    json_keys_pages_parameters = ["order", "title", "note_php"]
    field_parameters = {}
    json_keys_field_parameters = ["field_name_sql", "field_front_text_php", "field_type_sql", "enum_values_sql", "enum_values_php", "field_include_not_answered", "field_default_value", "associated_status_field", "page_php", "hidden_on_php", "group_php", "rule_php", "note_php"]
    group_parameters = {}
    json_keys_group_parameters = ["group_fields", "group_front_text_php", "type"]
    # TODO: add group validation 
    
    # instrument_warnings = {}
    
    # ------------------------ parse instrument parameters ----------------------- #
    # REQUIRED: must have a `instrument_name_sql` defined
    try: 
        if isinstance(instrument_information["instrument_name_sql"], str):
            instrument_parameters["sql_table_name"] = instrument_information["instrument_name_sql"] 
            if (len(instrument_information["instrument_name_sql"]) >= 64): 
                raise ValueError(f'String value for `instrument_name_sql` must be 64 characters or less.\nInput value is = {instrument_information["instrument_name_sql"]}, which is {len(instrument_information["instrument_name_sql"])} charaters long.\nPlease update with a valid SQL table name.')
            if (bool(re.search(r"\s", instrument_information["instrument_name_sql"]))): 
                raise ValueError(f'String value for `instrument_name_sql` cannot contain spaces.\nInput value is = {instrument_information["instrument_name_sql"]}.\nPlease update with a valid SQL table name.')
    except KeyError as err: 
        raise KeyError(f"[from create_instrument_php()] the input instrument json does not contain the key `instrument_name_sql` which is required. Update json file. ")
    
    # parse other instrument level parameters, besides `instrument_name_sql`
    for inst_param in json_keys_instrument_parameters[0:]: 
        if (inst_param in instrument_information.keys()): 
            instrument_parameters[inst_param] = instrument_information[inst_param]
    
    # as a default, if there is not a descriptive instrument name provided in `instrument_name` we automatically set that value to the table name. 
    if ("instrument_name" not in instrument_parameters.keys()): 
        instrument_parameters["instrument_name"] = instrument_parameters["sql_table_name"]
    else: 
        instrument_parameters["instrument_name"] = clean_strings_for_php(instrument_parameters["instrument_name"])
    
    # as a default, if `metadata_fields`, `validity_enabled`, `validity_required`, and `author` not provided set as False
    for inst_param in json_keys_instrument_parameters[1:]: 
        if (inst_param not in instrument_parameters.keys()): 
            instrument_parameters[inst_param] = False
    
    # automatically add instrument `date`. This will be populated in a comment at the top of the PHP file under @updated
    instrument_parameters["date"] = datetime.today().strftime('%Y-%m-%d')
    
    
    # -------------------------- parse page information -------------------------- #
    npages = 0 
    if ("pages" in instrument_information.keys()): 
        for pg in instrument_information["pages"].keys():
            # it is not required to define the Top Page, but if they do don't include it in the count
            tmp_page = {}
            
            if (pg in ["page0", "main"] or instrument_information["pages"][pg]["title"] == "Top Page"):  
                tmp_page_key = "page0"
            # otherwise we increment npages and pull the information
            else: 
                npages += 1
                tmp_page_key = f'page{npages}'
            
            for param in json_keys_pages_parameters: 
                if (param in instrument_information["pages"][pg].keys()): 
                    tmp_page[param] = instrument_information["pages"][pg][param] 
                else: 
                    tmp_page[param] = None
            tmp_page["page_number"] = npages
            tmp_page["page_name"] = tmp_page_key
            pages_parameters[tmp_page_key] = tmp_page
        
                        
    if ("page0" not in pages_parameters.keys()): 
        # save the default page
        pages_parameters["page0"] = {"order": 0, "title": "Top", "notes": None}
        
    # after looping through, add the number of pages to the page parameters    
    pages_parameters["npages"] = npages
    
    # ------------------------- parse group data, if any ------------------------- #
    ngroups = 0 
    if ("groups" in instrument_information.keys()):
        for g in instrument_information["groups"].keys(): 
            tmp_g = {}
            ngroups += 1
            for param in json_keys_group_parameters:
                # if we are on the group_fields, we grab all the keys from "fields" for easy access
                if param == "group_fields": 
                    # grab dict keys from instrument["fields"]
                    tmp_g["group_fields_keys"] = [
                        {
                            "key": key, 
                            "field": value["field_name_sql"],
                            "label": value.get("field_front_text_php", value["field_name_sql"]),
                            "type": [x for x in [k if (value["field_type_sql"] in v) else None for k,v in field_type.items()] if x is not None][0],
                            # TODO: add these parameters to template
                            # "attributes": None, 
                            "options": "array(" + ",".join([f'"{key1}" => "{key2}"' for key1, key2 in zip(value["enum_values_sql"], value.get("enum_values_php", value["enum_values_sql"])) ]) + ")" if value["field_type_sql"] == "enum" else False, 
                                # } 
                            # "customs": None 
                        }  for key, value in instrument_information["fields"].items() if value["field_name_sql"] in instrument_information["groups"][g]["group_fields"]] 
                    # grab php text for the keys
                    # tmp_g["group_fields_text"] = [value.get("field_front_text_php", value["field_name_sql"]) for key, value in instrument_information["fields"].items() if value["field_name_sql"] in instrument_information["groups"][g]["group_fields"]] 
                elif param in instrument_information["groups"][g].keys(): 
                    # add the parameter to the group dict entry
                    tmp_g[param] = instrument_information["groups"][g][param]
                else: 
                    tmp_g[param] = None
            
            # after looping through group parameters, save group name and data to dictionary. 
            tmp_g["group_name"] = g
            group_parameters[f"group_{ngroups}"] = tmp_g
    
    group_parameters["ngroups"] = ngroups
    
    # ----------------------------- parse field data ----------------------------- #
    if ("fields" in instrument_information.keys()): 
        # groups_added = []
        fields_warnings = {}
        # date_fields = []
        # if not isinstance(instrument_information["fields"], (dict)): 
        #         print(f'error with fields: {instrument_information["fields"]} and is type: {type(instrument_information["fields"])}')
        for q in instrument_information["fields"].keys(): 
            tmp_q = {}
            # if isinstance(json_keys_field_parameters, (bool)): 
            #     print(f'error with q: {instrument_information["fields"][q]["field_name_sql"]} and json_keys_field_parameters: {json_keys_field_parameters}')
            for param in json_keys_field_parameters: 
                # ["field_name_sql", "field_front_text_php", "field_type_sql", 
                # "enum_values_sql", "enum_values_php", "field_include_not_answered", 
                # "field_default_value", "associated_status_field", "page_php", 
                # "hidden_on_php", "group_php", "rule_php", "note_php"]
                # print(f'question {q} is type {type(instrument_information["fields"][q])}')
                if (param in instrument_information["fields"][q].keys()): 
                    # ------------------------------- format enums ------------------------------- #
                    if param == "enum_values_sql" and instrument_information["fields"][q]["field_type_sql"] == "enum":
                        # IF we do not have enum fields provided
                        if not bool(instrument_information["fields"][q]["enum_values_sql"]): 
                            fields_warnings[f'{q}'] = "Question listed as enum, but no enum_values_sql provided."
                        # or IF we have enum_values_sql and enum_values_php 
                        elif bool(instrument_information["fields"][q]["enum_values_sql"]) and bool(instrument_information["fields"][q].get("enum_values_php", [])): 
                        #    confirm that enum_values_php is the same length as enum_values_sql
                           if len(instrument_information["fields"][q].get("enum_values_php", [])) != len(instrument_information["fields"][q]["enum_values_sql"]): 
                               fields_warnings[f'{q}'] = "Length of enum_values_sql does not equal enum_values_php. Did not apply enum_values_php to template"
                               tmp_q["enum_array"] = "array(" + ",".join([f'"{key1}"' for key1 in instrument_information["fields"][q]["enum_values_sql"]]) + ")"
                           else: 
                               tmp_q["enum_array"] = "array(" + ",".join([f'"{key1}" => "{key2}"' for key1, key2 in zip(instrument_information["fields"][q]["enum_values_sql"], instrument_information["fields"][q]["enum_values_php"])]) + ")"
                        # otherwise we have enum_values_sql, and just save those values
                        else:
                            tmp_q["enum_array"] = "array(" + ",".join([f'"{key1}"' for key1 in instrument_information["fields"][q]["enum_values_sql"]]) + ")"
                    # if param == "enum_values_php": 
                    #     # if enum_values_php is not empty, and the list of enums does not match, raise error
                    #     if bool(instrument_information["fields"][q]["enum_values_php"]) and len(instrument_information["fields"][q].get("enum_values_sql", [])) != len(instrument_information["fields"][q]["enum_values_php"]): 
                    #         fields_warnings[f'{q}'] = "Length of enum_values_sql does not equal enum_values_php. Did not apply enum_values_php to template"
                    #         print(f"\tQuestion {q}: Length of enum_values_sql does not equal enum_values_php. Did not apply enum_values_php to template")
                    #         tmp_q["enum_array"] = "array(" + ",".join([f'"{key1}"' for key1 in instrument_information["fields"][q]["enum_values_sql"]]) + ")"
                    #     # OR, enum_values_php may just be an empty array or false
                    #     elif not bool(instrument_information["fields"][q]["enum_values_php"]):
                    #         print(f"\tQuestion {q}: DOES NOT have enum_values_php, so save just the enum_values_sql values")
                    #         tmp_q["enum_array"] = "array(" + ",".join([f'"{key1}"' for key1 in instrument_information["fields"][q]["enum_values_sql"]]) + ")"
                    #     # otherwise we zip the two list together for php
                    #     else: 
                    #         print(f"\tQuestion {q}: zip/map values from enum_values_sql and enum_values_php.")
                    #         tmp_q["enum_array"] = "array(" + ",".join([f'"{key1}" => "{key2}"' for key1, key2 in zip(instrument_information["fields"][q]["enum_values_sql"], instrument_information["fields"][q].get("enum_values_php", instrument_information["fields"][q]["enum_values_sql"])) ]) + ")" if instrument_information["fields"][q]["field_type_sql"] == "enum" else False
                    # elif (instrument_information["fields"][q]["field_type_sql"] == "enum") and (param == "enum_values_sql") and ("enum_array" not in tmp_q.keys()): 
                    #     tmp_q["enum_array"] = "array(" + ",".join([f'"{key1}"' for key1 in instrument_information["fields"][q]["enum_values_sql"]]) + ")"
                    # ----------------------------- format XIN Rules ----------------------------- #
                    if param == "rule_php" and bool(instrument_information["fields"][q]["rule_php"]):
                        # TODO: test this works, and add error IO handling
                        tmp_q["XINRegisterRule"] = {
                            "field_name": instrument_information["fields"][q]["field_name_sql"], 
                            "rule": instrument_information["fields"][q]["rule_php"]["rule"] if ("rule" in instrument_information["fields"][q]["rule_php"].keys()) else False, 
                            "required": instrument_information["fields"][q]["rule_php"]["required"] if ("required" in instrument_information["fields"][q]["rule_php"].keys()) else False, 
                            "message": instrument_information["fields"][q]["rule_php"]["message"] if ("message" in instrument_information["fields"][q]["rule_php"].keys()) else False,
                            "group": instrument_information["fields"][q]["rule_php"]["group"] if ("group" in instrument_information["fields"][q]["rule_php"].keys()) else False
                        }
                    
                    tmp_q[param] = instrument_information["fields"][q][param] 
                else: 
                    tmp_q[param] = None
                
                # then we save those parameters to the array 
                field_parameters[q] = tmp_q
            
    else: 
        raise OSError("Instrument Template file doesn't have any fields, or they are incorrectly labelled. Should be 'fields': \{\}")
    
    # field_parameters = instrument_information.get("fields", {})
    
    # ----------------------------- parse group data ----------------------------- #
    # group_parameters = instrument_information.get("groups", {})
    
    # ============================================================================ #
    #                          generate php from template                          #
    # ============================================================================ #
    
    
    
    template_parameters = {
        "instrument": instrument_parameters if bool(instrument_parameters) else None, 
        "pages": pages_parameters if bool(pages_parameters) else None,
        "fields": field_parameters if bool(field_parameters) else None, 
        "field_type": field_type,
        "groups": group_parameters if bool(group_parameters) else None 
        }
    
    return template_parameters


def generate_instrument_sql(instrument_data): 
    
    # ----------------------- INSERT into test_names table ----------------------- #
    with open("templates/LORIS_INSERT_test_names_template.sql.jinja2") as filein:  # noqa
        test_names_template = Template(filein.read(), trim_blocks=True, lstrip_blocks=True)
        # TODO: add support for instrument subgroup input
        
    with open("outputs/sql/test_names_INSERT_" + instrument_data["instrument"]["sql_table_name"] + ".sql", "w") as output: 
        output.write(test_names_template.render(instrument_data))
        
    # --------------------- INSERT into test_subgroups table --------------------- #
    # NOTE: this is typically not necessary. if we add a kwarg to this function, it could easily just append the script above
    # with open("LORIS_INSERT_test_subgroups_template.sql.jinja2") as filein:  # noqa
    #     test_names_template = Template(filein.read(), trim_blocks=True, lstrip_blocks=True)
        
    # with open("outputs/sql/test_subgroups_INSERT_" + instrument_data["instrument"]["sql_table_name"] + ".sql", "w") as output: 
    #     output.write(test_names_template.render(instrument_data))
    
    # --------------------- INSERT into test_subgroups table --------------------- #
    with open("templates/LORIS_INSERT_instrument_subtests_template.sql.jinja2") as filein:  # noqa
        instrument_subtest_template = Template(filein.read(), trim_blocks=True, lstrip_blocks=True)
        
    with open("outputs/sql/instrument_subtests_INSERT_" + instrument_data["instrument"]["sql_table_name"] + ".sql", "w") as output: 
        output.write(instrument_subtest_template.render(instrument_data))
    
    # ---------------------- INSERT into test_battery table ---------------------- #
    

def generate_instrument_from_template(instrument_json, output_dir):
    '''
    read_instrument_template: 

    kwargs:
    
    '''
    cwd = os.getcwd()
    # TODO: update this function to add folders if they don't exist in the current working directory. 
    
    # read instrument template
    inst = convert_instrument_template(instrument_json)
    # save input json file 
    with open(os.path.join(output_dir, "json", f"intrument_{inst['instrument']['sql_table_name']}.json"), "w+") as output: 
        output.write(json.dumps(instrument_json))
    
    # ============================================================================ #
    #                            generate SQL statements                           #
    # ============================================================================ #
    # generate_instrument_sql(inst)
    # -------------------------- CREATE instrument table ------------------------- #
    with open("templates/LORIS_CREATE_instrument_table_template.sql.jinja2") as filein:  # noqa
        create_table_template = Template(filein.read(), trim_blocks=True, lstrip_blocks=True)
        
    with open(os.path.join(output_dir, "sql", f"intrument_CREATE_{inst['instrument']['sql_table_name']}.sql"), "w+") as output: 
        output.write(create_table_template.render(inst))
    
    # ----------------------- INSERT into test_names table ----------------------- #
    with open("templates/LORIS_INSERT_test_names_template.sql.jinja2") as filein:  # noqa
        test_names_template = Template(filein.read(), trim_blocks=True, lstrip_blocks=True)
        # TODO: add support for instrument subgroup input
        
    with open(os.path.join(output_dir, "sql", "test_names_INSERT_" + inst["instrument"]["sql_table_name"] + ".sql"), "w+") as output: 
        output.write(test_names_template.render(inst))
    
    #  --------------------- INSERT into test_subgroups table --------------------- #
    with open("templates/LORIS_INSERT_instrument_subtests_template.sql.jinja2") as filein:  # noqa
        instrument_subtest_template = Template(filein.read(), trim_blocks=True, lstrip_blocks=True)
        
    with open(os.path.join(output_dir, "sql", "instrument_subtests_INSERT_" + inst["instrument"]["sql_table_name"] + ".sql"), "w+") as output: 
        output.write(instrument_subtest_template.render(inst))
    
    # ============================================================================ #
    #                            generate PHP instrument                           #
    # ============================================================================ #
    
    with open("templates/LORIS_instrument_builder_php_template.html.jinja2") as filein:
        loris_template = Template(filein.read(), trim_blocks=True, lstrip_blocks=True)
    
    # ------------------ compile instrument with jinja template ------------------ #
    with open(os.path.join(output_dir, "php", "NDB_BVL_Instrument_" + inst["instrument"]["sql_table_name"] + ".class.inc"), "w+") as output: 
        output.write(loris_template.render(inst))
        # output.write(inst_php)
    
    
# generate_instrument_from_template("E-Lab/adi_r_toddler_instrument_details.json")
# t1 = convert_instrument_template("E-Lab/adi_r_toddler_instrument_details.json")
# t1.keys()
# sorted(t1['pages'])
# t1["pages"]
# t1["groups"].keys()
# t1["groups"]["group_1"].keys()
# t1["groups"]["group_1"]["type"]
# t1["fields"]["field11"]
# t1["fields"]["field11"].keys()
# t1["fields"]["field26"].keys()
# t1["fields"]["field247"]