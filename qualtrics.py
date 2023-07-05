import os
import re
import requests
import argparse
import configparser
import json

# from redcap_config import token, api_route
# import pandas as pd

# ============================================================================ #
#             for testing and quick access to qualtrics json format            #
# ============================================================================ #
def get_list_keys(dict1):
    return [x for x in dict1.keys()]


def print_json_string(jsonstring, indent=1):
    print(json.dumps(jsonstring, indent=indent))


def get_question_types(surveydata):
    return {x: surveydata["result"]["Questions"][x]["QuestionType"] for x in surveydata["result"]["Questions"].keys()}


def get_question_tags(surveydata):
    return {x: surveydata["result"]["Questions"][x]["DataExportTag"] for x in surveydata["result"]["Questions"].keys()}


# ============================================================================ #
#                              parse question data                             #
# ============================================================================ #
htmlcleaner = re.compile("<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});")


def get_TE_question_data(questiondata):
    # Text Entry question data.
    questionid = questiondata["QuestionID"]
    questiontag = questiondata["DataExportTag"]
    questiontext = re.sub(htmlcleaner, "", questiondata["QuestionText"])
    questiontype = questiondata["QuestionType"]
    questionselector = questiondata["Selector"]
    questioninfo = {}
    questioninfo[questionid] = {
        "ID": questionid,
        "Tag": questiontag,
        "QuestionType": questiontype,
        "QuestionText": questiontext,
        "Selector": questionselector,
        "Answers": None,
    }
    return questioninfo


def get_MC_question_data(questiondata):
    # details on MC questions here: https://www.qualtrics.com/support/survey-platform/survey-module/editing-questions/question-types-guide/standard-content/multiple-choice/?parent=p001132

    questionid = questiondata["QuestionID"]
    questiontag = questiondata["DataExportTag"]
    questiontype = questiondata["QuestionType"]
    questiontext = re.sub(htmlcleaner, "", questiondata["QuestionText"])
    questionselector = f'{questiondata["Selector"]}_{questiondata["SubSelector"]}'
    questioninfo = {}
    if questiondata["Selector"] == "SAVR" and questiondata["SubSelector"] == "TX":
        answers = {x: questiondata["Choices"][str(x)]["Display"] for x in questiondata["ChoiceOrder"]}
        questioninfo[questionid] = {
            "ID": questionid,
            "Tag": questiontag,
            "QuestionType": questiontype,
            "QuestionText": questiontext,
            "Selector": questionselector,
            "Answers": answers,
        }
        # for answers that might have text entry included, as in selecting "Other: "
        for x in questiondata["ChoiceOrder"]:
            if "TextEntry" in questiondata["Choices"][str(x)].keys():
                questioninfo[f"{questionid}_{x}_TEXT"] = {
                    "ID": f"{questionid}_{x}_TEXT",
                    "Tag": f"{questiontag}_{x}_TEXT",
                    "ParentID": questionid,
                    "QuestionType": "TE",
                    "QuestionText": f'{questiontext} - {re.sub(htmlcleaner, "", questiondata["Choices"][str(x)]["Display"])} - Text',
                    "Selector": "SL",
                    "Answers": None,
                }
    # if questiondata["Selector"] == 'MAVR' and questiondata["SubSelector"] == 'TX':

    return questioninfo


