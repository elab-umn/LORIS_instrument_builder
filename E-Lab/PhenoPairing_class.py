import os
from numpy import mat
import pandas as pd
import openpyxl
import re

# import argparse


class PhenoPairing:
    def __init__(self):
        self.trackingsheetfile = os.path.join(
            "/mnt",
            "box",
            "Phenoscreening",
            "Phenoscreening Identifiable Data",
            "Tracking sheets",
            "Wave4",
            "4.1 Tracking Sheet_AG.xlsx",
        )
        self.trackingsheetnames = {
            "consent": "Consent",
            "demographics": "Demo",
            "vrRSB": "vrRSB",
            "RBS-ECS": "RBS-ECS",
            "MCDI": "MCDI-WG",
            "MCHAT": "M-CHAT",
            "APSI": "APSI",
            "Final": "Final",
        }
        self.qualtricsfiles = {
            # "consent": "Consent",
            "demographics": os.path.join(
                "/home",
                "glick094",
                "WSL_Documents",
                "Q2L_general",
                "conf_pheno2_pheSurvey1",
                "MyQualtricsDownload",
                "101_20221020_pheno_demo.xlsx",
            ),
            "vrRSB": os.path.join(
                "/home",
                "glick094",
                "WSL_Documents",
                "Q2L_general",
                "conf_pheno2_pheSurvey1",
                "MyQualtricsDownload",
                "102_20221020_pheno_vrrsb.xlsx",
            ),
            "RBS-ECS": os.path.join(
                "/home",
                "glick094",
                "WSL_Documents",
                "Q2L_general",
                "conf_pheno2_pheSurvey1",
                "MyQualtricsDownload",
                "103_20221020_pheno_rbsecs.xlsx",
            ),
            "MCDI": os.path.join(
                "/home",
                "glick094",
                "WSL_Documents",
                "Q2L_general",
                "conf_pheno2_pheSurvey1",
                "MyQualtricsDownload",
                "104_20221020_pheno_mcdi_wg.xlsx",
            ),
            "MCHAT": os.path.join(
                "/home",
                "glick094",
                "WSL_Documents",
                "Q2L_general",
                "conf_pheno2_pheSurvey1",
                "MyQualtricsDownload",
                "105_20221020_pheno_mchat.xlsx",
            ),
            "APSI": os.path.join(
                "/home",
                "glick094",
                "WSL_Documents",
                "Q2L_general",
                "conf_pheno2_pheSurvey1",
                "MyQualtricsDownload",
                "106_20221020_pheno_apsi.xlsx",
            ),
            "Final": os.path.join(
                "/home",
                "glick094",
                "WSL_Documents",
                "Q2L_general",
                "conf_pheno2_pheSurvey1",
                "MyQualtricsDownload",
                "107_20221020_pheno_concern.xlsx",
            ),
        }
        self.qualtricsIdFields = {
            "demographics_trackingID": ["Q1", "Q3#1_1", "Q3#2_1", "Q3#3_1"],
            "demographics_Initials": ["Q1"],
            "demographics_DOB": ["Q3#1_1", "Q3#2_1", "Q3#3_1"],
            "demographics_EDC": ["Q3#1_2", "Q3#2_2", "Q3#3_2"],
            "demographics_Sex": ["Q2"],
            "demographics": [
                "trackingID",
                "Initials",
                "DOB_qualtrics",
                "EDC_qualtrics",
                "SexOfChild",
                "Progress",
                "ResponseId",
                "RecordedDate",
                "IPAddress",
            ],
            "vrRSB_trackingID": ["Q1", "Q9#1_1", "Q9#2_1", "Q9#3_1"],
            "vrRSB_Initials": ["Q1"],
            "vrRSB": [
                "trackingID",
                "Initials",
                "Progress",
                "ResponseId",
                "RecordedDate",
                "IPAddress",
            ],
            "vrRSB_trackingID": ["Q1", "Q9#1_1", "Q9#2_1", "Q9#3_1"],
            "vrRSB_Initials": ["Q1"],
            "vrRSB": [
                "trackingID",
                "Initials",
                "Progress",
                "ResponseId",
                "RecordedDate",
                "IPAddress",
            ],
            "RBS-ECS_trackingID": ["Q1", "Q19#1_1", "Q19#2_1", "Q19#3_1"],
            "RBS-ECS_Initials": ["Q1"],
            "RBS-ECS": [
                "trackingID",
                "Initials",
                "Progress",
                "ResponseId",
                "RecordedDate",
                "IPAddress",
            ],
            "MCDI_trackingID": ["Q1", "Q3#1_1", "Q3#2_1", "Q3#3_1"],
            "MCDI_Initials": ["Q1"],
            "MCDI": [
                "trackingID",
                "Initials",
                "Progress",
                "ResponseId",
                "RecordedDate",
                "IPAddress",
            ],
            "MCHAT_trackingID": ["Q7", "Q11#1_1", "Q11#2_1", "Q11#3_1"],
            "MCHAT_Initials": ["Q7"],
            "MCHAT": [
                "trackingID",
                "Initials",
                "Progress",
                "ResponseId",
                "RecordedDate",
                "IPAddress",
            ],
            "APSI_trackingID": ["Q3#", "Q7#1_1", "Q7#2_1", "Q7#3_1"],
            "APSI_Initials": ["Q3#"],
            "APSI": [
                "trackingID",
                "Initials",
                "Progress",
                "ResponseId",
                "RecordedDate",
                "IPAddress",
            ],
            "Final_trackingID": ["Q4", "Q3#1_1", "Q3#2_1", "Q3#3_1"],
            "Final_Initials": ["Q4"],
            "Final": [
                "trackingID",
                "Initials",
                "Progress",
                "ResponseId",
                "RecordedDate",
                "IPAddress",
            ],
        }
        self.matching_errors = {
            ### 100s: SUCCESS but may need additional verification
            101: "101__SUCCESS: Only one qualtrics submission from this trackingID and submission is fully complete.",
            102: "102__VERIFY: More than one fully complete qualtrics submission from this IP Address, but different tracking IDs.",
            ### 200s: Incomplete submissions, but likely no action required?
            201: "201__ERROR: (1) Incomplete submission and (2) qualtrics trackingID does not match any ID in tracking sheet. May be incomplete submission and no action is required.",  # added
            202: "202__ERROR: (1) Incomplete submission (Progress < 100). However, there are other paired entries from this trackingID. May be duplicate/incomplete submission and no action is required.",  # added
            ### 300s: Incomplete submissions, but only entry from candidate.
            301: "301__ERROR: (1) Incomplete submission and (2) only paired entry from this trackingID. Check if this is valid qualtrics submission and if Initials and DOB are correct.",  # added
            ### 400s: Fully complete, but unpaired from tracking sheet
            401: "401__ERROR: (1) Tracking sheet candidate does not match any of the qualtrics trackingIDs. Check initials and DOB are correct on tracking sheet.",  # added
            402: "402__ERROR: (1) Qualtrics trackingID does not match any ID in tracking sheet. Check initials and DOB are correct; find matching candidate from list of candidates flagged with 401__ERROR.",  # added
            ### 500s: Paired, fully complete response, with multiple submissions.
            501: "501__ERROR: (1) Multiple fully complete submissions from this trackingID. Confirm which response to use.",
            502: "502__ERROR: Multiple fully complete submissions from (1) this trackingID and (2) IPAddress. Confirm which response to use.",
        }

    def read_tracking_sheet(self, sheetname):
        return pd.read_excel(
            self.trackingsheetfile,
            sheet_name=self.trackingsheetnames[sheetname],
        )

    def read_qualtrics_data(self, instrumentname):
        return pd.read_excel(
            self.qualtricsfiles[instrumentname],
            header=[0, 1, 2],
        )

    def create_trackingID_from_qualtrics(self, qualtricsdata, testname):
        data = qualtricsdata

        # print(data[["Q1", "Q3#1_1", "Q3#2_1", "Q3#3_1", "Q2"]].head()) #testing demographics
        # print(data[["Q3", "Q7#1_1", "Q7#2_1", "Q7#3_1"]].head()) #testing APSI
        # print(data[["Q3", "Q7#1_1", "Q7#2_1", "Q7#3_1"]].query("pd.to_numeric(Q7#1_1, errors='coerce').isnull()")) #testing APSI
        # print(data[["Q3", "Q7#1_1", "Q7#2_1", "Q7#3_1"]].query("pd.to_numeric(Q7#2_1, errors='coerce').isnull()").head()) #testing APSI
        # print(data[["Q3", "Q7#1_1", "Q7#2_1", "Q7#3_1"]].query("pd.to_numeric(Q7#3_1, errors='coerce').isnull()").head()) #testing APSI
        
        # t1 = data[["Q3#", "Q7#1_1", "Q7#2_1", "Q7#3_1"]]
        # print(t1.columns)
        # t1.columns = ["Q3#", "Q7#1_1", "Q7#2_1", "Q7#3_1"]
        # print(t1[t1.isna().any(axis=1)])
        

        # create tracking ID from DOB and initials
        if testname == "demographics":
            data["trackingID"] = data[self.qualtricsIdFields[testname + "_trackingID"]].apply(
                lambda x: "{initials} {MM:02d}/{DD:02d}/{YYYY:04d}".format(
                    initials=x[0].upper().strip(), MM=x[1], DD=x[2], YYYY=x[3] + 2011
                ),
                axis=1,
            )
            data["Initials"] = data[self.qualtricsIdFields[testname + "_Initials"]].apply(
                lambda x: x[0],
                axis=1,
            )
            data["DOB_qualtrics"] = data[self.qualtricsIdFields[testname + "_DOB"]].apply(
                lambda x: "{YYYY:04d}-{MM:02d}-{DD:02d}".format(MM=x[0], DD=x[1], YYYY=x[2] + 2011),
                axis=1,
            )
            data["EDC_qualtrics"] = data[self.qualtricsIdFields[testname + "_EDC"]].apply(
                lambda x: "{YYYY:04d}-{MM:02d}-{DD:02d}".format(MM=x[0], DD=x[1], YYYY=x[2] + 2011),
                axis=1,
            )
            data["SexOfChild"] = data[self.qualtricsIdFields[testname + "_Sex"]].apply(
                lambda x: "Male" if x[0] == 1 else "Female" if x[0] == 2 else "Other", axis=1
            )
        else:
            # year increment is different from demographics compared to other surveys
            data["trackingID"] = data[self.qualtricsIdFields[testname + "_trackingID"]].apply(
                lambda x: "{initials} {MM:02d}/{DD:02d}/{YYYY:04d}".format(
                    initials=x[0].upper().strip(), MM=x[1], DD=x[2], YYYY=x[3] + 2014
                ),
                axis=1,
            )
            data["Initials"] = data[self.qualtricsIdFields[testname + "_Initials"]].apply(
                lambda x: x[0],
                axis=1,
            )

        return data

    def merge_trackingsheet_and_qualtrics(self, instrumentname):
        tracking_data = self.read_tracking_sheet(instrumentname)
        qualtrics_data = self.read_qualtrics_data(instrumentname)

        # get tracking IDs from qualtrics data
        qualtrics_data = self.create_trackingID_from_qualtrics(qualtrics_data, instrumentname)

        # print(self.qualtricsIdFields[instrumentname])
        # print(qualtrics_data[self.qualtricsIdFields[instrumentname]].head())
        # print(pd.DataFrame(tracking_data.Initials_DOB.unique(), columns=["Initials_DOB"]).head())

        # merge data from set of columns selected for each instrument, and a unique list of trackingIDs from the tracking sheet
        merged_data = qualtrics_data[self.qualtricsIdFields[instrumentname]].merge(
            pd.DataFrame(tracking_data.Initials_DOB.unique(), columns=["Initials_DOB"]),
            left_on="trackingID",
            right_on="Initials_DOB",
            how="outer",
        )

        # standardize column names
        if instrumentname == "demographics":
            merged_data.columns = [
                "trackingID",
                "Initials",
                "DOB_qualtrics",
                "EDC_qualtrics",
                "Sex",
                "Progress",
                "ResponseId",
                "RecordedDate",
                "IPAddress",
                "Initials_DOB_trackingsheet",
            ]
        else:
            merged_data.columns = [
                "trackingID",
                "Initials",
                "Progress",
                "ResponseId",
                "RecordedDate",
                "IPAddress",
                "Initials_DOB_trackingsheet",
            ]

        # add column to indicate the response has been matched from tracking sheet
        merged_data["matched_from_tracking"] = (
            merged_data.trackingID.notnull() & merged_data.Initials_DOB_trackingsheet.notnull()
        )

        return merged_data

    def export_merged_data(self, instrumentname):
        print(f"pull and merge {instrumentname} data ------------")
        data = self.merge_trackingsheet_and_qualtrics(instrumentname)

        print(f"flag {instrumentname} data paired from tracking sheet")
        # handle unpaired data
        data_unpaired = data.query("matched_from_tracking == False").copy()
        data_unpaired.loc[:, "comparison_ids"] = [
            row.trackingID if pd.isnull(row.Initials_DOB_trackingsheet) else row.Initials_DOB_trackingsheet
            for index, row in data_unpaired.iterrows()
        ]
        data_unpaired.loc[:, "FLAG"] = [
            self.matching_errors[401]
            # flag for rows from tracking sheet
            if pd.isnull(row.trackingID) else self.matching_errors[402]
            # flag for 100 completed responses from qualtrics that were unpaired
            if row.Progress == 100 and pd.isnull(row.Initials_DOB_trackingsheet) else self.matching_errors[201]
            # flag for <100 completed reponses from qualtrics that were unpaired
            for index, row in data_unpaired.iterrows()
        ]

        # print unpaired data: # data_unpaired.sort_values(by=["comparison_ids", "trackingID"], axis = 0)

        # handle paired data
        data_paired = data.query("matched_from_tracking == True").copy()
        data_paired["count_duplicate_trackingIDs_allmatched"] = data_paired.groupby("trackingID")[
            "trackingID"
        ].transform(
            "count"
        )  # duplicates based on tracking IDs of all paired responses

        ## Paired but incomplete responses.
        data_paired_incomplete = data_paired.query("Progress < 100").copy()
        data_paired_incomplete.loc[:, "FLAG"] = [
            self.matching_errors[301]
            # flag for <100 completed responses from qualtrics that were paired and were the ONLY response from that trackingID
            if row.count_duplicate_trackingIDs_allmatched == 1 else self.matching_errors[202]
            # flag for <100 completed responses from qualtrics that had multiple responses
            for index, row in data_paired_incomplete.iterrows()
        ]

        ## Paired, 100% complete responses. Check for duplicate entries.
        data_paired_completed = data_paired.query("Progress == 100").copy()
        ### check duplicated fully completed responses
        data_paired_completed["count_duplicate_trackingIDs_completedmatched"] = data_paired_completed.groupby(
            "trackingID"
        )["trackingID"].transform("count")
        data_paired_completed["count_duplicate_IPAddresses_completedmatched"] = data_paired_completed.groupby(
            "IPAddress"
        )["IPAddress"].transform("count")
        data_paired_completed["count_duplicate_IDsIPs_completedmatched"] = data_paired_completed.groupby(
            ["trackingID", "IPAddress"]
        )["IPAddress"].transform("count")

        data_paired_completed.loc[:, "FLAG"] = [
            self.matching_errors[502]
            # flag duplicate respones from the same trackingID and IPAddress
            if row.count_duplicate_IDsIPs_completedmatched > 1 else self.matching_errors[501]
            # flag duplicate responses from the same tracking ID but different IPAddresses
            if row.count_duplicate_IDsIPs_completedmatched == 1 and row.count_duplicate_trackingIDs_completedmatched > 1
            else self.matching_errors[102]
            # flag single response, but matched another submission IP Address.
            if row.count_duplicate_trackingIDs_completedmatched == 1
            and row.count_duplicate_IPAddresses_completedmatched > 1
            else self.matching_errors[101]
            # otherwise they should be fine.
            for index, row in data_paired_completed.iterrows()
        ]


        print(f"saving {instrumentname} data")
        # Set up file to save data to
        savefile = os.path.join(
            "/mnt",
            "box",
            "Phenoscreening",
            "Phenoscreening Identifiable Data",
            "Tracking sheets",
            "Wave4",
            "Qualtrics_Data_Validation",
            f"pheno_wave4.1_qualtrics_mappings_{instrumentname}.xlsx",
        )
        ### writer = pd.ExcelWriter(savefile, engine="openpyxl", engine_kwargs={"options": {"strings_to_formulas": False}})
        writer = pd.ExcelWriter(savefile)

        # NOTE: we use the regex r"^10" in the FLAG field to get all the properly paired completed matches. If error codes change update this pattern.
        if instrumentname == "demographics":
            # Ready to upload, may include some verifies
            data_paired_completed.query("FLAG.str.match('^10')")[
                [
                    "trackingID",
                    "Initials",
                    "DOB_qualtrics",
                    "EDC_qualtrics",
                    "Sex",
                    "IPAddress",
                    "Progress",
                    "RecordedDate",
                    "ResponseId",
                    "matched_from_tracking",
                    "FLAG",
                ]
            ].sort_values(by=["FLAG", "trackingID"], ascending=[False, True], axis=0).to_excel(
                writer, sheet_name="Ready_to_Upload"
            )
            # Fully Complete and Paired, but filter duplicates
            data_paired_completed.query("not FLAG.str.match('^10')")[
                [
                    "trackingID",
                    "Initials",
                    "DOB_qualtrics",
                    "EDC_qualtrics",
                    "Sex",
                    "IPAddress",
                    "Progress",
                    "RecordedDate",
                    "ResponseId",
                    "matched_from_tracking",
                    "FLAG",
                ]
            ].sort_values(by=["FLAG", "trackingID"], ascending=[False, True], axis=0).to_excel(
                writer, sheet_name="DUPLICATES_Complete"
            )
            # Unpaired, may include incomplete
            data_unpaired[
                [
                    "comparison_ids",
                    "Initials",
                    "DOB_qualtrics",
                    "EDC_qualtrics",
                    "Sex",
                    "IPAddress",
                    "Progress",
                    "RecordedDate",
                    "ResponseId",
                    "matched_from_tracking",
                    "FLAG",
                ]
            ].sort_values(by=["FLAG", "comparison_ids"], ascending=[False, True], axis=0).to_excel(
                writer, sheet_name="UNPAIRED_from_tracking"
            )
            # Incomplete and paired (may not need anything)
            data_paired_incomplete[
                [
                    "trackingID",
                    "Initials",
                    "DOB_qualtrics",
                    "EDC_qualtrics",
                    "Sex",
                    "IPAddress",
                    "Progress",
                    "RecordedDate",
                    "ResponseId",
                    "matched_from_tracking",
                    "FLAG",
                ]
            ].sort_values(by=["FLAG", "trackingID"], ascending=[False, True], axis=0).to_excel(
                writer, sheet_name="Incomplete_confirm_NOACTION"
            )
        else:
            # TODO: make this cleaner so that it's not repeated code just for DOB, EDC, and Sex which should be included in demographics to create the candidates for LORIS
            # Ready to upload, may include some verifies
            data_paired_completed.query("FLAG.str.match('^10')")[
                [
                    "trackingID",
                    "Initials",
                    "IPAddress",
                    "Progress",
                    "RecordedDate",
                    "ResponseId",
                    "matched_from_tracking",
                    "FLAG",
                ]
            ].sort_values(by=["FLAG", "trackingID"], ascending=[False, True], axis=0).to_excel(
                writer, sheet_name="Ready_to_Upload"
            )
            # Fully Complete and Paired, but filter duplicates
            data_paired_completed.query("not FLAG.str.match('^10')")[
                [
                    "trackingID",
                    "Initials",
                    "IPAddress",
                    "Progress",
                    "RecordedDate",
                    "ResponseId",
                    "matched_from_tracking",
                    "FLAG",
                ]
            ].sort_values(by=["FLAG", "trackingID"], ascending=[False, True], axis=0).to_excel(
                writer, sheet_name="DUPLICATES_Complete"
            )
            # Unpaired, may include incomplete
            data_unpaired[
                [
                    "comparison_ids",
                    "Initials",
                    "IPAddress",
                    "Progress",
                    "RecordedDate",
                    "ResponseId",
                    "matched_from_tracking",
                    "FLAG",
                ]
            ].sort_values(by=["FLAG", "comparison_ids"], ascending=[False, True], axis=0).to_excel(
                writer, sheet_name="UNPAIRED_from_tracking"
            )
            # Incomplete and paired (may not need anything)
            data_paired_incomplete[
                [
                    "trackingID",
                    "Initials",
                    "IPAddress",
                    "Progress",
                    "RecordedDate",
                    "ResponseId",
                    "matched_from_tracking",
                    "FLAG",
                ]
            ].sort_values(by=["FLAG", "trackingID"], ascending=[False, True], axis=0).to_excel(
                writer, sheet_name="Incomplete_confirm_NOACTION"
            )

        # save file
        writer.save()

        print(f"------------ Matched {instrumentname} data saved in the following file: {savefile} ------------")
        return f"Matched {instrumentname} data saved in the following file: {savefile}"


