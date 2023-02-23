import mysql.connector
import datetime
import requests
import json
import traceback
import functools
from jinja2 import Template
from config import config, token, api_route
from random import randint

class RedcapToLoris:
    """
    Class that pulls data from the REDCap API and places it in the LORIS MySQL databse.

    Attributes
    ----------
    verbose: boolean
        whether to output a high number of print statments
    cnx: mysql connector connection object
        set by init using information from config.py
    cursor: mysql connector cursor object
        set by init, always a non-buffered cursor that returns a dictionary. See MySQL connector's documentation for more information.
    error_log: string
        path to the error log. Set by init
    api_route: string
        set by init using information from config.py
    reports: dictionary
        initialized by init. Populated by get_report
    records: list of dictionaries
        the data for all records in REDCap. Set by get_records
    metadata: list of dictionaries
        the REDCap instance's metadata. Set by get_metadata
    form_event_mapping: list of dictionaries
        the REDCap instance's mappings between forms and events. Set by get_form_event_mapping
    repeating_forms_events: list of dictionaries
        the REDCap instance's description of repeat instruments and the events they belong to
    cand_ids: list of strings
        list of all CandIDs from LORIS's MySQL database. Used to check if a candidate exists in LORIS
    pscids: list of strings
        list of all PSCIDs from LORIS's MySQL database. Used to check if a candidate exsists in LORIS
    """

    ## setup database connection, basic operations
    def __init__(self, **kwargs):
        self.verbose = kwargs.get("verbose")

        self.cnx = mysql.connector.connect(**config)
        self.cursor = self.cnx.cursor(dictionary=True)
        self.error_log = "outputs/redcap_to_loris_errors.txt"
        self.token = token
        self.api_route = api_route
        self.reports = {}


    def __del__(self):
        """ 
        Upon deleting the RedcapToLoris instance close the connection and the cursor.
        """
        self.cnx.close()
        self.cursor.close()

    def commit(self):
        """ 
        Commit changes to the database 
        """
        self.cnx.commit()

    def insert(self, table, dict):
        """
        Insert a row into 'table'.

        Parameters
        ----------
        table: string
            the name of the table to insert into
        dict: dictionary
            the data to insert. Dictionary keys are the SQL column names and dictionary values are the SQL values.
        
        Returns
        --------
        None
        """
        placeholder = ", ".join(["%s"] * len(dict))
        stmt = "INSERT INTO `{table}` ({columns}) VALUES ({values});".format(table=table, columns=",".join(dict.keys()), values=placeholder)
        self.cursor.execute(stmt, list(dict.values()))

    def query(self, **kwargs):
        """
        Queries a table in the database.

        Key Word Agruments
        ----------
        table: string
            REQUIRED
            the name of the table to query
        fields: list of strings
            REQUIRED
            the fields to query for
        where: dictionary
            OPTIONAL
            the where clause for the query. Dictionary keys are the SQL columns and dictionary values are the SQL values to match.
        where_like: dictionary
            OPTIONAL
            the where clause for the query for fields that use the LIKE key word. Dictionary keys are the SQL columns and dictionary values are the SQL values to match.

        Returns
        --------
        list 
            each row returned by the query is an item in the list.
        """
        table = kwargs.get("table")
        fields = kwargs.get("fields")
        where = kwargs.get("where")
        where_like = kwargs.get("where_like")

        columns = ', '.join(fields)

        query = f"SELECT {columns} FROM {table}"

        if where:
            wheres = ' AND '.join(f'{key} = "{value}"' for key, value in where.items())
   
        if where_like:
            where_likes = ' AND '.join(f'{key} LIKE "{value}"' for key, value in where_like.items())

        if where and where_like:
            query += " WHERE " + wheres + " AND " + where_likes
        elif where:
            query += " WHERE " + wheres
        elif where_like:
            query += " WHERE " + where_likes

        self.cursor.execute(query)
        return [row for row in self.cursor]

    def update(self, **kwargs):
        """
        Updates rows in the database.

        Key Word Arguments
        ----------
        table: string
            REQUIRED
            the name of the table to update
        fields: dictionary
            REQUIRED
            the fields to update, dictionary keys are SQL columns and dictionary values are SQL values
        where: dictionary
            REQUIRED
            the where clause for the SQL update. Dictionary keys are SQL columns and dictionary values are SQL values to match.

        Returns
        ----------
        None
        """
        table = kwargs.get("table")
        fields = kwargs.get("fields")
        where = kwargs.get("where")

        sql = 'UPDATE {table} SET {values} WHERE {where}'.format(table=table, values=', '.join('{}=%s'.format(key) for key in fields), where=' AND '.join(f'{key} = "{value}"' for key, value in where.items()))
        self.cursor.execute(sql, list(fields.values()))


    def log_error(self, **kwargs):
        """
        General purpose error logging.
        Creates an entry in the error log with information about the error.
        Prints to stdout if class instance is set to verbose.

        Key Word Arguments
        ----------
        method: string
            the method where the error arrose
        details: string
            further details on the error
            recommended to use an identifier that distinguishes this from other iterations of a loop such as candidate id etc.

        Returns
        ----------
        None
        """
        method = kwargs.get("method")
        details = kwargs.get("details")

        if self.verbose:
            print(f"Error executing {method}: {details}", flush=True)
        with open(self.error_log, "a") as file:
            file.write(f"--------------------------\n{datetime.datetime.now()} | Error in {method}: {details}\n{traceback.format_exc()}\n")

    ## api calls

    def get_data(self, data):
        """
        General api call function.
        Generates a json file of the returned data if set to verbose.

        Parameters
        ----------
        data: dictionary
            the dictionary used in the API get. See API documentation available when logged into a REDCap instance for examples.
        
        Returns
        ----------
        result: type determined by returnFormat in the data parameter
        """
        name = data['content']
        r = requests.post(self.api_route,data=data)
        result = r.json()
        print(f'Get {name} HTTP Status: ' + str(r.status_code), flush=True)

        if self.verbose:
            with open(f'outputs/json/{name}.json', 'w+') as file:
                json.dump(result, file, indent=4)

        return result

    def get_records(self):
        '''
        Gets all records from the REDCap API. See get_data
        Sets self.records to the returned value of get_data
        '''
        data = {
            'token': self.token,
            'content': 'record',
            'action': 'export',
            'format': 'json',
            'type': 'flat',
            'csvDelimiter': '',
            'rawOrLabel': 'raw',
            'rawOrLabelHeaders': 'raw',
            'exportCheckboxLabel': 'false',
            'exportSurveyFields': 'false',
            'exportDataAccessGroups': 'false',
            'returnFormat': 'json'
        }
        self.records = self.get_data(data)

    
    def get_metadata(self):
        '''
        Gets REDCap metadata from the API. See get_data
        Sets self.metadata to the returned value of get_data
        '''
        data = {
            'token': f'{self.token}',
            'content': 'metadata',
            'format': 'json',
            'returnFormat': 'json',
        }
        self.metadata = self.get_data(data)

    def get_form_event_mapping(self):
        '''
        Gets form event mappings from the REDCap API. See get_data
        Sets self.form_event_mapping to the returned value of get_data
        '''
        data = {
            'token': self.token,
            'content': 'formEventMapping',
            'format': 'json',
            'returnFormat': 'json'
        }
        self.form_event_mapping = self.get_data(data)

    def get_report(self, report_id):
        '''
        Gets a report from the REDCap API. See get_data
        Reports are constructed in the REDCap instance. Data returned will vary depending on what report is created.
        Adds a key-values pair to self.reports where key is the report id and value is the data returned by get_data
        Parameters
        ----------
        report_id: int
            the id of the report to get from the API
        '''
        data = {
            'token': self.token,
            'content': 'report',
            'format': 'json',
            'report_id': report_id,
            'csvDelimiter': '',
            'rawOrLabel': 'raw',
            'rawOrLabelHeaders': 'raw',
            'exportCheckboxLabel': 'false',
            'returnFormat': 'json'
        }
        self.reports[report_id] = self.get_data(data)

    def get_repeating_forms_events(self):
        '''
        Gets a the repeating forms metadata from the REDCap API
        Sets self.repeating_forms_events to the returned value of get_data
        '''
        data = {
            'token': self.token,
            'content': 'repeatingFormsEvents',
            'format': 'json',
            'returnFormat': 'json'
        }
        self.repeating_forms_events = self.get_data(data)

    ## Creating Candidates

    def get_existing_candidates(self):
        '''
        Queries the LORIS database for all existing candidates' PSCIDs and CandIDs
        Sets self.cand_ids equal to a list of CandIDs
        Sets self.pscids equal to a list of PSCIDs
        '''
        candidates = self.query(table='candidate', fields=['PSCID', 'CandID'])
        self.cand_ids = [candidate["CandID"] for candidate in candidates]
        self.pscids = [candidate["PSCID"] for candidate in candidates]

    def generate_offset(self):
        '''
        Generates a random number in a specific range.

        Returns
        ----------
        offset: int
            Random integer in [-30, -10) or (10, 30]
        '''
        offset = 0
        while offset <= 10 and offset >= -10:
            offset = randint(-30,30)
        return offset

    def jitter_dob(self, dob):
        '''
        Obscures dates.

        Parameters
        ----------
        dob: string
            datetime string in format YYYY-MM-DD
        
        Returns
        ----------
        datetime string
            an obscured date offset by the amount of time determined in generate_offset
        '''
        offset = datetime.timedelta(days = self.generate_offset())
        date = datetime.datetime.strptime(dob, '%Y-%m-%d')
        jittered_dob = date + offset
        return jittered_dob.strftime('%Y-%m-%d')

    def generate_cand_id(self):
        '''
        Randomly generates a CandID for use in LORIS's MySQL database.
        CandID will be unique across the LORIS instance

        Returns
        ----------
        cand_id: int
            a 6 digit integer
        '''
        while True:
            cand_id = randint(100000, 999999)
            if cand_id not in self.cand_ids:
                break
            self.cand_ids.append(cand_id)
        return cand_id

    def get_cand_info(self, **kwargs):
        """
        Constructs a dictionary with the values required to create an entry in the candidate table

        Key Word Arguments
        ----------
        record: dictionary
            a single record from self.records
        dob_field: string
            the label of the field to be used to find the candidat's DoB in the record
        sex_field: string
            the label of the field to be used to find the candidate's sex in the record
        registration_center_field: string
            the label of the field to be used to find the candidat's study center
        registration_date_field: string
            the label of the field to be used to find the candidate's date of registration
        registration_project_id: int
            the registration project id in LORIS
        registration_center_lookup: dictionary
            dictionary keys are the integer id for the study center in REDCap, dictionary values are the integer id for the study center in LORIS

        Returns
        ----------
        candidate_info: dictionary
            a dictionary with the values required to insert an entry in the candidate table
        """
        record = kwargs.get("record")
        dob_field = kwargs.get("dob_field")
        sex_field = kwargs.get("sex_field")
        registration_center_field = kwargs.get("registration_center_field")
        registration_date_field = kwargs.get("registration_date_field")
        registration_project_id = kwargs.get("registration_project_id")
        registration_center_lookup = kwargs.get("registration_center_lookup")
        sex_lookup = {
            '1': 'Male',
            '2': 'Female',
            '': 'Other'
        }
        candidate_info = {
            "CandID": self.generate_cand_id(),
            "PSCID": record['record_id'],
            "DoB": self.jitter_dob(record[dob_field]),
            "Sex": sex_lookup[record[sex_field]],
            "RegistrationCenterID": registration_center_lookup[record[registration_center_field]],
            "RegistrationProjectID": registration_project_id,
            "Active": 'Y',
            "Date_active": record[registration_date_field],
            "RegisteredBy": 'redcapTransfer',
            "UserID": 'redcapTransfer',
            "Date_registered": record[registration_date_field],
            "flagged_caveatemptor": 'false',
            "Testdate": record[registration_date_field],
            "Entity_type": 'Human'
        }
        return candidate_info

    def populate_candidate_table(self, **kwargs):
        """
        Inserts new candidates into the candidate table in LORIS's MySQL database.

        Key Word Arguments
        ----------
        dob_field: string
            the label of the field to be used to find the candidat's DoB in the record
        sex_field: string
            the label of the field to be used to find the candidate's sex in the record
        registration_center_field: string
            the label of the field to be used to find the candidat's study center
        registration_date_field: string
            the label of the field to be used to find the candidate's date of registration
        registration_project_id: int
            the registration project id in LORIS
        registration_center_lookup: dictionary
            dictionary keys are the integer id for the study center in REDCap, dictionary values are the integer id for the study center in LORIS

        Returns
        ----------
        None
        """
        dob_field = kwargs.get("dob_field")
        sex_field = kwargs.get("sex_field")
        registration_center_field = kwargs.get("registration_center_field")
        registration_date_field = kwargs.get("registration_date_field")
        registration_project_id = kwargs.get("registration_project_id", 1)
        registration_center_lookup = kwargs.get("registration_center_lookup")

        self.get_existing_candidates()
        num_old = len(self.cand_ids)
        num_added = 0
        num_error = 0
        for record in self.records:
            if record["record_id"] not in self.pscids and record[registration_date_field]:
                try:
                    candidate_info = self.get_cand_info(
                        record = record,
                        dob_field = dob_field,
                        sex_field = sex_field,
                        registration_center_field = registration_center_field,
                        registration_date_field = registration_date_field,
                        registration_project_id = registration_project_id,
                        registration_center_lookup = registration_center_lookup
                    )
                    self.insert('candidate', candidate_info)
                    if self.verbose:
                        print(f"Added candidate: {record['record_id']}")
                    num_added += 1
                except Exception:
                    self.log_error(method='populate_candidate_table', details=record["record_id"])
                    num_error += 1
        print(f"{num_added + num_old} candidates in LORIS. {num_old} unchanged, {num_added} added. {num_error} errors.", flush=True)

    ## make instruments


    ## set up project in database

    def populate_visit_table(self, **kwargs):
        """
        Adds new visits to the LORIS MySQL database. Used for initial setup.
        Finds visits that have not yet been added to LORIS and adds them. Does not alter existing visits.

        Key Word Arguments
        ----------
        visits: dictionary
            a dictionary describing the visit metadata
            the visit dictionary is used by multiple methods, this method only uses the label attribute
        
        Returns
        ----------
        None
        """
        visits = kwargs.get("visits")

        num_old = self.query(table="visit", fields=["count(*)"])[0]["count(*)"]
        num_new = 0
        num_error = 0

        for visit in visits:
            values = {
                "VisitName": visit["label"],
                "VisitLabel": visit["label"]
            }
            if not len(self.query(table="visit", fields=list(values.keys()), where=values)):
                try:
                    self.insert('visit', values)
                    num_new += 1
                    if self.verbose:
                        print(f"Added visit {visit['label']}")
                except Exception:
                    self.log_error(method="populate_visit_table", details=visit["label"])
                    num_error += 1
        print(f"{num_old + num_new} visits in visit. {num_old} unchanged, {num_new} added. {num_error} errors.", flush=True)

    def populate_test_battery_table(self, **kwargs):
        """
        Inserts tests into the test_battery table in LORIS's MySQL database. Used for initial setup.
        Finds tests that have not yet been inserted into LORIS. Will not update existing visits.

        Key Word Arguments
        ----------
        visits: dictionary
            a dictionary describing the visit metadata
            the visit dictionary is used by multiple methods, this method uses the label and match attributes
        exclude: list of strings
            a list of REDCap forms that will not be transfered to LORIS

        Returns
        ----------
        None

        """
        visits = kwargs.get("visits")
        exclude = kwargs.get("exclude")
        expected_repeat_instruments = kwargs.get("expected_repeat_instruments")

        old_num = self.query(table="test_battery", fields=["count(*)"])[0]["count(*)"]
        new_num = 0
        num_error = 0

        for form in self.form_event_mapping:
            if form["form"] not in exclude:
                visit_labels = []
                if form["form"] in expected_repeat_instruments:
                    visit_labels = list(expected_repeat_instruments[form["form"]].values())
                else:
                    unexpected_repeat = False
                    for form_event in self.repeating_forms_events:
                        if form_event["event_name"] == form["unique_event_name"] and form_event["form_name"] == form["form"]:
                            unexpected_repeat = True
                    if unexpected_repeat:
                        continue

                    visit_label = 'NULL'
                    for visit in visits:
                        if "match" in visit:
                            if visit["match"] in form["unique_event_name"]:
                                visit_label = visit["label"]
                                break
                    visit_labels = [visit_label]

                for visit_label in visit_labels:
                    values = {
                        "Test_name": form["form"],
                        "AgeMinDays": 0,
                        "AgeMaxDays": 99999,
                        "Stage": 'Visit',
                        "SubprojectID": form["arm_num"],
                        "Visit_label": visit_label
                    }
                    if not len(self.query(table="test_battery", fields=list(values.keys()), where=values)):
                        try:
                            if visit_label == 'NULL':
                                raise Exception(f"Visit_label NULL for {form['form']}")
                            self.insert("test_battery", values)
                            new_num += 1
                            if self.verbose:
                                print(f"Added test {form['form']}, {visit_label}")
                        except Exception:
                            self.log_error(method="populate_test_battery_table", details=form["form"])
                            num_error += 1
        print(f"{old_num + new_num} tests in test_battery. {old_num} unchanged, {new_num} added. {num_error} errors.", flush=True)

    def populate_session_table(self, **kwargs):
        """
        Inserts sessions into the LORIS MySQL database.
        Each candidate has a new session in LORIS for every visit, this will insert new rows for the candidate's new visits but not alter old rows.
        Identifies whcih visit to label it as by using the 'match' attribute of visits kwarg

        Key Word Arguments
        ----------
        visits: dictionary
            a dictionary describing the visit metadata
            the visit dictionary is used by multiple methods, this method uses the label, match, scan attributes
        get_subproject_function: function
            a function that takes a record_id and returns a subproject_id.
        report_id: integer
            the id for the report in REDCap.
            this function expects a report that generates a row for each form containing its <form>_complete and <form>_timestamp field
        expected_repeat_instruments: dictionary
            instruments that repeat and should be different visits for each repeat instance. repeat instruments not in this dictionary will be combined with other instruments for that visit when determining visit date.
            keys are instrument names and values are a dictionary with instance number: visit_label pairs.
        
        Returns
        ----------
        None
        """
        visits = kwargs.get("visits")
        get_subproject_function = kwargs.get("get_subproject_function")
        report_id = kwargs.get("report_id")
        expected_repeat_instruments = kwargs.get("expected_repeat_instruments")

        subject_visits = {}
        for record in self.records:
            subject = record['record_id']
            result = self.query(table="candidate", fields=["CandID"], where={"PSCID": subject})
            if result:
                cand_id = result[0]["CandID"]
                if subject not in subject_visits:
                    subject_visits[subject] = { "CandID": cand_id, "visits": {} }
                repeat_instrument = False
                if record["redcap_repeat_instrument"] in expected_repeat_instruments:
                    if record["redcap_repeat_instance"] in expected_repeat_instruments[record["redcap_repeat_instrument"]]:
                        repeat_instrument = True
                        visit_label = expected_repeat_instruments[record["redcap_repeat_instrument"]][record["redcap_repeat_instance"]]
                        for visit in visits:
                            if visit_label == visit["label"]:
                                subject_visits[subject]["visits"][visit_label] = visit
                                break
                if not repeat_instrument:
                    for visit in visits:
                        if "match" in visit:
                            if visit["match"] in record["redcap_event_name"]:
                                subject_visits[subject]["visits"][visit['label']] = visit
                                break

        num_old = self.query(table="session", fields=["count(*)"])[0]["count(*)"]
        num_new = 0
        num_error = 0
        for subject in subject_visits:
            for visit in subject_visits[subject]["visits"]:
                values = {
                    'CandID': subject_visits[subject]["CandID"],
                    'Visit_label': visit,
                }
                if not len(self.query(table="session", fields=list(values.keys()), where=values)):
                    scan_done = 'Y' if subject_visits[subject]["visits"][visit]['scan'] else 'N'
                    result = self.query(table='candidate', fields=['RegistrationCenterID', 'RegistrationProjectID'], where={"PSCID": subject})[0]
                    center_id = result['RegistrationCenterID']
                    project_id = result["RegistrationProjectID"]
                    subproject_id = get_subproject_function(subject)

                    timestamps = []
                    for row in self.reports[report_id]:
                        if subject in row["record_id"]:
                            if "match" in subject_visits[subject]["visits"][visit]:
                                if subject_visits[subject]["visits"][visit]['match'] in row["redcap_event_name"]:
                                    for field in row:
                                        if "_timestamp" in field and row[field]:
                                            timestamps.append(row[field])
                            if row["redcap_repeat_instrument"] in expected_repeat_instruments:
                                if row["redcap_repeat_instance"] in expected_repeat_instruments[row["redcap_repeat_instrument"]]:
                                    if row[f"{row['redcap_repeat_instrument']}_timestamp"]:
                                        timestamps.append(row[f"{row['redcap_repeat_instrument']}_timestamp"])
                    try:
                        visit_date = functools.reduce(lambda a, b: a if a < b else b, timestamps)
                    except Exception:
                        self.log_error(method="functools.reduce() in populate_session_table", details=f"{subject}, {visit}")
                        num_error += 1
                        continue

                    values.update({ 
                        'CenterID': center_id,
                        'ProjectID': project_id,
                        'SubprojectID': subproject_id,
                        'Current_stage': "Visit",
                        'Visit': "In Progress",
                        'Date_visit': visit_date,
                        'RegisteredBy': "redcapTransfer",
                        'UserID': "redcapTransfer",
                        'Scan_done': scan_done,
                        'languageID': 1
                    })
                    try:
                        self.insert('session', values)
                        num_new += 1
                        if self.verbose:
                            print(f"Added session {subject}, {visit_label}")
                    except Exception:
                        self.log_error(method="populate_session_table", details=f"{subject}, {visit}")
                        num_error += 1
        print(f"{num_old + num_new} sessions in session. {num_old} unchanged, {num_new} added. {num_error} errors.", flush=True)

    def populate_session_table_override(self, **kwargs):
        """
        Inserts sessions into the LORIS MySQL database.
        Differs from populate_session_table by allowing the user to start LORIS visits from instruments that are otherwise combined in a single REDCap visit
        Identifies whcih visit to label it as by looking for the field defined by 'override' in a record

        Key Word Agruments
        ----------
        visits: dictionary
            a dictionary describing the visit metadata
            the visit dictionary is used by multiple methods, this method uses the label, date_field, override and scan attributes
        get_subproject_function: function
            a function that takes a record_id and returns a subproject_id.
        expected_repeat_instruments: dictionary
            instruments that repeat and should be different visits for each repeat instance. repeat instruments not in this dictionary will be combined with other instruments for that visit when determining visit date.
            keys are instrument names and values are a dictionary with instance number: visit_label pairs.
        handle_subject_ids: function
            takes a record_id an returns a subject_id.
            Used to handle REDCap instances where multiple candidate records may correspond to the same candidate
            if not given defaults to returning the record_id unchanged.
        
        Returns
        ----------
        None
        """
        visits = kwargs.get("visits")
        get_subproject_function = kwargs.get("get_subproject_function")
        expected_repeat_instruments = kwargs.get("expected_repeat_instruments")
        handle_subject_ids = kwargs.get("handle_subject_ids", lambda x: x)

        num_old = self.query(table="session", fields=["count(*)"])[0]["count(*)"]
        num_new = 0
        num_error = 0

        for visit in visits:
            if 'override' in visit:
                visit_label = visit["label"]
                date_field = visit["date_field"]
                override = visit["override"]
                scan_done = 'Y' if visit['scan'] else 'N'
                
                for record in self.records:
                    if record[override]:
                        if record["redcap_repeat_instrument"]:
                            repeat_instrument = record["redcap_repeat_instrument"]
                            repeat_instance = record["redcap_repeat_instance"]
                            skip = True
                            if repeat_instrument in expected_repeat_instruments:
                                if repeat_instance in expected_repeat_instruments[repeat_instrument]:
                                    if visit_label == expected_repeat_instruments[repeat_instrument][repeat_instance]:
                                        skip = False
                            if skip:
                                continue
                                    
                        subject = handle_subject_ids(record['record_id'])
                        result = self.query(table="candidate", fields=["CandID", "RegistrationCenterID", "RegistrationProjectID"], where={"PSCID":subject})
                        try:
                            cand_id = result[0]["CandID"]
                        except:
                            self.log_error(method="populate_session_table_override", details=f"{subject}, {visit_label}")
                            num_error += 1
                            continue
                        values = {
                            'CandID': cand_id,
                            'Visit_label': visit_label,
                        }
                        if not len(self.query(table="session", fields=list(values.keys()), where=values)):
                            center_id = result[0]['RegistrationCenterID']
                            project_id = result[0]["RegistrationProjectID"]
                            subproject_id = get_subproject_function(subject)
                            visit_date = record[date_field]

                            values.update({ 
                                'CenterID': center_id,
                                'ProjectID': project_id,
                                'SubprojectID': subproject_id,
                                'Current_stage': "Visit",
                                'Visit': "In Progress",
                                'Date_visit': visit_date,
                                'RegisteredBy': "redcapTransfer",
                                'UserID': "redcapTransfer",
                                'Scan_done': scan_done,
                                'languageID': 1
                            })
                            try:
                                self.insert('session', values)
                                num_new += 1
                                if self.verbose:
                                    print(f"Added session {subject}, {visit_label}")
                            except Exception:
                                self.log_error(method="populate_session_table_override", details=f"{subject}, {visit}")
                                num_error += 1
        print(f"{num_old + num_new} sessions in session. {num_old} unchanged, {num_new} added. {num_error} errors.", flush=True)

    def transfer_data(self, **kwargs):
        """
        Loops through REDCap records and identifies where to insert records in LORIS's MySQL database.

        Key Word Arguments
        ----------
        visits: dictionary
            a dictionary describing the visit metadata
            the visit dictionary is used by multiple methods, this method uses the label and match attributes
        expected_repeat_instruments: dictionary
            instruments that repeat and should be different visits for each repeat instance. repeat instruments not in this dictionary will be combined with other instruments for that visit when determining visit date.
            keys are instrument names and values are a dictionary with instance number: visit_label pairs.
        handle_subject_ids: function
            takes a record_id an returns a subject_id.
            Used to handle REDCap instances where multiple candidate records may correspond to the same candidate
            if not given defaults to returning the record_id unchanged.

        Returns
        ----------
        None
        """
        visits = kwargs.get("visits")
        expected_repeat_instruments = kwargs.get("expected_repeat_instruments")
        handle_subject_ids = kwargs.get("handle_subject_ids", lambda x: x)

        num_flag = self.query(table="flag", fields=["count(*)"])[0]["count(*)"]
        updated_flag = 0
        updated_inst = 0
        num_error = 0

        keys = list(self.records[0].keys())
        multi_selects = []
        for key in keys:
            if "___" in key:
                split_key = key.split("___")[0]
                if split_key not in multi_selects:
                    multi_selects.append(split_key)

        for record in self.records:
            try:
                for visit in visits:
                    if "match" in visit:
                        if visit["match"] in record["redcap_event_name"]:
                            visit_label = visit["label"]
                            break

                if record["redcap_repeat_instrument"]:
                    if record["redcap_repeat_instrument"] in expected_repeat_instruments:
                        visit_label = expected_repeat_instruments[record["redcap_repeat_instrument"]][record["redcap_repeat_instance"]]
                    else:
                        continue
            except:
                self.log_error(method="transfer_data", details=f"Visit lookup for {record['record_id']}")
                num_error += 1

            updated_inst, updated_flag, num_error = self.update_data(handle_subject_ids=handle_subject_ids, record=record, multi_selects=multi_selects, visit_label=visit_label, updated_inst=updated_inst, updated_flag=updated_flag, num_error=num_error)

        print(f"{int(num_flag/2)} tests in flag. {updated_inst} instrument entries updated. {updated_flag} flag entries updated. {num_error} errors.", flush=True)

    def update_data(self, **kwargs):
        """
        Updates an entry in the LORIS MySQL databse with data from REDCap. Called by transfer_data to do the actual data transfer.

        Key Word Arguments
        ----------
        handle_subject_ids: function
            takes a record_id an returns a subject_id.
            Used to handle REDCap instances where multiple candidate records may correspond to the same candidate
            if not given defaults to returning the record_id unchanged.
        record: dictionary
            a single REDCap record from self.records
        multi_selects: list of strings
            fields that are multi-select in REDCap and need to be combined to be inserted into LORIS
        visit_label: string
            the name of the visit to be updated
        updated_inst: int
            current number of successful instrument table updates performed, to be incremented upon success.
        updated_flag: int
            current number of successful flag table updates performed, to be incremented upon success.
        num_error: int
            current number of unsuccessful update attempts, to be incremented upon failure.

        Returns
        ----------
        updated_inst
            described above
        updated_flag
            described above
        num_error
            described above
        """
        handle_subject_ids = kwargs.get("handle_subject_ids", lambda x: x)
        record = kwargs.get("record")
        multi_selects = kwargs.get("multi_selects")
        visit_label = kwargs.get("visit_label")
        updated_inst = kwargs.get("updated_inst")
        updated_flag = kwargs.get("updated_flag")
        num_error = kwargs.get("num_error")

        subject = handle_subject_ids(record["record_id"])
        result = self.query(table="candidate", fields=["CandID", "RegistrationCenterID", "RegistrationProjectID"], where={"PSCID": subject})
        try:
            cand_id = result[0]["CandID"]
        except:
            self.log_error(method="transfer_data", details=f"CandID lookup for {subject}")
            num_error += 1
            return updated_inst, updated_flag, num_error
        result = self.query(table="session", fields=["ID", "SubprojectID"], where={"CandID": cand_id, "Visit_label": visit_label })
        try:
            session_id = result[0]['ID']
            subproject_id = result[0]['SubprojectID']
        except:
            self.log_error(method="transfer_data", details=f"session lookup for {subject}")
            num_error += 1
            return updated_inst, updated_flag, num_error
        partial_comment_id = f"{cand_id}{subject}{session_id}{subproject_id}"

        tests = self.query(table="flag", fields=["Test_name"], where_like={ "CommentID": f"{partial_comment_id}%" })
        for test in tests:
            test_name = test["Test_name"]
            current_data = self.query(table=test_name, fields=["*"], where_like={ "CommentID": f"{partial_comment_id}%" })
            values = current_data[0]
            empty = True
            for value in values:
                if value in record:
                    if record[value]:
                        values[value] = record[value]
                        empty = False
                    else:
                        values[value] = None
                elif value in multi_selects:
                    choice_string = list(filter(lambda field: field["field_name"] == value, self.metadata))[0]["select_choices_or_calculations"]
                    choices = { choice.split(", ")[0]: choice.split(", ")[1] for choice in choice_string.split(" | ") }
                    multi_select_values = [choices[choice] for choice in choices if record[f"{value}___{choice}"] == "1"]
                    if multi_select_values:
                        values[value] = ",".join(multi_select_values)
                        empty = False
                    else:
                        values[value] = None
            if not empty:
                try:
                    self.update(table=test_name, fields=values, where={ "CommentID": values["CommentID"]})
                    updated_inst += 1
                    if self.verbose:
                        print(f"Updated {test_name}, {subject}")
                except Exception:
                    self.log_error(method="transfer_data", details=f"update {test_name}, {subject}")
                    num_error += 1
                if record[f"{test_name}_complete"] == "2":
                    flag_values = {
                        "Data_entry": "Complete",
                        "Administration": "All"
                    }
                    try:
                        self.update(table="flag", fields=flag_values, where={ "CommentID": values["CommentID"]})
                        updated_flag += 1
                        if self.verbose:
                            print(f"Updated flag: {test_name}, {subject}")
                    except Exception:
                        self.log_error(method="transfer_data", details=f"update flag: {test_name}, {subject}")
                        num_error += 1
        return updated_inst, updated_flag, num_error

    def populate_candidate_parameters(self, **kwargs):
        """
        Adds data to the multiple tables involved in the Candidate Information page in LORIS.

        Key Word Arguments
        ----------
        candidate_parameters: dictionary
            information on what parameters to update

        Returns
        ----------
        None
        """
        # add to parameter_type_category and parameter_type_category_rel
        candidate_parameters = kwargs.get("candidate_parameters")

        num_parameters = self.query(table="parameter_candidate", fields=["count(*)"])[0]["count(*)"]
        num_new = 0
        num_error = 0

        keys = list(self.records[0].keys())
        multi_selects = []
        for key in keys:
            if "___" in key:
                split_key = key.split("___")[0]
                if split_key not in multi_selects:
                    multi_selects.append(split_key)

        for parameter in candidate_parameters:
            metadata = list(filter(lambda field: field["field_name"] == parameter, self.metadata))[0]
            result = self.query(table="parameter_type", fields=["ParameterTypeID"], where={ "Name": parameter })
            if result:
                parameter_id = result[0]["ParameterTypeID"]
            else:
                values = {
                    "Name": parameter,
                    "Type": "varchar(255)",
                    "Description": metadata["field_label"],
                    "SourceFrom": "parameter_file",
                    "Queryable": 1
                }
                self.insert("parameter_type", values)
                parameter_id = self.query(table="parameter_type", fields=["ParameterTypeID"], where={ "Name": parameter })[0]["ParameterTypeID"]

            for record in self.records:
                empty = True
                if parameter in multi_selects:
                    fields = list(filter(lambda field: parameter in field, list(record.keys())))
                    if record[fields[0]]:
                        empty = False

                    if not empty:
                        choice_string = list(filter(lambda field: field["field_name"] == parameter, self.metadata))[0]["select_choices_or_calculations"]
                        choices = { choice.split(", ")[0]: choice.split(", ")[1] for choice in choice_string.split(" | ") }
                        multi_select_values = [choices[choice] for choice in choices if record[f"{parameter}___{choice}"] == "1"]
                        value  = ", ".join(multi_select_values)

                else:
                    if record[parameter]:
                        empty = False
                        choice_string = list(filter(lambda field: field["field_name"] == parameter, self.metadata))[0]["select_choices_or_calculations"]
                        choices = { choice.split(", ")[0]: choice.split(", ")[1] for choice in choice_string.split(" | ") }
                        value = choices[record[parameter]]
                
                if not empty:
                    subject = record["record_id"]
                    result = self.query(table="candidate", fields=["CandID"], where={"PSCID": subject})
                    try:
                        cand_id = result[0]["CandID"]
                    except:
                        self.log_error(method="populate_candidate_parameters", details=f"CandID lookup for {subject}")
                        num_error += 1
                        continue

                    to_insert = { 
                        "CandID": cand_id,
                        "ParameterTypeID": parameter_id,
                        "Value": value
                    }
                    if not len(self.query(table="parameter_candidate", fields=list(to_insert.keys()), where=to_insert)):
                        try:
                            self.insert("parameter_candidate", to_insert)
                            num_new += 1
                            if self.verbose:
                                print(f"Inserted Candidate Parameter: {parameter}, {subject}")
                        except Exception:
                            self.log_error(method="populate_candidate_parameters", details=f"insert parameter_candidate: {parameter}, {subject}")
                            num_error += 1

        print(f"{num_parameters} candidate parameters in parameter_candidate. {num_new} added. {num_error} errors.", flush=True)

    def populate_flag_table(self, **kwargs):
        """
        Inserts a new row into flag and the corresponding instrument table in LORIS. Mimics the standard LORIS script assign_missing_instruments.php

        Key Word Arguments
        ----------
        visits: dictionary
            a dictionary describing the visit metadata
            the visit dictionary is used by multiple methods, this method only uses the label attribute

        Returns
        ----------
        None
        """
        visits = kwargs.get("visits")

        num_flag = self.query(table="flag", fields=["count(*)"])[0]["count(*)"]
        num_added = 0
        num_error = 0

        for visit in visits:
            query = f"SELECT DISTINCT s.CandID, c.PSCID, s.ID AS sessionID, s.subprojectID, tn.ID AS testID, tb.Test_name from session s LEFT JOIN candidate c USING (CandID) RIGHT JOIN test_battery tb USING (Visit_label) LEFT JOIN test_names tn USING (Test_name) WHERE s.Active='Y' AND c.Active='Y' AND tb.Active='Y' AND s.visit_label='{visit['label']}'"
            self.cursor.execute(query)
            result = [row for row in self.cursor]
            for row in result:
                test_name = row['Test_name']
                partial_comment_id = f"{row['CandID']}{row['PSCID']}{row['sessionID']}{row['subprojectID']}{row['testID']}"
                comment_id_list = self.query(table=test_name, fields=["CommentID"], where_like={ "CommentID": f"{partial_comment_id}%" })
                if len(comment_id_list) == 0:
                    timestamp = int(datetime.datetime.utcnow().timestamp())
                    comment_id = f"{partial_comment_id}{timestamp}"
                    try:
                        flag_values = {
                            "SessionID": row["sessionID"],
                            "Test_name": test_name,
                            "CommentID": comment_id,
                            "UserID": 'redcapTransfer'
                        }
                        self.insert("flag", flag_values)
                        flag_values["CommentID"] = f"DDE_{comment_id}"
                        self.insert("flag", flag_values)
                        if self.verbose:
                            print(f"Inserted into flag: {comment_id}")
                        inst_values = {
                            "CommentID": comment_id
                        }
                        self.insert(test_name, inst_values)
                        if self.verbose:
                            print(f"Inserted new row into {test_name}")
                        num_added += 1
                    except:
                        self.log_error(method="populate_flag_table", details=comment_id)
                        num_error += 1

        print(f"{int(num_flag/2) + num_added} entries in flag. {num_added} added. {num_error} errors.", flush=True)

    def truncate_all_instruments(self):
        """
        Truncates all insturment tables.  
        """
        for form in self.form_event_mapping:
            try:
                statement = f"TRUNCATE {form['form']}"
                self.cursor.execute(statement)
            except:
                self.log_error(method="truncate_all_instruments", details=form['form'])