def get_Matrix_question_data(questiondata):
    # details on qualtrics matrix question type here: https://www.qualtrics.com/support/survey-platform/survey-module/editing-questions/question-types-guide/standard-content/matrix-table/
    # ------------------------------ selector types ------------------------------ #
    # Single Answer Likert Matrix Table:: For single answer variations of the likert matrix table, where a participant can choose 1 answer per statement on your matrix table, you’ll find 1 column in your dataset for each statement in your matrix table. Generally, each matrix table statement get its own separate column of data. Each column has a header in the format “Question Text – Statement Text” to clarify what specific matrix table and what statement it’s referring to.
    # Multi-Answer Likert Matrix Table:: For multiple answer variations, it depends on whether you chose to split multi-value fields into columns.
    #     If you did not (which is the default), each statement gets its own column, and every answer the respondent selected is listed as comma-separated in the same column.
    #     If you did choose to split columns, then each scale point will have its own column in the dataset. On each participant’s row, there will be a “1” or the text of the answer in the columns of the choices they selected.
    # Text Entry Matrix Table:: For this matrix variation, a column will be included in the dataset for each text box in the table. In this column, you’ll see the text each participant typed into the text box. In the example below, the text entry was restricted to Numeric Content Type, and so the export displays the numbers the respondents typed into the text boxes.
    #     Each column is labeled according to this numbering scheme: [Question Number]_[Row Number]_[Column Number].
    # Max Diff Matrix Table:: For this matrix variation, you will see a column in the spreadsheet for each item the participant can rate in your MaxDiff table. These columns are sorted so the first column in the dataset refers to the first statement in your matrix table, the second column in the dataset to the second statement in your matrix table, etc.
    #     Depending on whether you exported the data in choice text or numeric format, you will either see:
    #     Choice Text: The level of favorability the respondent selected (e.g., “Favorite” or “Least Favorite”).
    #     Numeric Value: For each row of the matrix table, you’ll see a “1” in the column representing the item listed on the left of the statements, and a “0” in the column representing the item listed on the right of the statements. In the example shown here, “Least Favorite” would be coded a “1” and “Favorite” would be coded as a 0.
    # Constant Sum Matrix Table:: For this matrix variation, the downloaded data file will include 1 column for every text box in the matrix table. The columns are labeled according to this numbering scheme: (question number)_(column number)_(row number). In each cell of those columns will be the number that the respondent typed into the constant sum text box.
    # Bipolar Matrix Table:: For this matrix variation, the downloaded data file will include 1 column for each row in the matrix table. In each cell of those columns will be a number that corresponds to 1 of the radio boxes on that particular row. For more information on the numbers attached to radio boxes in a question, visit our recode values page.
    questionid = questiondata["QuestionID"]
    questiontag = questiondata["DataExportTag"]
    questiontype = questiondata["QuestionType"]
    questiontext = re.sub(htmlcleaner, "", questiondata["QuestionText"])
    questionselector = f'{questiondata["Selector"]}_{questiondata["SubSelector"]}'
    questioninfo = {}
    if questiondata["Selector"] == "Likert" and questiondata["SubSelector"] == "SingleAnswer":
        # subquestionorder = questiondata["ChoiceOrder"]
        subquestions = {
            x: re.sub(htmlcleaner, "", questiondata["Choices"][x]["Display"]) for x in questiondata["Choices"].keys()
        }
        # subquestions = {x:questiondata["Choices"][str(x)]["Display"] for x in questiondata["ChoiceOrder"]}
        # answerorder = questiondata["AnswerOrder"]
        answers = {x: questiondata["Answers"][x]["Display"] for x in questiondata["Answers"].keys()}
        # answers = {x:questiondata["Answers"][str(x)]["Display"] for x in questiondata["AnswerOrder"]}

        for x in subquestions.keys():
            questioninfo[f"{questionid}_{x}"] = {
                "ID": f"{questionid}_{x}",
                "Tag": f"{questiontag}_{x}",
                "ParentID": questionid,
                "ParentText": questiontext,
                "ParentSelector": questionselector,
                "QuestionType": questiontype,
                "QuestionText": subquestions[x],
                "Answers": answers,
            }
            if "TextEntry" in questiondata["Choices"][str(x)].keys():
                questioninfo[f"{questionid}_{x}_TEXT"] = {
                    "ID": f"{questionid}_{x}_TEXT",
                    "Tag": f"{questiontag}_{x}_TEXT",
                    "ParentID": questionid,
                    "ParentText": questiontext,
                    "ParentSelector": questionselector,
                    "QuestionType": "TE",
                    "QuestionText": f'{re.sub(htmlcleaner, "", questiondata["Choices"][str(x)]["Display"])} - Text',
                    "Selector": "SL",
                    "Answers": None,
                }

    if questiondata["Selector"] == "Likert" and questiondata["SubSelector"] == "MultiAnswer":
        # TODO: implement this routine!
        questioninfo = []

    return questioninfo


