import csv, json, os

def convert_csv_to_json(inputfile): 
    """Read csv file, and convert to json string"""
    data = []
    
    i = 0
    with open(inputfile) as f: 
        for row in csv.DictReader(f): 
            data.append(row) 
    
    return json.dumps(data)

json0 = convert_csv_to_json(os.path.join(os.getcwd(),'data','V3CR_153523_20221115214820778_PAIRED_VISITS.csv'))
json.loads(json0)[0]

with open(os.path.join(os.getcwd(),'data','CONFIG_vineland3_table_qglobal_agcc.json')) as f: 
    map0 = json.loads(f.read())

# step 1: pull json for LORIS table

# step 2: add array of import data., example below
# {
#     "Test_name": "vineland3",
#     "Survey Name": "Vineland 3 (VABS-3)", 
#     "External Source": "QGlobal", 
#     "Filters": {
#         "0": {
#             "Field": "PSCID", 
#             "External Field": "ExamineeID", 
#             "Operator": "like"
#         }, 
#         "1": {
#             "Field": "Visit_label", 
#             "External Field": "LastName", 
#             "Operator": "equivalent"
#         }
#     },
#     "Validation": {
#         "scores": [null, 0, 1, 2], 
#         "confidencelevel": [1, 2, 3],
#         "significancelevel": [1, 2, 3]
#     }
# },

# step 3: add the following key pairs to each field in the LORIS table columns: 
# "External Field": null, 
# "External Type": null, 
# "External Conversion": null, 
# "External Validation": null

# step 4: manually add mappings for External Field. If a field remains null, it will not be used. 

def map_data_json_to_loris_json(lorismap, datarow): 
    
    # testname = lorismap[0]['Test_name']
    filters = pull_filters_from_loris_json(lorismap, datarow)
    
    testname = filters["testname"]
    candidatefilter = filters["candidatefilter"] if (filters["candidatefilter"] != None) else " "
    visitfilter = filters["visitfilter"] if (filters["visitfilter"] != None) else " "
    datefilter = filters["datefilter"] if (filters["datefilter"] != None) else " "
    
    # queryCommentID = f"SELECT t.CommentID FROM (SELECT * FROM {testname}) as t WHERE CommentID = (SELECT f.CommentID FROM candidate AS c LEFT JOIN session AS s on c.CandID = s.CandID LEFT JOIN flag AS f on s.ID = f.SessionID WHERE f.CommentID NOT LIKE 'DDE%' AND f.Test_name = '{testname}' {candidatefilter} {visitfilter} {datefilter})"
    # AND c.PSCID like 'AIS1145%'
    # AND s.Visit_label = "agccx12m"
    
    # find the correct Comment ID based on the filters in the CONFIG file
    queryCommentID = (
        "SELECT instrument.CommentID "
        f"FROM {testname} AS instrument "
        "WHERE instrument.CommentID = ( "
        "SELECT f.CommentID "
        "FROM session s "
        "LEFT JOIN candidate c "
        "ON c.CandID = s.CandID "
        "LEFT JOIN flag f "
        "ON s.ID = f.SessionID "
        "WHERE f.CommentID NOT LIKE 'DDE%' "
        f"AND f.Test_name = '{testname}' "
        f"{candidatefilter} " #of the form:  "AND c.PSCID LIKE 'AIS1001%' " or "AND c.CandID = 661098 "
        f"{visitfilter} " #of the form: "AND s.Visit_label LIKE 'agccx12m' "
        f"{datefilter} " #of the form: "AND ABS(DATEDIFF(s.Date_visit, '2021-05-26')) < 40 "
        " ) "
    )
    
    # Update Data_entry to complete and Administration to All
    queryUpdateFlag = (
        "UPDATE flag SET Data_entry = 'Complete', Administration = 'All' "
        f"WHERE test_name = '{testname}' "
        "AND CommentID = 'REPLACE_CommentID' " #this will be replaced in the next routine
        # "AND CommentID = ( "
        # f"{queryCommentID}"
        # " ) "
        # "SELECT f.CommentID "
        # "FROM session s "
        # "LEFT JOIN candidate c "
        # "ON c.CandID = s.CandID "
        # "LEFT JOIN flag f "
        # "ON s.ID = f.SessionID "
        # "WHERE f.CommentID NOT LIKE 'DDE%' "
        # f"AND f.Test_name = '{testname}' "
        # f"{candidatefilter} " #of the form:  "AND c.PSCID LIKE 'AIS1001%' " or "AND c.CandID = 661098 "
        # f"{visitfilter} " #of the form: "AND s.Visit_label LIKE 'agccx12m' "
        # f"{datefilter} " #of the form: "AND ABS(DATEDIFF(s.Date_visit, '2021-05-26')) < 40 "
    )
    
    # loop through loris map and pair data from the data row. 
    datetaken, instrumentdata = get_query_to_populate_instrument_data(lorismap, datarow)
    
    queryUpdateInstrument = (
        f"UPDATE {testname} "
        f"{instrumentdata} " #in the form: SET column1 = 'value1', column2 = 'value2' ...
        "WHERE Date_taken IS NULL " #only update rows with no existing data
        "AND CommentID = 'REPLACE_CommentID' "
    )
    
    return {"Test_name": testname, "Date_taken": datetaken, "queryCommentID": queryCommentID, "queryUpdateFlag": queryUpdateFlag, "queryUpdateInstrument": queryUpdateInstrument}

