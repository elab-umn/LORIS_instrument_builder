import mysql.connector
from config import config, token
import datetime
import requests
import json
from jinja2 import Template
import traceback
import functools

class Loris:

    def __init__(self):
        self.cnx = mysql.connector.connect(**config)
        self.cursor = self.cnx.cursor(dictionary=True)
        self.error_log = "outputs/data_transfer_errors.txt"
        self.token = token

    def __del__(self):
        self.cnx.close()
        self.cursor.close()

    def commit(self):
        self.cnx.commit()

    def insert(self, table, columns, values):
        statement = (f"INSERT INTO {table} " f"({columns}) " f"VALUES ({values})")
        self.cursor.execute(statement)

    def query(self, table, fields, condition):
        query = (f"SELECT {fields} FROM {table} " f"WHERE {condition}")
        self.cursor.execute(query)
        self.result = [row for row in self.cursor]

    def add_project(self, **kwargs):
        name = kwargs.get('name')
        alias = kwargs.get('alias')
        target = kwargs.get('target', 0)

        self.insert('Project', 'Name, Alias, recruitmentTarget', f'{name}, {alias}, {target}')
        self.project_id = self.cursor.lastrowid

    def add_psc(self, **kwargs):
        name = kwargs.get('name')
        alias = kwargs.get('alias')

        self.insert('psc', 'Name, Alias, Study_site', f'{name}, {alias}, Y')
        self.center_id = self.cursor.lastrowid

    def add_subproject(self, **kwargs):
        name = kwargs.get('name')
        use_edc = kwargs.get('use_edc', 0)
        window_difference = kwargs.get('window_difference', 'optimal')
        target = kwargs.get('target')

        self.insert('subproject', 'title, useEDC, WindowDifference, RecruitmentTarget', f'{name}, {use_edc}, {window_difference}, {target}')
        self.subproject_id = self.cursor.lastrowid

    def add_visit(self, **kwargs):
        name = kwargs.get('name')
        label = kwargs.get('label', name)

        self.insert('visit', 'VisitName, VisitLabel', f'{name}, {label}')
        self.visit_id = self.cursor.lastrowid

    def link_subproj(self, **kwargs):
        proj = kwargs.get('project')
        sub = kwargs.get('subproject')
        values = ''
        if proj and sub:
            self.query('Project', 'ProjectID', f"Name = '{proj}'")
            proj_id = self.result[0]['ProjectID']
            self.query('subproject', 'SubprojectID', f"title = '{sub}'")
            sub_id = self.result[0]['SubprojectID']

            values = f'{proj_id}, {sub_id}'
        else:
            values = f'{self.project_id}, {self.subproject_id}'
        self.insert('project_subproject_rel', 'ProjectID, SubprojectID', values)

    def add_to_test_battery(self, **kwargs):
        test = kwargs.get('instrument')
        visit = kwargs.get('visit')
        subproject = kwargs.get('subproject')
        age_min_days = kwargs.get('age_min_days', 0)
        age_max_days = kwargs.get('age_max_days', 99999)
        active = kwargs.get('active', 'Y')
        stage = kwargs.get('stage', 'Visit')
        center_id = kwargs.get('center_id', 'NULL')
        first_visit = kwargs.get('first_visit', 'NULL')
        instrument_order = kwargs.get('instrument_order', 'NULL')

        columns = 'Test_name, AgeMinDays, AgeMaxDays, Active, Stage, SubprojectID, Visit_label, CenterID, firstVisit, instr_order'
        values = f"'{test}', {age_min_days}, {age_max_days}, '{active}', '{stage}', {subproject}, '{visit}', {center_id}, {first_visit}, {instrument_order}"
        self.insert('test_battery', columns, values)

    def get_candidate_info(self, **kwargs):
        subject = kwargs.get('subject')
        candidate = kwargs.get('candidate')
        columns = 'PSCID, CandID, RegistrationCenterID, RegistrationProjectID'

        if subject:
            condition = f"PSCID = '{subject}'"
        elif candidate:
            condition = f"CandID = '{candidate}'"
        self.query('candidate', columns, condition)
        return self.result[0]
        
    def add_session(self, **kwargs):
        subject = kwargs.get('subject')
        subproject_id = kwargs.get('subproject_id')
        visit = kwargs.get('visit')
        today = datetime.date.today().strftime("%Y-%m-%d")
        visit_date = kwargs.get('visit_date', today)
        scan_done = kwargs.get('scan_done', 'N')
        cand = self.get_candidate_info(subject=subject)

        cand_id = cand['CandID']
        center_id = cand['RegistrationCenterID']
        project_id = cand['RegistrationProjectID']

        columns = 'CandID, CenterID, ProjectID, Visit_label, SubprojectID, Current_stage, Date_stage_change, Visit, Date_visit, Date_active, RegisteredBy, UserID, Date_registered, Testdate, Scan_done, languageID'
        values = f"{cand_id}, {center_id}, {project_id}, '{visit}', {subproject_id}, 'Visit', '{today}', 'In Progress', '{visit_date}', '{today}', 'redcapTransfer', 'redcapTransfer', '{today}', '{today}', '{scan_done}', 1"
        print(f"Adding session: {subject}, {visit}")
        self.insert('session', columns, values)

    def get_active_visits(self, **kwargs):
        subject = kwargs.get('subject')
        data = {
            'token': self.token,
            'content': 'record',
            'action': 'export',
            'format': 'json',
            'type': 'flat',
            'csvDelimiter': '',
            'records[0]': subject,
            'rawOrLabel': 'raw',
            'rawOrLabelHeaders': 'raw',
            'exportCheckboxLabel': 'false',
            'exportSurveyFields': 'false',
            'exportDataAccessGroups': 'false',
            'returnFormat': 'json',
            'dateRangeBegin': ''
        }
        r = requests.post('https://redcap.ahc.umn.edu/api/',data=data)
        print(f'get active visits {subject} HTTP Status: ' + str(r.status_code))
        records = r.json()

        visits = {'visit_1': False, 'visit_2': False, 'mri_visit': False}
        for record in records:
            if 'visit_1' in record['redcap_event_name']:
                visits['visit_1'] = True
            if 'visit_2' in record['redcap_event_name']:
                visits['visit_2'] = True
            if 'mri_visit' in record['redcap_event_name']:
                visits['mri_visit'] = True
        active_visits = [ visit for visit in visits.keys() if visits[visit]]
        return active_visits

    def add_sessions(self, **kwargs):
        subjects = kwargs.get('subjects')

        with open(self.error_log, "a") as file:
            file.write(f"============ Add Sessions: {datetime.datetime.now()} ============\n")

        for subject in subjects:
            visits = self.get_active_visits(subject=subject)
            if subject in self.candid_dict:
                candid = self.candid_dict[subject]
                for visit in visits:
                    if candid not in self.sessions:
                        self.sessions[candid] = {}
                    if visit not in self.sessions[candid]:
                        subproject_id = 1 if 'SUB-1' in subject else 2
                        scan_done = 'Y' if visit == 'mri_visit' else 'N'
                        visit_date = self.get_session_date(visit=visit, subject=subject)
                        try:
                            self.add_session(subject=subject, subproject_id=subproject_id, visit=visit, visit_date=visit_date, scan_done=scan_done)
                        except Exception:
                            self.log_data_transfer_error(table="session", criteria=f"{subject} {visit}")

    def start_visit(self):
        print("Please run assign_missing_instruments.php to start visits")

    def get_form_metadata(self, **kwargs):
        forms = kwargs.get('forms')
        data = {
            'token': f'{self.token}',
            'content': 'metadata',
            'format': 'json',
            'returnFormat': 'json',
        }
        data.update({f'forms[{index}]': form for index, form in enumerate(forms)})
        r = requests.post('https://redcap.ahc.umn.edu/api/',data=data)
        print('HTTP Status: ' + str(r.status_code))
        records = r.json()
        self.metadata = { record['form_name']: { field['field_name']: { 'field_type': field['field_type'], 'field_label': field['field_label'], 'select_choices_or_calculations': field['select_choices_or_calculations'], 'text_validation_type_or_show_slider_number': field['text_validation_type_or_show_slider_number']} for field in records if field['form_name'] == record['form_name']} for record in records if record['form_name'] in forms}
        with open('outputs/form.json', 'w+') as file:
            json.dump(self.metadata, file, indent=4)

    def get_all_subject_ids(self):
        print("Getting Subject IDs...")
        data = {
            'token': f'{self.token}',
            'content': 'record',
            'action': 'export',
            'format': 'json',
            'type': 'flat',
            'csvDelimiter': '',
            'fields[0]': 'record_id',
            'rawOrLabel': 'raw',
            'rawOrLabelHeaders': 'raw',
            'exportCheckboxLabel': 'false',
            'exportSurveyFields': 'false',
            'exportDataAccessGroups': 'false',
            'returnFormat': 'json'
        }

        r = requests.post('https://redcap.ahc.umn.edu/api/',data=data)
        print('get all subject ids HTTP Status: ' + str(r.status_code))
        records = r.json()
        subjects = []
        for record in records:
            subject = record['record_id']
            if(subject not in subjects and 'SUB' in subject and subject[-1] != 'T'):
                subjects.append(subject)
        self.subjects = subjects

    def field_type_lookup(self, question):
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

    def make_enum_array(self, question):
        options = question['select_choices_or_calculations']
        field_type = question['field_type']

        if self.field_type_lookup(question) == 'enum':
            options_loris = []
            options_sql = []
            if field_type == 'yesno':
                options_loris = ['No', 'Yes']
                options_sql = [ '0', '1' ]
            else:
                options_sql = [option.split(',')[0] for option in options.split('|')]
                options_loris = [option.split(',')[1] for option in options.split('|')]

            opt_str = "''=>''"
            for optionNum, _ in enumerate(options_sql):
                opt_sql = options_sql[optionNum].strip().strip("'").strip('"')
                opt_loris = options_loris[optionNum].strip().strip("'").strip('"')
                opt_str += ", '" + opt_sql + "'=>" + '"' + opt_loris + '"'
            opt_str += ", " + "'not_answered'=>'Not Answered'"
            return opt_str
        else:
            return ''

    def create_instrument_php(self, **kwargs):
        form = kwargs.get('form')
        include_meta_fields = kwargs.get("include_meta_fields", True)
        field_type = {'text': ['varchar', 'varchar(255)', 'int', 'char', 'tinyint', 'smallint', 'mediumint', 'bigint', 'decimal', 'dec',
                       'float', 'double', 'tinytext'],
              'textarea': ['text', 'mediumtext', 'longtext'],
              'select': 'enum', 'date': 'date'}

        values = self.metadata[form]
        date_fields = [field for field in values if self.field_type_lookup(values[field]) == 'date']
        instrument_params = {
            "instrument_table_name": form,
            "validity_required": False,
            "validity_enabled": False,
            "include_meta_fields": include_meta_fields,
            "date_fields":date_fields,
            "loris_num_pages": 1,
            "instrument_name_text": form
        }
        var_data_object = [
            {
                "page": 1,
                "var_type": self.field_type_lookup(values[value]),
                "status":'',
                "front_end": True,
                "name": value,
                "text": values[value]['field_label'].replace('"', "'"),
                "enum_array": self.make_enum_array(values[value])
            }
            for i, value in enumerate(values)]

        jinja_dict = {'param': instrument_params, 'var_data': var_data_object, 'field_type': field_type}

        with open('LORIS_php_instrument_template.html.jinja2') as filein:  # noqa
            loris_template = Template(filein.read(), trim_blocks=True, lstrip_blocks=True)
        
        with open('outputs/php/NDB_BVL_Instrument_' + instrument_params['instrument_table_name'] + '.class.inc', 'w') as fileout:
            fileout.write(loris_template.render(jinja_dict))

    def create_table_lines(self, question, values):
        field_type = values['field_type']
        sql_type = self.field_type_lookup(values)
        if sql_type == 'enum':
            enums = 'enum('
            if field_type == 'yesno':
                enums += "'0', '1', 'not_answered')"
            else:
                choices = values['select_choices_or_calculations']
                choices = [choice.split(',')[0] for choice in choices.split('|')]
                for choice in choices:
                    choice_string = choice.strip().strip("'").strip('"')
                    enums += f"'{choice_string}', "
                enums += "'not_answered')"
            sql_type = enums
        sql_line = f"  `{question}` {sql_type} DEFAULT NULL,\n"
        return sql_line

    def create_instrument_sql(self, **kwargs):
        form = kwargs.get('form')
        include_meta_fields = kwargs.get("include_meta_fields", True)
        file_output = kwargs.get('file_output')
        create_table = kwargs.get('create_table')
        drop = kwargs.get('drop', False)
        
        table_line_start = f"CREATE TABLE `{form}` (\n"
        meta_fields = "  `CommentID` varchar(255) NOT NULL DEFAULT '',\n"  
        if include_meta_fields:
            meta_fields += "`UserID` varchar(255) DEFAULT NULL,\n`Examiner` varchar(255) DEFAULT NULL,\n`Testdate` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,\n`Data_entry_completion_status` enum('Incomplete','Complete') NOT NULL DEFAULT 'Incomplete',\n`Date_taken` date DEFAULT NULL,\n`Candidate_Age` varchar(255) DEFAULT NULL,\n`Window_Difference` int(11) DEFAULT NULL,"
        else:
            meta_fields += "`UserID` varchar(255) DEFAULT NULL,\n"
        table_line_end = """  PRIMARY KEY (`CommentID`)\n) ENGINE=InnoDB DEFAULT CHARSET=utf8;\n"""
        test_name_insert = f"INSERT IGNORE INTO test_names (Test_name, Full_name, Sub_group) VALUES ('{form}','{form}',1);"
        sql_lines = ''
        for question in self.metadata[form]:
            if self.metadata[form][question]["field_type"] != "descriptive":
                sql_line = self.create_table_lines(question, self.metadata[form][question])
                if sql_line:
                    sql_lines += sql_line
        sql_string = table_line_start + meta_fields + sql_lines + table_line_end + test_name_insert

        if(file_output):
            sqlfile = open(f'outputs/sql/{form}.sql', 'w')
            sqlfile.write(sql_string)
            sqlfile.close()

        if(create_table):
            while(self.cnx.next_result()):
                pass
            try:
                if drop:
                    self.cursor.execute(f"DROP TABLE IF EXISTS {form}")
                self.cursor.execute(sql_string)
                print(f"Successfully created {form} table.")
            except Exception as e:
                print(f"Error creating table {form}:", e)

    def create_all_instrument_files(self, **kwargs):
        exclude = kwargs.get('exclude', [])
        php = kwargs.get('php', False)
        sql = kwargs.get('sql', False)
        include_meta_fields = kwargs.get("include_meta_fields", True)
        self.get_all_form_metadata(exclude=exclude)
        for inst in self.metadata:
            if php:
                self.create_instrument_php(form=inst, include_meta_fields=include_meta_fields)
            if sql:
                self.create_instrument_sql(form=inst, file_output=True, create_table=True, drop=True, include_meta_fields=include_meta_fields)

    def parse_metadata(self):
        # utility function to see what data types are in use
        field_types = []
        for inst in self.metadata:
            for question in self.metadata[inst]:
                if self.metadata[inst][question]['field_type'] not in field_types:
                    field_types.append(self.metadata[inst][question]['field_type'])
        print(field_types)

    def get_participant_status(self):
        pass

    def drop_tables(self, **kwargs):
        tables = kwargs.get('tables')
        for table in tables:
            self.cursor.execute(f"DROP TABLE IF EXISTS {table}")

    def get_forms(self, **kwargs):
        exclude = kwargs.get('exclude', [])
        data = {
            'token': self.token,
            'content': 'formEventMapping',
            'format': 'json',
            'arms[0]': '1',
            'returnFormat': 'json'
        }
        r = requests.post('https://redcap.ahc.umn.edu/api/',data=data)
        print('get forms HTTP Status: ' + str(r.status_code))
        records = r.json()

        visits = ['visit_1', 'visit_2', 'mri_visit']

        self.forms = { visit: [ record['form'] for record in records if visit in record['unique_event_name'] and  record['form'] not in exclude] for visit in visits }

    def list_all_forms(self, **kwargs):
        exclude = kwargs.get('exclude', [])
        self.get_forms(exclude=exclude)
        forms = []
        for visit in self.forms:
            for form in self.forms[visit]:
                if form not in forms:
                    forms.append(form)
        return forms

    def get_all_form_metadata(self, **kwargs):
        exclude = kwargs.get('exclude', [])
        self.get_form_metadata(forms=self.list_all_forms(exclude=exclude))

    def populate_visits(self, **kwargs):
        subprojects = kwargs.get('subprojects', [1,2])
        for visit in self.forms:
            for form in self.forms[visit]:
                for subproject in subprojects:
                    try:
                        self.add_to_test_battery(instrument=form, subproject=subproject, visit=visit)
                        print(f'successfully added instrument {form} to test_battery')
                    except Exception as e:
                        print(f'error adding instrument {form} to test_battery: ', e)

    def add_all_sessions(self):
        self.get_all_subject_ids()
        self.get_candids_from_subjects(subjects=self.subjects)
        self.get_session_info()
        self.get_survey_dates()
        self.add_sessions(subjects=self.subjects)

    def get_candids_from_subjects(self, **kwargs):
        subjects = kwargs.get('subjects')

        conditon = "PSCID IN ('" + ("', '").join(subjects) + "')"
        self.query('candidate', 'PSCID, CandID', conditon)

        self.candid_dict = {record['PSCID']: record['CandID'] for record in self.result}
    
    def get_session_info(self):
        self.query('session', 'ID, CandID, Visit_label', 'CandID')
        result = self.result
        sessions = { record['CandID']: {session['Visit_label']: session['ID'] for session in result if record['CandID'] == session['CandID'] } for record in result }
        self.sessions = sessions

    def assemble_commentid(self, **kwargs):
        pscid = kwargs.get('subject')
        visit = kwargs.get('visit')
        candid = self.get_candidate_info(subject=pscid)['CandID']
        session_id = self.sessions[candid][visit]
        
        commentid = f"{candid}{pscid}{session_id}"
        return commentid

    def redcap_event_to_visit(self, **kwargs):
        event = kwargs.get('event')
        if 'visit_1' in event:
            return 'visit_1'
        elif 'visit_2' in event:
            return 'visit_2'
        elif 'mri_visit' in event:
            return 'mri_visit'
        else:
            print(f'Failed to parse event: {event}')
            return ''

    def update_instrument(self, **kwargs):
            table = kwargs.get('table')
            record = kwargs.get('record')
            comment_id = kwargs.get('comment_id')
            exclude = ['record_id', 'redcap_event_name', 'redcap_repeat_instrument', 'redcap_repeat_instance', f'{table}_complete']
            keys = [key for key in list(record.keys()) if key not in exclude]
            sql = f"UPDATE {table} SET "
            for key in keys:
                sql += f"{key}={self.prepare_update_value(record[key])}, "
            sql = sql[:-2]
            sql += f" WHERE CommentID LIKE '{comment_id}%'"
            self.cursor.execute(sql)
            print(f"Updated {table}: {comment_id}")

    def prepare_update_value(self, value):
        if value == "":
            return "NULL"
        elif isinstance(value, str):
            string = value.replace("'", "\\'")
            return f"'{string}'"
        else:
            return f"'{value}'"

    def log_data_transfer_error(self, **kwargs):
        table = kwargs.get("table")
        criteria = kwargs.get("criteria")

        print(f"Failed to update {table}: {criteria}")
        with open(self.error_log, "a") as file:
            file.write(f"--------------------------\n{datetime.datetime.now()} | Error updating {table}: {criteria} error:\n{traceback.format_exc()}\n")


    def populate_instrument(self, **kwargs):
        form = kwargs.get('form')
        data = {
            'token': f'{self.token}',
            'content': 'record',
            'action': 'export',
            'format': 'json',
            'type': 'flat',
            'csvDelimiter': '',
            'fields[0]': 'record_id',
            'forms[0]': f'{form}',
            'rawOrLabel': 'raw',
            'rawOrLabelHeaders': 'raw',
            'exportCheckboxLabel': 'false',
            'exportSurveyFields': 'false',
            'exportDataAccessGroups': 'false',
            'returnFormat': 'json'
        }
        r = requests.post('https://redcap.ahc.umn.edu/api/',data=data)
        print('Instrument Data HTTP Status: ' + str(r.status_code))
        records = r.json()
        records = [record for record in records if int(record[f'{form}_complete'] or 0)]
        with open('outputs/response.json', 'w+') as file:
            json.dump(records, file, indent=4)

        for record in records:
            record = self.collapse_multi_select(form=form, record=record)
            event = record['redcap_event_name']
            subject = record['record_id']
            if 'teac' in event:
                if ('T' not in subject or 'SUB' not in subject):
                    with open(self.error_log, "a") as file:
                        file.write(f"Unexpected Record: {form}, {subject}\n")
                else:
                    subject = subject[:12]
                    try:
                        comment_id = self.assemble_commentid(subject=subject, visit=self.redcap_event_to_visit(event=event))
                        self.update_instrument(table=form, record=record, comment_id=comment_id)
                    except Exception:
                        self.log_data_transfer_error(table=form, criteria=subject)

            else:
                if ('T' in subject or 'SUB' not in subject):
                    with open(self.error_log, "a") as file:
                        file.write(f"Unexpected Record: {form}, {subject}\n")
                else:
                    try:
                        comment_id = self.assemble_commentid(subject=subject, visit=self.redcap_event_to_visit(event=event))
                        self.update_instrument(table=form, record=record, comment_id=comment_id)
                    except Exception:
                        self.log_data_transfer_error(table=form, criteria=subject)        

    def populate_all_instruments(self, **kwargs):
        exclude = kwargs.get('exclude', [])
        self.get_all_form_metadata(exclude=exclude)
        self.get_all_subject_ids()
        self.get_candids_from_subjects(subjects=self.subjects)
        self.get_session_info()
        with open(self.error_log, "a") as file:
            file.write(f"============ Populate All Instruments: {datetime.datetime.now()} ============\n")
        for form in self.list_all_forms(exclude=exclude):
            self.populate_instrument(form=form)

    def collapse_multi_select(self, **kwargs):
        record = kwargs.get('record')
        form = kwargs.get('form')
        flagged = {field[0:-4]: [item[-1] for item in record if item[0:-4] == field[0:-4] and record[item] != '0'] for field in record if field[-4:-1] == '___'}
        to_del = [field for field in record if field[-4:-1] == '___']
        for field in flagged:
            choices = self.metadata[form][field]['select_choices_or_calculations'].split('|')
            choices = {choice.split(', ')[0].strip(): choice.split(', ')[1].strip() for choice in choices}
            value = ', '.join([choices[str(item)] for item in flagged[field]])
            record[field] = value
        for field in to_del:
            del record[field]
        return record

    def get_survey_dates(self):
        data = {
            'token': self.token,
            'content': 'report',
            'format': 'json',
            'report_id': '47678',
            'csvDelimiter': '',
            'rawOrLabel': 'raw',
            'rawOrLabelHeaders': 'raw',
            'exportCheckboxLabel': 'false',
            'returnFormat': 'json'
        }
        r = requests.post('https://redcap.ahc.umn.edu/api/',data=data)
        print('Survey Dates HTTP Status: ' + str(r.status_code))
        records = r.json()
        with open('outputs/response.json', 'w+') as file:
            json.dump(records, file, indent=4)

        visits = ['visit_1', 'visit_2', 'mri_visit']
        timestamps = {record['record_id'][:12]: {visit: {event['redcap_event_name']: {field[:-9]: { 'complete': event[field], 'timestamp': event[f'{field[:-9]}_timestamp'] } for field in event if event[field] and field[-9:] == '_complete'} for event in records if record['record_id'][:12] == event['record_id'][:12] and visit in event['redcap_event_name']} for visit in visits} for record in records if 'SUB' in record['record_id']}

        dict = {}
        for subject in timestamps:
            dict[subject] = {}
            for visit in timestamps[subject]:
                dict[subject][visit] = {}
                for event in timestamps[subject][visit]:
                    for field in timestamps[subject][visit][event]:
                        dict[subject][visit][field] = timestamps[subject][visit][event][field]

        with open('outputs/timestamps.json', 'w+') as file:
            json.dump(dict, file, indent=4)
        
        self.survey_dates = dict

    def update_test_dates(self, **kwargs):
        form = kwargs.get('form')
        subject = kwargs.get('subject')
        timestamp = kwargs.get('timestamp')
        
        visit = kwargs.get('visit')
        examiner = kwargs.get('examiner', 1)
        user_id = kwargs.get('user_id', 'frontEndAdmin')

        comment_id = self.assemble_commentid(subject=subject, visit=visit)
        record = {'Date_taken': timestamp, 'Examiner': examiner, 'UserID': user_id}

        self.update_instrument(table=form, record=record, comment_id=comment_id)


    def update_flag_table(self, **kwargs):
        complete_num = kwargs.get('complete')
        form = kwargs.get('form')
        subject = kwargs.get('subject')
        visit = kwargs.get('visit')

        complete = "In Progress"
        if complete_num == '2':
            complete = "Complete"

        record = {'Data_entry': complete}
        if complete == "Complete":
            record['Administration'] = "All"

        partial_comment_id = self.assemble_commentid(subject=subject, visit=visit)

        self.query(table=form, fields='CommentID', condition=f"CommentID LIKE '{partial_comment_id}%'")
        comment_id = self.result[0]['CommentID']
        self.update_instrument(table='flag', record=record, comment_id=comment_id)


    def get_session_date(self, **kwargs):
        subject = kwargs.get('subject')
        visit = kwargs.get('visit')
        tests = list(self.survey_dates[subject][visit].values())
        filtered_tests = list(filter(lambda x: x["timestamp"], tests))
        min_timestamp = ""
        if len(filtered_tests):
            min_timestamp = functools.reduce(lambda a, b: a if a['timestamp'] < b['timestamp'] else b, filtered_tests)['timestamp']
        return min_timestamp

    def update_all_instrument_metadata(self, **kwargs):
        exclude = kwargs.get('exclude')
        self.get_survey_dates()
        self.get_session_info()
        self.get_all_subject_ids()
        self.get_candids_from_subjects(subjects=self.subjects)
        self.get_forms(exclude=exclude)

        with open(self.error_log, "a") as file:
            file.write(f"============ Update All Instrument Metadata: {datetime.datetime.now()} ============\n")

        for subject in self.survey_dates:
            for visit in self.survey_dates[subject]:
                for form in self.survey_dates[subject][visit]:
                    if form not in exclude and self.survey_dates[subject][visit][form]['timestamp']:
                        timestamp = self.survey_dates[subject][visit][form]['timestamp']
                        complete = self.survey_dates[subject][visit][form]['complete']
                        try:
                            self.update_test_dates(form=form, subject=subject, timestamp=timestamp, complete=complete, visit=visit)
                            self.update_flag_table(form=form, subject=subject, complete=complete, visit=visit)
                        except Exception:
                            self.log_data_transfer_error(table=form, criteria=subject)

    def get_repeating_form(self, **kwargs):
        instrument = kwargs.get("instrument")
        data = {
            'token': self.token,
            'content': 'record',
            'action': 'export',
            'format': 'json',
            'type': 'flat',
            'csvDelimiter': '',
            'fields[0]': 'record_id',
            'forms[0]': instrument,
            'rawOrLabel': 'raw',
            'rawOrLabelHeaders': 'raw',
            'exportCheckboxLabel': 'false',
            'exportSurveyFields': 'false',
            'exportDataAccessGroups': 'false',
            'returnFormat': 'json'
        }
        r = requests.post('https://redcap.ahc.umn.edu/api/',data=data)
        print('get_repeating_form HTTP Status: ' + str(r.status_code))
        records = r.json()
        instrument_data = { record["record_id"]: {instance["redcap_repeat_instance"]: instance for instance in records if instance["redcap_repeat_instance"] and record["record_id"] == instance["record_id"]} for record in records if record["redcap_repeat_instrument"] == instrument}
        with open('outputs/repeat_instrument.json', 'w+') as file:
            json.dump(instrument_data, file, indent=4)
        return instrument_data

    def add_repeat_sessions(self, **kwargs):
        instrument = kwargs.get("instrument")
        visit_label = kwargs.get("visit_label")
        scan_done = kwargs.get("scan_done")
        visit_date_field = kwargs.get("visit_date_field")
        skip_first = kwargs.get("skip_first") #if the first visit is already made

        repeat_instrument = self.get_repeating_form(instrument=instrument)

        for subject in repeat_instrument:
            subproject_id = 1 if "SUB-1" in subject else 2
            for instance in repeat_instrument[subject]:
                if skip_first and instance == 1:
                    pass
                else:
                    visit = f"{visit_label}_{instance}"
                    visit_date = repeat_instrument[subject][instance][visit_date_field]
                    self.add_session(subject=subject, visit=visit, subproject_id=subproject_id, visit_date=visit_date, scan_done=scan_done)

    def get_form_event_mappings(self):
        data = {
            'token': self.token,
            'content': 'formEventMapping',
            'format': 'json',
            'arms[0]': '1',
            'returnFormat': 'json'
        }
        r = requests.post('https://redcap.ahc.umn.edu/api/',data=data)
        print('get forms HTTP Status: ' + str(r.status_code))
        records = r.json()

        self.form_event_mappings = records

    def categorize_forms(self, **kwargs):
        exclude = kwargs.get("exclude")
        mappings = kwargs.get("mappings")

        categorized_forms = {}
        for form in self.form_event_mappings:
            if form["form"] not in exclude:
                found = False
                for key in list(mappings.keys()):
                    if key in form["unique_event_name"]:
                        found = True
                        category = mappings[key]
                        categorized_forms[form["form"]] = category
                if not found:
                    print(f"Form not categorized: {form['form']}")
        return categorized_forms

    def update_instrument_subgroups(self, **kwargs):
        exclude = kwargs.get("exclude")
        mappings = kwargs.get("mappings")

        categories = self.categorize_forms(exclude=exclude, mappings=mappings)

        for category in categories:
            print(f"Updating test_names: {category}, {categories[category]}")
            sql = f"UPDATE test_names SET Sub_group = {categories[category]} WHERE Test_name = '{category}'"
            self.cursor.execute(sql)

    def populate_repeating_instrument(self, **kwargs):
        instrument = kwargs.get("instrument")
        visit_label = kwargs.get("visit_label")
        visit_date_field = kwargs.get("visit_date_field")
        repeat_instrument = self.get_repeating_form(instrument=instrument)

        with open(self.error_log, "a") as file:
            file.write(f"============ Populate Repeating Instrument: {datetime.datetime.now()} ============\n")

        for subject in repeat_instrument:
            for instance in repeat_instrument[subject]:
                record = self.collapse_multi_select(form=instrument, record=repeat_instrument[subject][instance])
                record["Date_taken"] = record[visit_date_field]
                visit = visit_label if instance == 1 else f"{visit_label}_{instance}"
                complete = record[f"{instrument}_complete"]
                try:
                    comment_id = self.assemble_commentid(subject=subject, visit=visit)
                    self.update_instrument(table=instrument, record=record, comment_id=comment_id)
                    self.update_flag_table(form=instrument, subject=subject, complete=complete, visit=visit)
                except Exception:
                    self.log_data_transfer_error(table=instrument, criteria=subject)

    def update_session_dates(self, **kwargs):
        # visits to exclude
        exclude = kwargs.get("exclude") 

        self.get_session_info()

        with open(self.error_log, "a") as file:
            file.write(f"============ Update Session Dates: {datetime.datetime.now()} ============\n")

        for candidate in self.sessions:
            for visit in self.sessions[candidate]:
                if visit not in exclude:
                    scan_done = 'Y' if visit == 'mri_visit' else 'N'
                    subject = self.get_candidate_info(candidate=candidate)['PSCID']
                    visit_date = self.get_session_date(visit=visit, subject=subject)
                    session = self.sessions[candidate][visit]

                    try:
                        sql = f"UPDATE session SET Scan_done = '{scan_done}', Date_visit = '{visit_date}' WHERE ID = '{session}'"
                        self.cursor.execute(sql)
                        print(f"Updated session: subject = {subject}, visit = {visit}")
                    except Exception:
                        self.log_data_transfer_error(table='session', criteria=f"ID {session}, Subject {subject}, visit {visit}")

    def rename_tests(self):
        self.query("test_names", "ID, Test_name, Full_name", "ID")
        for row in self.result:
            id = row["ID"]
            full_name = row["Full_name"].replace("_", " ").title()
            sql = f"UPDATE test_names SET Full_name = '{full_name}' WHERE ID = '{id}'"
            self.cursor.execute(sql)