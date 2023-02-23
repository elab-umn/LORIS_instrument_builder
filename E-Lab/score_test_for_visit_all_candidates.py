from logging import raiseExceptions
import os
import subprocess
import pandas as pd
import mysql.connector
import re
import argparse

# from db_connect import connect_server, execute_select_commentid

"""
This script calls the score_instrument.php function in LORIS
Since this script can score (1) all instruments (2) all for a single instrument or (3) one instrument for one candidate/visit 
this script acts as a wrapper for looping through a list of participants. 
"""


def connect_server():
    mydb = mysql.connector.connect(
        host="loris.ahc.umn.edu",
        database="icd",
        user="redcap_ro",
        password="2022$RedCap3",
    )
    mycursor = mydb.cursor()
    return mydb, mycursor


def execute_select(mydb, mycursor, statement):
    # Init
    comment = ""
    # Check if statement is a select statement
    if not statement.startswith("SELECT"):
        comment = 'statement does not start with "SELECT"'
    # Check if single statement
    elif len(re.findall(";", statement)) > 1:
        comment = "Too many statements"
    else:
        try:
            # mycursor.execute(statement)
            # myresult = mycursor.fetchall()
            # myresult = mycursor.fetchone()

            # Read into pandas df instead of local python list
            myresult = pd.read_sql(sql=statement, con=mydb)
            if len(myresult) >= 1:
                comment = "SUCCESS:: results found"
            elif len(myresult) == 0:
                comment = "NONE:: no results found"
            else:
                comment = "ERROR:: else, returned sql value invalid"
                raise Exception(comment)
        except mysql.connector.errors.DataError:
            comment = "ERROR:: statement-failed"
        except mysql.connector.errors.ProgrammingError:
            comment = "ERROR:: statement-failed"
        finally:
            if "myresult" in locals():
                return myresult, comment
            else:
                return 0, comment


def get_list_candidateID_sessionID_for_visit(visit_label):
    # initiate database connection
    db, dbcursor = connect_server()

    # get statement for visit_label
    # NOTE: we name columns here in sql statement, which move to pandas
    statement = 'SELECT sess.CandID AS candidateID, sess.ID AS sessionID, sess.Visit_label AS visitLabel FROM session AS sess WHERE Visit_label = "{visit}";'.format(
        visit=visit_label
    )

    # execute statement
    myresult, comment = execute_select(db, dbcursor, statement)

    if myresult.empty:
        raise Exception("null result from SELECT query; ERROR: ")
    else:
        print("List pulled from DB ===== {comment}".format(comment=comment))
        # print(myresult)
        return myresult


def score_one_test_for_one_candidate_visit(test_i, candidateID_i, sessionID_i):
    try:
        # subprocess.run(
        #     "php /swadm/var/www/elab-loris/tools/data_integrity/score_instrument.php {test} one {candidateID} {sessionID}".format(
        #         test=test_i, candidateID=candidateID_i, sessionID=sessionID_i
        #     ),
        #     check=True,
        # )
        process = subprocess.Popen(
            # ["php", "/swadm/var/www/elab-loris/tools/data_integrity/score_instrument.php", test_i, "one", candidateID_i, sessionID_i]
            # "php /swadm/var/www/elab-loris/tools/data_integrity/score_instrument.php {test} one {candidateID} {sessionID}".format(
            "php ../data_integrity/score_instrument.php {test} one {candidateID} {sessionID}".format(
                test=test_i, candidateID=candidateID_i, sessionID=sessionID_i
            ),
            shell=True, 
            stdout=subprocess.PIPE
        )
        response = process.stdout.read()
        print(response)

    except subprocess.CalledProcessError:
        print("command does not exist")
    # os.system(
    #     "php /swadm/var/www/elab-loris/tools/data_integrity/score_instrument.php {test} one {candidateID} {sessionID}".format(
    #         test=test_i, candidateID=candidateID_i, sessionID=sessionID_i
    #     )
    # )


def score_test_for_candidate_list(test, candidate_list):

    for i, x in candidate_list.iterrows():
        print(
            "====> Scoring instrument {test} ({i} of {N}): for \tCandidateID {candidateID}\tsessionID {sessionID}".format(
                test=test,
                i="{:4}".format(i + 1),
                N="{:4}".format(len(candidate_list)),
                candidateID=x["candidateID"],
                sessionID=x["sessionID"],
            )
        )
        score_one_test_for_one_candidate_visit(test, x["candidateID"], x["sessionID"])


# def run_test(test, visit):
#     mylist = get_list_candidateID_sessionID_for_visit(visit)
#     score_test_for_candidate_list(test, mylist)
#     return 0


def get_visit_list_and_score_test(visit, test):
    mylist = get_list_candidateID_sessionID_for_visit(visit)
    score_test_for_candidate_list(test, mylist)


if __name__ == "__main__":
    # main - argparse indicating which function to run and filepath and instrument template to use
    parser = argparse.ArgumentParser(
        description='Run LORIS "score_instrument.php" for a list of candidates for the specified test and visit'
    )
    parser.add_argument(
        "-t",
        "--test",
        dest="test",
        type=str,
        help="name of instrument or test to score",
        required=True,
    )
    parser.add_argument(
        "-v",
        "--visit",
        dest="visit",
        type=str,
        help="name of visit you want to score",
        required=True,
    )
    args = parser.parse_args()

    # if args.test.isalnum() and args.visit.isalnum():
    if re.match(r"^[A-Za-z0-9_]+$", args.test) and re.match(
        r"^[A-Za-z0-9_]+$", args.visit
    ):
        get_visit_list_and_score_test(args.visit, args.test)
    else:
        raise Exception(
            "specify the test and visit like:\n\n\tpython score_test_for_visit_all_candidates.py --test <test_name> --visit <visit_label>\n"
        )

    # if args.fx == 0:
    #     create_review_template(args.filepath, args.instrument)
    # elif args.fx == 1:
    #     template_to_config(args.filepath, args.instrument)
    # elif args.fx == 9:
    #     create_instr_default(args.filepath, args.instrument)
    # else:
    #     raise FunctionNameError("fx (second argument) must be one of the following values\n"
    #                             "0: create template for review\n"
    #                             "1: create config json from reviewed template\n"
    #                             "9: create instrument default from json\n")