from datetime import datetime

def get_query_to_populate_instrument_data(lorismap, datarow):
    
    map = lorismap[1:] # drop the first item in list, which is metadata. 
    datetaken = None
    
    # loop through values in data map 
    mappedvalues = "SET Data_entry_completion_status = 'Complete', examiner = 54, "
    for x in map: 
        if x["External Field"] is not None: 
            # TODO: add in data validation and conversion steps here
            xval = datarow[x['External Field']]
            if xval == '': 
                xval = "NULL" if (x["Null"] == "YES") else xval
            elif x['External Conversion'] == "date": 
                xval = f"{datetime.strptime(xval, '%m/%d/%Y'):%Y-%m-%d}"
            mappedvalues = mappedvalues + f"{x['Field']} = '{xval}', "
            if x["Field"] == "Date_taken": 
                datetaken = xval
    
    if mappedvalues[-2:] == ", ": 
        mappedvalues = mappedvalues[:-2] + " "
    
    #TODO: check that this solves the NULL problem. 
    mappedvalues = re.sub("'NULL'", "NULL", mappedvalues) 
    
    return datetaken, mappedvalues

def sql_operator_conversion(operatorword): 
    operator = None
    if operatorword == "like": 
        operator = "LIKE"
    elif operatorword == "not like": 
        operator = "NOT LIKE"
    elif operatorword == "equivalent": 
        operator = "="
    elif operatorword == "not equivalent": 
        operator = "<=>"
    elif operatorword == "less than": 
        operator = "<"
    elif operatorword == "less than or equal": 
        operator = "<="
    elif operatorword == "greater than": 
        operator = ">"
    elif operatorword == "greater than or equal": 
        operator = ">="
    
    return operator 

def pull_filters_from_loris_json(lorismap, datarow): 
    filters = {
        "testname": lorismap[0]['Test_name'],
        "candidatefilter": None,
        "visitfilter": None,
        "datefilter": None,
    }
    
    for x in lorismap[0]['Filters']:
        xval = None
        xval = datarow[x["External Field"]] if (x["Fixed Value"] == None) else x["Fixed Value"]
        operator = sql_operator_conversion(x["Operator"]) 
        
        if x["Field"] == "PSCID" and filters["candidatefilter"] == None:
            filters["candidatefilter"] = f"AND c.PSCID {operator} '{xval}" + ("%'" if str(operator).find("LIKE") != -1 else "'")
        if x["Field"] == "CandID": #this always comes after 
            filters["candidatefilter"] = f"AND c.CandID {operator} '{xval}" + ("%'" if str(operator).find("LIKE") != -1 else "'")
        if x["Field"] == "Visit_label" and filters["visitfilter"] == None:
            filters["visitfilter"] = f"AND s.Visit_label {operator} '{xval}" + ("%'" if str(operator).find("LIKE") != -1 else "'") 
        if x["Field"] == "Date" and filters["datefilter"] == None:
            # FIXME: this is probably wrong
            filters["datefilter"] = f"AND ABS(DATEDIFF(s.Date_visit, '{xval}')) > 40 "
    
    # "return the map replacing all 'None' values with '' empty string for f-string formating"
    # return { k: ('' if v is None else v) for k, v in filters.items() }
    return filters

