# LORIS Instrument Builder

Python scripts to configure and build instruments in LORIS

This repository has a number of scripts and classes that are useful to automatically building instruments for LORIS. In general, it is essential to know which data will be stored in the SQL, which data will be displayed in the PHP instrument, and the mapping between the datatypes in SQL and PHP.

## Steps to build an instrument with the LORIS_instrument_builder
1. Compile information about surveys you wish to build. This may come in different formats:
    * (1) Manually create a `.json` file that outlines the fields in the SQL table, linking SQL fields to specific data types and external field names and specifying how data will appear in PHP. 
    * (2) Set of surveys collected in Redcap. <span style="color: red;">FIXME: ADD DETAILS ABOUT WHAT IS NEEDED FOR REDCAP</span>
    * (3) Set of surveys collected in Qualtrics. You will need your qualtrics API key, datacenter, and survey IDs. 
2. Run script for set of surveys to create. 
3. Verify output. Edit `.json` files if necessary, and rerun script on the modified `.json` files
4. Build tables and add necessary lines to SQL database. This can be run directly from the SQL scripts the script produces. 
5. Add PHP files to the LORIS instance via scp command
    * ```scp <instrument_file.php> lorisadmin@elab0.ahc.umn.edu:/var/www/loris/project/instruments/<instrument_file.php>```


## Running the script

From the LORIS_INSTRUMENT_BUILDER directory run `python3 instrument_builder.py`.<br>
NOTE: you must include either `--path` or `--source` flag.<br>
The most common uses are as follows: 

* generate from an instrument_template.json file: `python3 instrument_builder.py --path /path/to/instrument_template.json`<br>
* generate from qualtrics using a config file (recommended): `python3 instrument_builder.py --source qualtrics --project study1 --survey id_survey2`<br> 
* generate from qualtrics without config file: `python3 instrument_builder.py --source qualtrics --apitoken example0GsPO37HcxB1Vlaznc --datacenter ca1 --survey SV_exampleOvygXolCODKL`<br>
* generate from redcap: `python3 instrument_builder.py --source redcap`<br>

### Description of Flags

|flag |Required |Description |Example |
| ---------- | -------- | -------------- | ---------
| `--output_dir`, `-o`| _Optional_, default is "outputs/"| optional path to an output directory. Defaults to `outputs` creates the directory if it does not already exist.| |
|`--path`  | _Optional_ + _Required_ if generating instrument from json file.  |path to an instrument details JSON file |`python3 instrument_builder.py --path /path/to/instrument_template.json`
|`--source` | _Optional_ + _Required_ if generating instrument from external source (qualtrics or redcap), not in instrument template.  |database to pull metadata from. Creates an instrument for each instrument in the source. | `python3 instrument_builder.py --source qualtrics (other flags...)`
|`--apitoken` |_Optional_ |String of API access token. Should be specified when using `--datacenter` and `--survey` flags |`python3 instrument_builder.py --source qualtrics --apitoken 0GsPO37HcxB1Vlaznc --datacenter ca1 --survey SV_OvygXolCODKL`
|`--datacenter` |_Optional_ |String of datacenter for qualtrics account. Should be specified when using `--apitoken` and `--survey` flags |`python3 instrument_builder.py --source qualtrics --apitoken 0GsPO37HcxB1Vlaznc --datacenter ca1 --survey SV_OvygXolCODKL`
|`--survey` |_Optional_ |String of survey to generate. If using config files, string should match the option label in the 'config/qualtrics_survey_import_config.ini' configuration file. If specifying a single survey, this should be the full survey ID." |`python3 instrument_builder.py --source qualtrics --project gates --survey id_cshq`
|`--project` |_Optional_ |String of project name. Should match the section in the 'config/redcap_config.ini' or 'config/qualtrics_config.ini' configuration file. |`python3 instrument_builder.py --source qualtrics --project gates --survey id_cshq`

### Example Config Files

Example `config/qualtrics_config.ini` configuration file. This config file contains the projects and their associated api and datacenter information:
```
[pheSurvey1]
api-token = ExampleZuTwasQ2KGVrd5r7OhDCYGqg8eavAOBve39jasv
data-center = umn

[otherProject]
api-token = ...
data-center = ...

...
```

