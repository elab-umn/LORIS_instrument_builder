import os
import re
import json

    

def create_instrument_php(**kwargs):
    '''
    create_instrument_php:
        generates php file for instrument 
    kwargs: 
        form = name of instrument table
    
    '''
    form = kwargs.get("form")
    include_meta_fields = kwargs.get("include_meta_fields", True)
    field_type = {
        "text": [
            "varchar",
            "varchar(255)",
            "int",
            "char",
            "tinyint",
            "smallint",
            "mediumint",
            "bigint",
            "decimal",
            "dec",
            "float",
            "double",
            "tinytext",
        ],
        "textarea": ["text", "mediumtext", "longtext"],
        "select": "enum",
        "date": "date",
    }

    values = self.metadata[form]
    date_fields = [field for field in values if self.field_type_lookup(values[field]) == "date"]
    instrument_params = {
        "instrument_table_name": form,
        "validity_required": False,
        "validity_enabled": False,
        "include_meta_fields": include_meta_fields,
        "date_fields": date_fields,
        "loris_num_pages": 1,
        "instrument_name_text": form,
    }
    var_data_object = [
        {
            "page": 1,
            "var_type": self.field_type_lookup(values[value]),
            "status": "",
            "front_end": True,
            "name": value,
            "text": values[value]["field_label"].replace('"', "'"),
            "enum_array": self.make_enum_array(values[value]),
        }
        for i, value in enumerate(values)
    ]

    jinja_dict = {"param": instrument_params, "var_data": var_data_object, "field_type": field_type}

    with open("LORIS_php_instrument_template.html.jinja2") as filein:  # noqa
        loris_template = Template(filein.read(), trim_blocks=True, lstrip_blocks=True)

    with open(
        "outputs/php/NDB_BVL_Instrument_" + instrument_params["instrument_table_name"] + ".class.inc", "w"
    ) as fileout:
        fileout.write(loris_template.render(jinja_dict))


def generate_instrument_from_template(path):
    '''
    read_instrument_template: 

    kwargs:
    
    '''
    file = open(path)
    instrument = json.load(file)
    pages = instrument['pages']
    fields = instrument['fields']
    if "groups" in instrument.keys(): 
        groups = instrument['groups']
    
    create_instrument_php(
        form = instrument['instrument_name_loris'], 
        include_meta_fields = 
        )
    os.getcwd()