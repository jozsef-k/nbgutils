"""
+----------------------------------------------------------------------------------------------------------------------+
mstudent_import.py
----------
As a preparation step to using nbgrader with Moodle this utility imports student information exported from Moodle into
the nbgrader gradebook database. The import is using create_or_update logic - so existing students are updated.
- exporting student data from Moodle: Participants / select all / With selected: "download table data as CSV"
- student ID is converted to alphanumeric JKU format: "k" + 8-digit numeric ID with leading zeros

Author: Jozsef KOVACS
Created: 31/03/2023
+----------------------------------------------------------------------------------------------------------------------+
"""
import csv
import argparse
from pathlib import Path
from nbgrader.api import Gradebook
from tqdm import tqdm


def process_participant_csv(args):
    """ process moodle student csv, import data to gradebook """
    print(f"...importing/updating student data into nbgrader database: {args.gradebook}")
    with open(args.moodle_csv, 'r', newline='') as in_csv, Gradebook("sqlite:///" + args.gradebook) as gb:
        reader = csv.reader(in_csv, delimiter=',', quotechar='"')
        for i, row in tqdm(enumerate(reader), desc='students'):
            if i == 0: continue
            firstname, surname, student_id, email = row
            student_id = f"k{int(student_id):08d}"
            gb.update_or_create_student(student_id, first_name=firstname, last_name=surname, email=email)
    print(f"...exiting... [ OK ]")


if __name__ == '__main__':
    print("#" * 80)
    print("# mstudent_import.py - Moodle student data import to nbgrader - v1.0")
    print("#" * 80)

    parser = argparse.ArgumentParser(description='Given a Moodle participant list, imports student data to nbgrader',
                                     add_help=True)
    parser.add_argument('moodle_csv', type=str,
                        help='Moodle student participants CSV file (courseid_XXXXX_participants.csv)')
    parser.add_argument('-g', '--gradebook', type=str, default='gradebook.db',
                        help='gradebook database of the nbgrader environment (default: gradebook.db in current dir)')
    args = parser.parse_args()

    # check if moodle csv exists
    if not Path(args.moodle_csv).is_file():
        raise FileNotFoundError(f"ERROR: The specified Moodle participants CSV does not exist: ({args.moodle_csv})")

    # check if gradebook exists and can be opened
    if not Path(args.gradebook).is_file():
        raise FileNotFoundError(f"ERROR: The specified gradebook database file ({args.gradebook}) does not exist! ")

    process_participant_csv(args)