def get_SBS_question_data(questiondata):
    # details here: https://www.qualtrics.com/support/survey-platform/survey-module/editing-questions/question-types-guide/standard-content/side-by-side/?parent=p001132
    questionid = questiondata["QuestionID"]
    questiontag = questiondata["DataExportTag"]
    questiontype = questiondata["QuestionType"]
    questiontext = re.sub(htmlcleaner, "", questiondata["QuestionText"])
    questionselector = questiondata["Selector"]
    questioninfo = {}
    # loop through each additional question/column to get the subquestions and answer choices
    for x in questiondata["AdditionalQuestions"].keys():
        questioninfo.update(parse_question_data(questiondata["AdditionalQuestions"][str(x)]))
    # loop through the quesitoninfo and add details on the SBS question Text and Selector for the SuperParent.
    for y in questioninfo.keys():
        questioninfo[y].update(
            {
                "SuperParentID": questionid,
                "SuperParentTag": questiontag,
                "SuperParentType": questiontype,
                "SuperParentText": re.sub(htmlcleaner, "", questiontext),
                "SuperParentSelector": questionselector,
            }
        )
    return questioninfo


def parse_question_data(questiondata):
    """Parse individual question data from qualtrics question. This function currently acts as a wrapper around the different question types 
    Currently supports question types [MC, TE, Matrix, and SBS]. Note, unsupported question types are simply printed to terminal as note. 

    Args:
        questiondata (dict): Data from Qualtrics API for a specific question, Q1 = surveydata["result"]["Questions"]["Q1"]

    Returns:
        dict: question data for a input
    """    
    questiontype = questiondata["QuestionType"]
    if questiontype == "MC":
        output = get_MC_question_data(questiondata)
    elif questiontype == "TE":
        output = get_TE_question_data(questiondata)
    elif questiontype == "Matrix":
        output = get_Matrix_question_data(questiondata)
    elif questiontype == "SBS":
        output = get_SBS_question_data(questiondata)
    elif questiontype == "DB": 
        print(
            f"Question {questiondata['QuestionID']} ({questiondata['DataExportTag']}) is a descriptive block (DB), so it is not included. {questiondata['DataExportTag']} has the following description:\n{questiondata['QuestionDescription']}\n"
        )
        output = {}
    else:
        print(
            f"ERROR parsing question {questiondata['QuestionID']} ({questiondata['DataExportTag']}) which has question type {questiondata['QuestionType']}. This question type is incorrect, or not implemented. Returning empty dictionary as result. "
        )
        output = {}
    return output


def parse_questions_from_survey(surveydata):
    """get standardized question data from qualtrics survey response

    Args:
        surveydata (dict): output from qualtrics survey api (func: get_qualtrics_survey_definition)

    Returns:
        dict: standardized question data from survey
    """    
    all_survey_questions = {}
    for x in surveydata["result"]["Questions"].keys():
        # loop through each question and parse the question data
        all_survey_questions.update(parse_question_data(surveydata["result"]["Questions"][x]))
    return all_survey_questions


def remove_trash_questions(blockdata, questiondata):
    """remove trash questions not shown to user from qualtrics output

    Args:
        blockdata (dict): The "result" "Blocks" response type from the qualtrics survey, which describes which blocks are used in the presentation of the survey
        questiondata (dict): The questiondata from parse_questions_from_survey() 

    Returns:
        dict: Essentially just questiondata with the trash questions removed
    """    
    outdata = {}
    trashdata = [
        y["QuestionID"]
        for x in blockdata.keys()
        for y in blockdata[str(x)]["BlockElements"]
        if blockdata[str(x)]["Type"] == "Trash"
    ]

    for x in questiondata.keys():
        # since some questions have multiple questions, we need to filter by parentID or questionID
        compareid = questiondata[x]["ParentID"] if "ParentID" in questiondata[x].keys() else questiondata[x]["ID"]
        if compareid not in trashdata:
            outdata[x] = questiondata[x]

    return outdata