json0 = convert_csv_to_json(os.path.join(os.getcwd(),'data','V3CR_153523_20221115214820778.csv'))

json.loads(json0)[0]["LastName"]

map0[0]["Filters"]

pull_filters_from_loris_json(map0, json.loads(json0)[0])
test1 = map_data_json_to_loris_json(map0, json.loads(json0)[13])
test00 = map_data_json_to_loris_json(map0, json.loads(json0)[0])

# json.loads(json0)[15]['vi3_rec_']

test1['queryCommentID']
test1['queryUpdateFlag']
test1['queryUpdateInstrument']

test00['queryCommentID']
test00['queryUpdateFlag']
test00['queryUpdateInstrument']

for x in json.loads(json0)[0:3]: 
    print(x["LastName"])

# import multiprocessing
# from functools import partial

# pool0 = multiprocessing.Pool()
# map_partial = map_data_json_to_loris_json, lorismap = map0)
# map_partial = lambda datarow : map_data_json_to_loris_json(map0, datarow)
# pool0.map(lambda datarow : map_data_json_to_loris_json(map0, datarow), json.loads(json0))


# loop through all data rows and get their queries
data_queries = []
for x in json.loads(json0): 
    data_queries.append(map_data_json_to_loris_json(map0, x))
    
data_queries[0:1]

# loop through all the queries. Run the select comment id, which we save a replace. 

data_queries[0]["queryCommentID"]

from db_connect import connect_to_database
from db_connect import execute_select_commentid
import re

# Query Database with select_query_str
db, dbcursor = connect_to_database(database = "redcap")
prod, prodcursor = connect_to_database(database = "prod")



query_results = []
for x in data_queries:
    tmp = x
    #pull the comment ID 
    select_query_result, commentid = execute_select_commentid(db, dbcursor, x["queryCommentID"])
    tmp['CommentID Status'] = select_query_result
    tmp['CommentID'] = commentid[0][0] if tmp['CommentID Status'] == 'y' else '' #returns a list of tuples. CommentID is the first value
    
    #try to update the flag table
    if tmp['CommentID Status'] != 'y': 
        tmp['UpdateFlag Status'] = 'n'
        tmp['UpdateInstrument Status'] = 'n'
    else: 
        # replace queries with the found comment id
        tmp['queryUpdateFlag'] = re.sub(r'REPLACE_CommentID', tmp["CommentID"], x['queryUpdateFlag'])
        tmp['UpdateFlag Status'] = ''
        tmp['queryUpdateInstrument'] = re.sub(r'REPLACE_CommentID', tmp["CommentID"], x['queryUpdateInstrument'])
        tmp['UpdateInstrument Status'] = ''
        # TODO: add routines to actually update prod here. 
        # Use transactions so we can rollback if necessary
        
    query_results.append(tmp)

        # print_line = "\t".join(
        #     ["", row_id, date_taken, select_query_str, select_query_result, update_flag_str, "", update_inst_str])

query_results[0].keys()
headers = ['Test_name', 'Date_taken', 'queryCommentID', 'CommentID Status', 'CommentID', 'queryUpdateFlag', 'UpdateFlag Status', 'queryUpdateInstrument', 'UpdateInstrument Status']

with open("vineland_transfer_tracker_2022-11-22.tsv", 'a') as output_file: 
    dict_writer = csv.DictWriter(output_file, headers, delimiter='\t')
    dict_writer.writeheader()
    dict_writer.writerows(sorted(query_results, key = lambda x: x["CommentID Status"], reverse=True))
    
# CHECK?: NULLS need to be NULL not 'NULL' dodo
# TODO: the percentile ranks had <1, which threw an INT error. I need to make a note in the instrument file/data export that 0 == <1 since you can't be the zeroth percentile. 