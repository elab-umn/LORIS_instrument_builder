import mysql.connector
import configparser
import re


def connect_to_database(database: str = "redcap", dbconfig = "db_config.ini"):
    """connect_to_database standardizes connections to all the various databases that may be used in different python scripts.

    Args:
        db (str, optional): Name of database to connect to.
            Options are ["redcap", "prod", "dev"] which will be lowered and stripped to match.
            Default = "redcap".

    Raises:
        ValueError: Invalid DB connection
        FileNotFoundError: db_config.ini file not found.
        RuntimeError: db_config.ini file doesn't contain information for selected db connection parameters

    Returns:
        cnx: mysql.connector db connection object
        cursor: cnx.cursor() for the return db object
    """
    # standardize input to lowered/stripped value and confirm it matches value
    db = str(database).lower().strip()
    ## CUSTOMIZATION: edit available dbs to connect to
    db_types = ["redcap", "prod", "dev"]
    if db not in db_types:
        raise ValueError(f"Invalid DB connection for '{db}'. Expected one of {db_types}")

    # Read config file for database connections
    config = configparser.ConfigParser()
    try:
        with open(dbconfig) as f:
            config.read_file(f)
    except IOError:
        raise FileNotFoundError(
            "database config file ({dbconfig}) not found. Check script directory or path to {dbconfig}"
        )

    # check config information is available, and connect to the databse selected
    if config.has_section(db):
        try:
            # connect to database
            cnx = mysql.connector.connect(
                host=config.get(db, "host"),
                database=config.get(db, "database"),
                user=config.get(db, "username"),
                password=config.get(db, "password"),
            )
            # save cursor to database
            cursor = cnx.cursor()
            return cnx, cursor
        except mysql.connector.Error as err:
            # handle errors in from the mysql.connector for username/password/db/etc
            # other mysql.connector.errorcodes outlined here: https://github.com/mysql/mysql-connector-python/blob/master/lib/mysqlx/errorcode.py
            if err.errno == mysql.connector.errorcode.ER_ACCESS_DENIED_ERROR:
                raise RuntimeError("mysql.connector.error -- Something is wrong with your user name or password")
            elif err.errno == mysql.connector.errorcode.ER_BAD_DB_ERROR:
                raise RuntimeError("mysql.connector.error -- Database does not exist")
            else:
                raise RuntimeError("mysql.connector.error -- " + err)

    else:
        # failsafe is config doesn't have expecated connection information
        raise RuntimeError("CONFIG ERROR -- Something went wrong. DB connection not found in {dbconfig} file.")


def execute_select_commentid(mydb, mycursor, statement):
    # Init
    commentid_found = ""
    # Check if statement is a select statement
    if not statement.startswith("SELECT"):
        commentid_found = ""
        errormsg = "statement does not start with \"SELECT\""
    # Check if single statement
    elif len(re.findall(";", statement)) > 1:
        commentid_found = ""
        errormsg = "Too many statement"
    else:
        try:
            mycursor.execute(statement)
            myresult = mycursor.fetchall()
            # myresult = mycursor.fetchone()
            if len(myresult) > 1:
                commentid_found = "m"
            elif len(myresult) == 1:
                commentid_found = "y"
            elif len(myresult) == 0:
                commentid_found = "n"
            else:
                commentid_found = "else"
                errormsg = "returned sql value invalid"
        except mysql.connector.errors.DataError:
            commentid_found = "statement-failed"
        except mysql.connector.errors.ProgrammingError:
            commentid_found = "statement-failed"

    return commentid_found, myresult