def get_questions_from_survey(surveydata):
    """Get parsed question data in a standardized format from Qualtrics API, only including the questions showed to users

    Args:
        surveydata (dict): survey data pulled from parse_questions_from_survey

    Returns:
        dict : questiondata in standardized format with "trash" questions removed
    """    
    qdata = parse_questions_from_survey(surveydata)
    questiondata = remove_trash_questions(surveydata["result"]["Blocks"], qdata)
    return questiondata


# def convert_name_for_sql(name):


def get_metadata_from_survey(token, datacenter, surveyid):
    """Generates the metadata information from the Qualtrics survey to create the LORIS instrument

    Args:
        token (str): Qualtrics API token 
        datacenter (str): Qualtrics Datacenter
        surveyid (str): Qualtrics survey ID 

    Returns:
        json: json string of the instrument_data 
    """    
    # pull survey question data from API
    surveydata = get_qualtrics_survey_definition(token, datacenter, surveyid)
    # process data into question format that mirrors data output
    parseddata = get_questions_from_survey(surveydata)
    # get question groups
    
    # convert parsed data into the LORIS_instrument_builder instrument template format
    instrument_data = {
        "instrument_name": surveydata["result"]["SurveyName"],
        "instrument_name_sql": surveydata["result"]["SurveyName"].lower(),
        "pages": {},
        "fields": {
            f"field{index + 1}": {
                "field_name_sql": parseddata[key]["Tag"],
                "field_front_text_php": parseddata[key]["QuestionText"].lower(),
                "field_name_external": parseddata[key]["ID"],
                # "field_type_sql": parseddata[key]["QuestionType"], #
                "field_type_sql": field_type_lookup(parseddata[key]),
                "enum_values_sql": (list(parseddata[key]["Answers"].keys()) if parseddata[key]["Answers"] != None else False) if "Answers" in list(parseddata[key].keys()) else False,
                "enum_values_php": ([f'{k} - {parseddata[key]["Answers"][k]}' for k in parseddata[key]["Answers"].keys()] if parseddata[key]["Answers"] != None else False) if "Answers" in list(parseddata[key].keys()) else False,
                "field_include_not_answered": False,
                "field_default_value": False,
                "associated_status_field": False,
                "page_php": 0,
                "hidden_on_php": False,
                "group_php": False,
                "rule_php": False,
                "note_php": False,
            }
            for index, key in enumerate(parseddata)
        },
        "groups": {},
    }
    
    # return json.dumps(instrument_data, indent=4)
    return instrument_data


# ============================================================================ #
#                           API Get Survey Definition                          #
# ============================================================================ #
def qualtrics_api_request(method, baseUrl, headers):
    response = None

    apimethod = str(method).upper().strip()
    method_types = ["GET", "POST", "DELETE"]
    if apimethod not in method_types:
        raise ValueError(f"'{apimethod}' is invalid API method. Expected one of {method_types}")

    try:
        response = requests.request(apimethod, baseUrl, headers=headers)
        response.raise_for_status()  # to catch HTTPError
    except requests.exceptions.Timeout:
        raise TimeoutError(
            f"qualtrics api request failed due to timeout \n\tRequest: {baseUrl}"
        )  # \n\tHeaders: {headers}")
    except requests.exceptions.TooManyRedirects:
        raise RuntimeError(f"URL request was bad. Try updating request. \n\tRequest: {baseUrl}")
    # except requests.exceptions.RequestException as e:
    #     # catastrophic error. bail
    #     raise SystemExit(e)
    except requests.exceptions.HTTPError as err:
        # raise SystemExit(err)
        raise RuntimeError(err)

    return response


