import pandas as pd
from jinja2 import Template
# import os
# import re
# import json
# from datetime import datetime

def generate_insert_sql(table_name, data, output_file=None):
    # Load Jinja2 template
    with open("templates/mysql_INSERT_VALUES.sql.jinja2", 'r') as filein: 
        insert_template_text = filein.read()
    template = Template(insert_template_text, trim_blocks=True, lstrip_blocks=True)
    # Handle empty values in the DataFrame and convert them to NULL
    data = data.where(pd.notna(data), None)
    # Get column names from DataFrame
    columns = data.columns.tolist()
    # Render the template
    # Write to file if output_file is provided
    sql_statement = template.render(table_name=table_name, columns=columns, df=data)
    # Save output if defined
    if output_file:
        with open(output_file, 'w') as file:
            file.write(sql_statement)
        print(f"SQL statement has been written to {output_file}")
    else:
        return sql_statement

