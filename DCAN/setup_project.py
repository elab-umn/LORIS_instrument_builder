from loris_class import Loris

exclude = ['unsecured_email_authorization_form_umn_only', 'unsecured_email_authorization_form_wu_only', 'umn_phone_screen_consent', 'umn_phone_screen_consent_04_04_2022', 'umn_phone_screen_consent_08_09_2022', 'data_collection_info', 'phonescreen', 'teacher_intake_info', 'teacher_survey_cover_page', 'coordinator_customization_for_teacher', 'umn_online_survey_consent', 'umn_online_survey_consent_04_04_2022', 'umn_online_survey_consent_08_09_2022', 'consent_tracker', 'mock_mri_survey', 'vineland_tracker']
exclude_error = ['family_medical_history_questionnaire', 'scapi']
exclude_repeating = ['mri_data_entry_summary']
exclude_all = exclude + exclude_error + exclude_repeating


loris = Loris()

# loris.create_all_instrument_files(exclude=exclude, php=True)
# loris.commit()
# # mysql connector may go out of sync after create_all_instruments. Run it seperately.

# # copy instrument files into the loris instrument directory, then parse them with "find ../project/instruments/*.inc | php lorisform_parser.php" fix errors if present and re-run.
# # after parsing, run the data dictionary generation script tools/exporters/data_dictionary_builder.php

# loris.get_all_form_metadata(exclude=exclude)
# loris.populate_visits()
# loris.commit()
# loris.add_all_sessions()
# loris.commit()
# # before proceeding run the loris script assign_missing_instruments.php

# loris.populate_all_instruments(exclude=exclude_all)
# loris.commit()

loris.update_all_instrument_metadata(exclude=exclude_all)

loris.get_form_event_mappings()
mappings = { "parent": 3, "teac": 4, "child": 5, "clinician": 6 }
loris.update_instrument_subgroups(exclude=exclude_all, mappings=mappings)

# loris.add_repeat_sessions(instrument="mri_data_entry_summary", visit_label="mri_visit", scan_done="Y", skip_first=True, visit_date_field="mri_scan_date")
# loris.populate_repeating_instrument(instrument="mri_data_entry_summary", visit_label="mri_visit", visit_date_field="mri_scan_date")

loris.commit()

del loris