def get_qualtrics_survey_definition(token, datacenter, surveyid):
    baseUrl = "https://{0}.qualtrics.com/API/v3/survey-definitions/{1}".format(datacenter, surveyid)
    headers = {"x-api-token": token}

    response = qualtrics_api_request("GET", baseUrl, headers).json()

    # we check if the response is okay, and if it is not, we raise the RuntimeError
    if re.search(pattern="^200\s", string=response["meta"]["httpStatus"]) is None:
        raise RuntimeError(
            f"API request failed: {response['meta']['httpStatus']}, {response['meta']['error']['errorMessage']}"
        )

    return response


# def pull_questions_from_survey_definition(surveydefinitionresponse):
#     '''Uses response from get_survey_definition to pull qualtrics survey information'''
#     htmlcleaner = re.compile('<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});')
#     survey_details = {
#         "Survey Name": surveydefinitionresponse['result']['SurveyName'],
#         "Survey Status": surveydefinitionresponse['result']['SurveyStatus'],
#         "Question Count": surveydefinitionresponse['result']['QuestionCount'],
#         "Question List": list(surveydefinitionresponse['result']['Questions'].keys()),
#         "Question Tag": dict((surveydefinitionresponse['result']['Questions'][q]['QuestionID'],re.sub(htmlcleaner, '', surveydefinitionresponse['result']['Questions'][q]['DataExportTag'])) for q in surveydefinitionresponse['result']['Questions']),
#         "Question Text": dict((surveydefinitionresponse['result']['Questions'][q]['QuestionID'],re.sub(htmlcleaner, '', surveydefinitionresponse['result']['Questions'][q]['QuestionText'])) for q in surveydefinitionresponse['result']['Questions']),
#         "Question Type": dict((surveydefinitionresponse['result']['Questions'][q]['QuestionID'],surveydefinitionresponse['result']['Questions'][q]['QuestionType']) for q in surveydefinitionresponse['result']['Questions']),
#         "Question Answers": dict((surveydefinitionresponse['result']['Questions'][q]['QuestionID'], pull_answers_from_question(surveydefinitionresponse['result']['Questions'][q])) for q in surveydefinitionresponse['result']['Questions'])
#     }
#     return survey_details

# def pull_answers_from_question(surveyquestion):
#     '''Pulls answers for qualtrics questions, of different types'''
#     questiontype = surveyquestion["QuestionType"]
#     answertype = None
#     answerchoices = None
#     answerorder = None