class PhenoPhilteringQualtrics():
    
    def __init__(self):
        self.lorismatchingsheet = os.path.join(
            "/home",
            "glick094",
            "WSL_Documents",
            "Q2L_general",
            "conf_pheno2_pheSurvey1",
            "pheno_LORIS_Candidate_Matching_20221107_PRIMARY.xlsx",
        )
        
        self.datamatchingsheets = {
            "demographics": os.path.join(
                "/mnt",
                "box",
                "Phenoscreening",
                "Phenoscreening Identifiable Data",
                "Tracking sheets",
                "Wave4",
                "Qualtrics_Data_Validation",
                "pheno_wave4.1_qualtrics_mappings_demographics.xlsx",
            ),
            "vrRSB": os.path.join(
                "/mnt",
                "box",
                "Phenoscreening",
                "Phenoscreening Identifiable Data",
                "Tracking sheets",
                "Wave4",
                "Qualtrics_Data_Validation",
                "pheno_wave4.1_qualtrics_mappings_vrRSB.xlsx",
            ),
            "RBS-ECS": os.path.join(
                "/mnt",
                "box",
                "Phenoscreening",
                "Phenoscreening Identifiable Data",
                "Tracking sheets",
                "Wave4",
                "Qualtrics_Data_Validation",
                "pheno_wave4.1_qualtrics_mappings_RBS-ECS.xlsx",
            ),
            "MCDI": os.path.join(
                "/mnt",
                "box",
                "Phenoscreening",
                "Phenoscreening Identifiable Data",
                "Tracking sheets",
                "Wave4",
                "Qualtrics_Data_Validation",
                "pheno_wave4.1_qualtrics_mappings_MCDI.xlsx",
            ),
            "MCHAT": os.path.join(
                "/mnt",
                "box",
                "Phenoscreening",
                "Phenoscreening Identifiable Data",
                "Tracking sheets",
                "Wave4",
                "Qualtrics_Data_Validation",
                "pheno_wave4.1_qualtrics_mappings_MCHAT.xlsx",
            ),
            "APSI": os.path.join(
                "/mnt",
                "box",
                "Phenoscreening",
                "Phenoscreening Identifiable Data",
                "Tracking sheets",
                "Wave4",
                "Qualtrics_Data_Validation",
                "pheno_wave4.1_qualtrics_mappings_APSI.xlsx",
            ),
            "Final": os.path.join(
                "/mnt",
                "box",
                "Phenoscreening",
                "Phenoscreening Identifiable Data",
                "Tracking sheets",
                "Wave4",
                "Qualtrics_Data_Validation",
                "pheno_wave4.1_qualtrics_mappings_Final.xlsx",
            ), 
        }
        self.qualtricsfiles = {
            "demographics": os.path.join(
                "/home",
                "glick094",
                "WSL_Documents",
                "Q2L_general",
                "conf_pheno2_pheSurvey1",
                "MyQualtricsDownload",
                "101_20221020_pheno_demo.xlsx",
            ),
            "vrRSB": os.path.join(
                "/home",
                "glick094",
                "WSL_Documents",
                "Q2L_general",
                "conf_pheno2_pheSurvey1",
                "MyQualtricsDownload",
                "102_20221020_pheno_vrrsb.xlsx",
            ),
            "RBS-ECS": os.path.join(
                "/home",
                "glick094",
                "WSL_Documents",
                "Q2L_general",
                "conf_pheno2_pheSurvey1",
                "MyQualtricsDownload",
                "103_20221020_pheno_rbsecs.xlsx",
            ),
            "MCDI": os.path.join(
                "/home",
                "glick094",
                "WSL_Documents",
                "Q2L_general",
                "conf_pheno2_pheSurvey1",
                "MyQualtricsDownload",
                "104_20221020_pheno_mcdi_wg.xlsx",
            ),
            "MCHAT": os.path.join(
                "/home",
                "glick094",
                "WSL_Documents",
                "Q2L_general",
                "conf_pheno2_pheSurvey1",
                "MyQualtricsDownload",
                "105_20221020_pheno_mchat.xlsx",
            ),
            "APSI": os.path.join(
                "/home",
                "glick094",
                "WSL_Documents",
                "Q2L_general",
                "conf_pheno2_pheSurvey1",
                "MyQualtricsDownload",
                "106_20221020_pheno_apsi.xlsx",
            ),
            "Final": os.path.join(
                "/home",
                "glick094",
                "WSL_Documents",
                "Q2L_general",
                "conf_pheno2_pheSurvey1",
                "MyQualtricsDownload",
                "107_20221020_pheno_concern.xlsx",
            ), 
        }
        
    def read_datamatching_sheet(self, instrumentname, sheetname="Ready_to_Upload"):
        return pd.read_excel(
            self.datamatchingsheets[instrumentname],
            sheet_name=sheetname,
        )

    def read_qualtrics_data(self, instrumentname):
        return pd.read_excel(
            self.qualtricsfiles[instrumentname],
            header=[0, 1, 2],
        )
    
    def filter_qualtrics_data_ready_to_upload(self, instrumentname, sheetname="Ready_to_Upload"): 
        matching_data = self.read_datamatching_sheet(instrumentname, sheetname=sheetname)
        qualtrics_data = self.read_qualtrics_data(instrumentname)
        
        responseIDs = matching_data.ResponseId
        keeprows = [True if row.ResponseId.isin(responseIDs).any() else False for index, row in qualtrics_data.iterrows()]
        
        filtered = qualtrics_data.iloc[keeprows]
        
        
        savefile = self.qualtricsfiles[instrumentname].replace(".xlsx", f"_{sheetname}.xlsx")
        writer = pd.ExcelWriter(savefile)
        
        filtered.to_excel(writer, sheet_name="Sheet")  #, index=False)
        
        writer.save()
        
        print(f"saving filtered {instrumentname} from sheet {sheetname} in the following location: ")
        return savefile
    
    # def filter_qualtrics_data_confirmed_to_upload(self, instrumentname): 
    #     matching_data = self.read_datamatching_sheet(instrumentname, sheetname="CONFIRMED_Second_Upload")
    #     qualtrics_data = self.read_qualtrics_data(instrumentname)
        
    #     responseIDs = matching_data.ResponseId
    #     keeprows = [True if row.ResponseId.isin(responseIDs).any() else False for index, row in qualtrics_data.iterrows()]
        
    #     filtered = qualtrics_data.iloc[keeprows]
        
        
    #     savefile = self.qualtricsfiles[instrumentname].replace(".xlsx", "_CONFIRMED_Second_UPLOAD.xlsx")
    #     writer = pd.ExcelWriter(savefile)
        
    #     filtered.to_excel(writer, sheet_name="Sheet")
        
    #     writer.save()
        
    #     print(f"saving filtered {instrumentname} in the following location: ")
    #     return savefile
        
        
        # #create trackingID from qualtrics IDs
        # qualtrics_data["trackingID"] = data[self.qualtricsIdFields[testname + "_trackingID"]].apply(
        #         lambda x: "{initials} {MM:02d}/{DD:02d}/{YYYY:04d}".format(
        #             initials=x[0].upper().strip(), MM=x[1], DD=x[2], YYYY=x[3] + 2011
        #         ),
        #         axis=1,
        #     )
