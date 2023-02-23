from redcap_to_loris_class import RedcapToLoris

loris = RedcapToLoris()

# tests = ['srs2_schoolage', 'srs2_preschool', 'srs2_relative_other', 'aq_ages_1215', 'aq_ages_16', 'aq_ages_411', 'cbcl_ages_15_to_5', 'cbcl_ages_6', 'conners_3']
# for i in range(7):
#     for j in range(2):
#         for test in tests:
#             line = { "Test_name": test, 'AgeMinDays': 0, 'AgeMaxDays': 99999, "Active": 'Y', "Stage": 'Visit', "SubprojectID": j + 1, "Visit_label": f"Sibling{i + 1}"}
#             loris.insert('test_battery', line)
# loris.commit()

loris.get_records()

visits = [
    { "label": 'Sibling1', "scan": False, "date_field": 'sib_date', "override": 'sib_1_dob'},
    { "label": 'Sibling2', "scan": False, "date_field": 'sib_date', "override": 'sib_1_dob_2'},
    { "label": 'Sibling3', "scan": False, "date_field": 'sib_date', "override": 'sib_1_dob_3'},
    { "label": 'Sibling4', "scan": False, "date_field": 'sib_date', "override": 'sib_1_dob_4'},
    { "label": 'Sibling5', "scan": False, "date_field": 'sib_date', "override": 'sib_1_dob_5'},
    { "label": 'Sibling6', "scan": False, "date_field": 'sib_date', "override": 'sib_1_dob_6'},
    { "label": 'Sibling7', "scan": False, "date_field": 'sib_date', "override": 'sib_1_dob_7'}
]

def get_subproject_function(subject):
    if "SUB-1" in subject:
        return 1
    elif "SUB-2" in subject:
        return 2
    else:
        print("Invalid Subject ID for get_subproject_function")
        return -1

def handle_subject_ids(subject):
    return subject[:12]

loris.populate_session_table_override(visits=visits, get_subproject_function=get_subproject_function, handle_subject_ids=handle_subject_ids)

tests = {
    "srs2_schoolage": "srs_school_age_dob",
    'srs2_preschool': "dob_srs_presc",
    'srs2_relative_other': "dob_srs_adult_other",
    'aq_ages_1215': "aqt_dob",
    'aq_ages_16': "aqa_dob",
    'aq_ages_411': "aqc_dob",
    'cbcl_ages_15_to_5': "cbcl_1_dob",
    'cbcl_ages_6': "cbcl_dob",
    'conners_3': "con3_p_dob"
}

keys = list(loris.records[0].keys())
multi_selects = []
for key in keys:
    if "___" in key:
        split_key = key.split("___")[0]
        if split_key not in multi_selects:
            multi_selects.append(split_key)

num_flag = loris.query(table="flag", fields=["count(*)"])[0]["count(*)"]
updated_inst = 0
updated_flag = 0
num_error = 0

for record in loris.records:
    if record['sib_1_dob']:
        sibling_records = [subject_record for subject_record in loris.records if record["record_id"] == subject_record["record_id"] and subject_record["redcap_repeat_instrument"] in tests.keys()]
        for sibling_record in sibling_records:
            for visit in visits:
                for test, dob_field in tests.items():
                    if record[visit["override"]] == sibling_record[dob_field] and sibling_record[dob_field] != "":
                        updated_inst, updated_flag, num_error = loris.update_data(handle_subject_ids=handle_subject_ids, record=sibling_record, multi_selects=multi_selects, visit_label=visit["label"], updated_inst=updated_inst, updated_flag=updated_flag, num_error=num_error)

print(f"{int(num_flag/2)} tests in flag. {updated_inst} instrument entries updated. {updated_flag} flag entries updated. {num_error} errors.")

loris.commit()

del loris