#     if questiontype == "TE": # text entry
#         answertype = "text"
#         answerchoices = "NULL"
#         answerorder = "NULL"
#     elif questiontype == "MC": # multiple choice
#         if surveyquestion["Selector"] in ["SAVR", "SAHR", "SACOL", "DL", "SB"]:  #single answer multiple choice questions
#             # "Single Answer Vertical", "Single Answer Horizontal", "Single Answer Column", "Dropdown List", "Select Box"
#             answertype = "single"
#             answerchoices = {i:surveyquestion["Choices"][i]["Display"] for i in surveyquestion["Choices"].keys()}
#             answerorder = surveyquestion["ChoiceOrder"]
#             # {i:t1['result']['Questions']["QID1713868340"]["Choices"][i]["Display"] for i in t1['result']['Questions']["QID1713868340"]["Choices"].keys()}
#         elif surveyquestion["Selector"] in ["MACOL"]: #assuming multiple answers...
#             answertype = "multiple"
#             answerchoices = {i:surveyquestion["Choices"][i]["Display"] for i in surveyquestion["Choices"].keys()}
#             answerorder = surveyquestion["ChoiceOrder"]
#     elif questiontype == "DB": # descriptive box
#         answertype = "DB-not_implemented"
#     elif questiontype == "Matrix": # matrix
#         answertype = "subquestions"
#         subquestionlist = [f'{surveyquestion["QuestionID"]}_{i}' for i in surveyquestion["ChoiceOrder"]]
#         subquestiontext = {f'{surveyquestion["QuestionID"]}_{i}':surveyquestion["Choices"][i]["Display"] for i in surveyquestion["ChoiceOrder"]}
#         answerchoices = {x:surveyquestion["Answers"][x]["Display"] for x in surveyquestion["Answers"].keys()}
#         answerorder = surveyquestion["AnswerOrder"]
#     elif questiontype == "SBS": # side-by-side
#         answertype = "subquestions"
#         subquestionlist = []
#         subquestiontext = []
#         answerchoices = {}
#         answerorder = []
#         for n in surveyquestion["AdditionalQuestions"].keys():
#             for i in surveyquestion["AdditionalQuestions"][n]["Choices"].keys():
#                 subquestionlist.append(f'{surveyquestion["AdditionalQuestions"][n]["QuestionID"]}_{i}') #add a column for each subquestion
#                 subquestiontext.append(f'{surveyquestion["AdditionalQuestions"][n]["QuestionID"]}_{i}')
#                 answerchoices[f'{surveyquestion["QuestionID"]}#{n}_{i}'] = {x:surveyquestion["AdditionalQuestions"][n]["Answers"][x]["Display"] for x in surveyquestion["AdditionalQuestions"][n]["Answers"].keys() }
#                 answerorder.append(surveyquestion["AdditionalQuestions"][n]["Answers"].keys())
#         # answerchoices = [f"{surveyquestion["QuestionID"]}#{n}_{i}":]
#         # print('')
#     elif questiontype == "DD": #drop down
#         answertype = "DD-not_implemented"
#     return {"AnswerType": answertype, "AnswerChoices": answerchoices, "AnswerOrder": answerorder}


# def get_metadata():
#     """
#     Gets Qualtrics survey metadata from the API. See get_data

#     Returns
#     ----------
#     result: dictionary
#         metadata from the Qualtrics API call
#     """


def field_type_lookup(question):
    """
    parses a single metadata field and maps the Qualtrics data type to a SQL datatype

    Arguments
    ----------
    question: dictionary
        a single field's metadata entry

    Returns
    ----------
    field_type: string
        a SQL data type
    """
    field_type = ""
    # if question["text_validation_type_or_show_slider_number"] == "date_mdy":
    #     field_type = "date"
    # elif question["text_validation_type_or_show_slider_number"] == "integer":
    #     field_type = "int"
    # elif question["text_validation_type_or_show_slider_number"] == "number":
    #     field_type = "varchar(255)"
    # else:
    field_type_lookup = {
        "MC": "enum",
        "TE": "varchar(255)",
        "Matrix": "enum",
        # "SBS": "", 
        # "descriptive": "",
        # "dropdown": "enum",
        # "notes": "text",
        # "calc": "int",
        # "yesno": "enum",
        # "checkbox": "varchar(255)",
    }
    field_type = field_type_lookup[question["QuestionType"]]
    return field_type


# def metadata_to_instrument_json(metadata, form):
#     """
#     parses a single form's metadata and transforms it into the format accepted by the instrument builder.

#     Arguments
#     ----------
#     metadata: dictionary
#         a dictionary where the keys are instrument names and values are field and their metadata
#     form: string
#         the name of a REDCap form

#     Returns
#     ----------
#     instrument_data: dictionary
#         a dictionary that is accepted by the instrument builder
#     """
#     instrument = metadata[form]

#     instrument_data = {
#         "instrument_name": form,
#         "instrument_name_loris": form,
#         "pages": {},
#         "fields": {
#             f"field{index + 1}": {
#                 "field_name_loris": field["field_name"],
#                 "field_front_text_php": field["field_label"],
#                 "field_type_loris": field_type_lookup(field),
#                 "enum_values_loris": make_enum_array(field)[0],
#                 "enum_values_php": make_enum_array(field)[1],
#                 "field_include_not_answered": False,
#                 "field_default_value": False,
#                 "associated_status_field": False,
#                 "page_php": 0,
#                 "hidden_on_php": False,
#                 "group_php": False,
#                 "rule_php": False,
#                 "note_php": False,
#             }
#             for index, field in enumerate(instrument.values())
#         },
#         "groups": {},
#     }