Example `config/qualtrics_survey_import_config.ini` configuration file. This config file contains the projects and their associated surveys:
```
[pheSurvey1]
id_demographics_eligibility = SV_6AwXVDIONRav1
id_vrRSB = SV_6AwXVDIONRav2
id_apsi = SV_6AwXVDIONRav3
id_mcdi = SV_6AwXVDIONRav4
id_mchat_RF = SV_6AwXVDIONRav5
id_rbs_ecs = SV_6AwXVDIONRav6
id_pheno2_concern = SV_6AwXVDIONRav7

[otherProject]
id_survey1 = SV_...
id_survey2 = SV_...

...
```


## Script example outputs

Outputs will be saved by default in `outputs/` and separated into `json`, `php`, and `sql` folders.<br>
* The `json` folder includes the input file/template file used to create all of the outputs. This file can be shared to generate files and tables needed to build an instrument in loris. This is where template files should be edited when updating the outputs generated from the instrument builder.<br>
* The `php` folder generated the php instrument files used for the front end of LORIS. This will specify how the data in the database is presented and can be manipulated from the front-end user.<br>
* The `sql` folder contains typically three sql scripts to build the instrument: _instrument_CREATE_, which builds the instrument table, _test_names_INSERT_, which adds the instrument to the `test_names` table, and _instrument_subtests_INSERT_, which adds the subtests or pages to the `instrument_subtests` table. 

## Formatting an instrument_template.json file

This is a basic json file that contains all of the information to generate an instrument in LORIS. 

### There are 6 main keys that are required: 

1. `instrument_name_sql`: The name of the SQL table. Best practice dictates that tables should follow the https://github.com/aces/Loris/blob/main/docs/SQLModelingStandard.md[LORIS conventions] for naming SQL tables in snake_case, which means they should be all lowercase with words separated by underscores (i.e. instrument_name, _not_ InstrumentName). 
2. `metadata_fields`: {} (empty dictionary)
3. `validity_enabled`: true
4. `validity_required`: false
5. `fields`: Dictionary containing the information for each individual field
6. `groups`: [] (usually an empty list)
<br>

### `fields` key details
The `fields` key in the json instrument template will have a dictionary as its value, containing the following keys:
* `field_name_sql`: The name of the field as it appears in the backend. We need this so we know where to put the data once it’s been processed
    * type: string
* `field_front_text_php`: The question “prompt” that users see on the front end
    * type: string
* `field_name_external`: The ID of the question in Qualtrics/Redcap. We need this so we can reference the correct question when processing the data
    * type: string
* `field_type_sql`: The type of the field in the backend (enum, varchar, int, date, etc.)
    * type: string
* `enum_values_sql`: The list of enum options as they appear in the backend.
    * type: list of strings | false
    * List elements should be in string form, even if the element is a number (e.g. 1 should be “1”)
    * Only present if field_type_sql is ‘enum’, otherwise ‘false’
* `enum_values_php`: The list of enum options as they appear to the user on the front end
    * type: list of strings | false
    * List elements should be in string form
    * Only present if field_type_sql is ‘enum’, otherwise ‘false’
* `field_include_not_answered`: Indicates if the enum options should include a ‘not_answered’ option
    * type: boolean
    * This will almost always be ‘true’ for enum fields – we want to be able to differentiate between data that was simply not answered, versus missing data (null)
    * Will only come into play when field_type_sql is ‘enum’
* `associated_status_field`: Indicates that a ‘not_answered’ option should be associated with a text response field to indicate whether or not it’s missing data or simply not answered
    * type: boolean
    * Should be ‘true’ for most text fields, but use best judgement. Should be ‘true’ for ALL required text fields
    * Will only come into play when field_type_sql is a form of string (varchar, text, mediumtext, etc.)
* `page_php`: Indicates what page the field will be presented on in the front end
    * type: int
* `hidden_on_sql`: ‘True’ if the field isn’t in the backend, ‘false’ otherwise
    * type: boolean
    * Will almost always be ‘false’
    * Kind of an unnecessary key, as the field probably shouldn’t be included in the template if it’s not in the backend, but sometimes it's helpful to have it in there
* `process_fx_external_to_sql`: Defines what process function to run for the field
    * type: dict | false
    * Whatever the process function, it should be defined in the processFunction.py zookeeper script
    * Probably the most complicated key:value pair in the template. It is highly customizable
* `enum_values_external`: The list of enum options as they appear in the external source (Qualtrics/Redcap) output data
    * type: list of strings | false
    * Generally numbered 1 through X
    * List elements should be in string form (e.g. 1 should be “1”)
    * Only present if field_type_sql is ‘enum’, otherwise ‘false’