#     # print(json.dumps(instrument_data, indent=4))
#     return instrument_data


def make_enum_array(question):
    """
    parses a single metadata field and if it would be an enum formats the Qualtrics choices

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
    options = question["select_choices_or_calculations"]
    field_type = question["field_type"]

    if field_type_lookup(question) == "enum":
        options_php = []
        options_sql = []
        if field_type == "yesno":
            options_sql = ["0", "1"]
            options_php = ["No", "Yes"]
        else:
            options_sql = [option.split(",")[0] for option in options.split("|")]
            options_php = [option.split(",")[1] for option in options.split("|")]

        return options_sql, options_php
    else:
        return "", ""


def main():
    args = parse_args()
    # path = args.path
    # source = args.source.__str__()

    if args.command != None:
        func = function_map[args.command]
        if args.command in ["survey_definition", "convert_survey"]:
            out = func(args.apitoken, args.datacenter, args.surveyid)
        elif args.command in [
            "get_survey_questions",
            "get_all_survey_questions",
            "get_question_types",
            "get_question_tags",
        ]:
            out = func(get_qualtrics_survey_definition(args.apitoken, args.datacenter, args.surveyid))

        print(out)


#     # Make output directories
#     output_dir = args.output_dir.directory
#     if not os.path.exists(os.path.join(output_dir, "php")):
#         os.makedirs(os.path.join(output_dir, "php"))
#     if not os.path.exists(os.path.join(output_dir, "sql")):
#         os.makedirs(os.path.join(output_dir, "sql"))

#     # Generate instrument(s)
#     if path:
#         print(f"Generating instrument from file: {path}")
#         with open(path) as json_file:
#             instrument_json = json.load(json_file)
#         generate_instrument_from_template(instrument_json, output_dir)
#     elif source:
#         print(f"Generating instruments from '{source}'")
#         if source == "redcap":
#             instruments = all_metadata_to_instrument_jsons()
#             for instrument in instruments:
#                 generate_instrument_from_template(instrument, output_dir)
#     else:
#         print(f"No inputs defined. Please include --path or --source")

function_map = {
    "survey_definition": get_qualtrics_survey_definition,
    "get_survey_questions": get_questions_from_survey,
    "get_all_survey_questions": parse_questions_from_survey,
    "get_question_types": get_question_types,
    "get_question_tags": get_question_tags,
    "convert_survey": get_metadata_from_survey
}


def parse_args():
    parser = argparse.ArgumentParser(
        "qualtrics.py",
        description="Using the qualtrics API, extract survey information and convert data to a format for LORIS_instrument_builder.",
    )

    parser.add_argument(
        "--command",
        choices=function_map,
        default="get_all_survey_questions",
        dest="command",
        help="Call a specific function from qualtrics.py file",
    )
    parser.add_argument("--surveyid", type=str, dest="surveyid", help="Qualtrics survey ID")
    parser.add_argument("--datacenter", type=str, dest="datacenter", help="Qualtrics datacenter")
    parser.add_argument("-t", "--token", "--APItoken", type=str, dest="apitoken", help="Qualtrics API token")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    main()



# python3 qualtrics.py --datacenter ca1 -t yhPQuWuY5BpIDRcNpcYmsclJDiv4M5KehA1ude1y --surveyid SV_b8ThCDyxclPJXiS --command survey_definition



# t1_survey = get_qualtrics_survey_definition("yhPQuWuY5BpIDRcNpcYmsclJDiv4M5KehA1ude1y", "ca1", "SV_b8ThCDyxclPJXiS")
