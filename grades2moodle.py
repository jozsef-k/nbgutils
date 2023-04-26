"""
+----------------------------------------------------------------------------------------------------------------------+
grades2moodle.py
================
This script exports the grades and feedback for a given assignment from nbgrader to a Moodle grading worksheet.
This grading approach assumes that participant identities were not revealed, and the nbgrader gradebook.db
contains an auxiliary participant_id-student_id lookup table, which should have been created by moodle2nbg.py
when the submissions were converted to nbgrader format. The result is written back to the Moodle grading worksheet
and will only contain rows for submitted assignments, which were also processed in nbgrader.

Usage:
- place this script in the nbgrader course root directory (where typically the gradebook.db is),
- download the moodle grading worksheet for the given assignment (e.g. into <course_dir>/moodle/grading/<...>.csv)
- start the script with:    python3 grades2moodle.py <assignment_id> <moodle_grading_worksheet>

+----------------------------------------------------------------------------------------------------------------------+
"""

import csv
import argparse
from pathlib import Path
import sqlite3
from tqdm import tqdm
from nbgrader.api import SubmittedAssignment, Gradebook

# query to resolve participant_id based on student_id for a specific assignment
PARTICIPANT_STUDENT_QUERY = """
    select mps.student_id, mps.participant_id
      from moodle_part_student mps
     where mps.assignment_id = ? 
    """

# pattern indicating feedback in html file
HTML_SEARCH_PATTERN = r'AssertionError</span>: ex'
hsp = HTML_SEARCH_PATTERN


class ParticipantGrade():
    """ Participant/student grade information retrieved from nbgrader """
    def __init__(self, participant_id: str, submitted_assignment: SubmittedAssignment):
        self.participant_id = participant_id
        self.student_id = submitted_assignment.student_id
        self.first_name = submitted_assignment.student.first_name
        self.last_name = submitted_assignment.student.last_name
        self.score = submitted_assignment.score
        self.max_score = submitted_assignment.max_score
        self.feedback = ""


def get_participant_lookup(args):
    """ initialises the participant lookup dict for a specific assignment """
    participant_lookup = dict()
    with sqlite3.connect(args.gradebook) as db_conn:
        try:
            cursor = db_conn.cursor()
            cursor.execute(PARTICIPANT_STUDENT_QUERY, (args.assignment_id,))
            result_set = cursor.fetchall()
            for row in result_set:
                student_id, participant_id = row
                participant_lookup[student_id] = participant_id
        except Exception as ex:
            print('ERROR: an error occured during accessing the database/retrieving the grades')
            print(ex)
    return participant_lookup


def retrieve_participant_grades(args):
    """ retrieves the assignment grades (total score) from nbgrader gradebook for participants """
    grade_dict = dict()
    participant_lookup = get_participant_lookup(args)
    with Gradebook("sqlite:///" + args.gradebook) as gb:
        for submitted_assignment in gb.assignment_submissions(args.assignment_id):
            if submitted_assignment.student_id not in participant_lookup:
                print(f"ERROR: student {submitted_assignment.student_id} not in participant lookup table!")
                continue
            participant_id = participant_lookup[submitted_assignment.student_id]
            grade_dict[participant_id] = ParticipantGrade(participant_id, submitted_assignment)

    return grade_dict


def retrieve_participant_feedback(grade_dict, feedback_dir, assignment_id):
    """ updates the ParticipantGrade object with the automated feedback retrieved from nbgrader files  """

    # iterate through ParticipantGrade objects and set feedback
    print(f"...retrieving feedback for participant grades")
    for _, part_grade in grade_dict.items():

        student_id = part_grade.student_id
        html_filepath = feedback_dir / student_id / assignment_id
        
        try:
            html_filepath = next(html_filepath.glob('*.html'))
        except:
            print(f'ERROR: no html feedback file found for student {student_id} and assignment {assignment_id}')
            continue
        
        # optionally - if submission reached max_points, start feedback with "well done :)"
        if part_grade.score == part_grade.max_score:
            part_grade.feedback = 'well done :)\n'
            
        # extract all assertion error messages -> feedback for assignment
        # assumes fixed mode of autograde testing plus no additonal assertion errors created by students
        with open(html_filepath, 'r', encoding='utf-8') as html:
            for line in html:
                if hsp in line:
                    feedback_msg = line[line.find(hsp)+len(hsp)-2:-7] + '\n'
                    part_grade.feedback += feedback_msg     


def export_grades_csv(args):
    """
    Given a Moodle grading worksheet and a participant lookup table
    fills in the grade and feedback information and writes it back to the csv.
    """

    # retrieve participant grades from the database
    print(f"...retrieving participant grades from {args.gradebook}")
    grade_dict = retrieve_participant_grades(args)

    # retrieve participant feedback from feedback HTML files
    feedback_dir = Path(args.course_dir) / 'feedback'
    assignment_id = args.assignment_id
    retrieve_participant_feedback(grade_dict, feedback_dir, assignment_id)

    # process the Moodle grading worksheet
    result_rows = list()
    print(f"...read Moodle grading worksheet and fetch relevant rows {args.moodle_worksheet}")
    with open(args.moodle_worksheet, 'r') as in_csv:
        reader = csv.reader(in_csv, delimiter=',', quotechar='"')
        for i, row in tqdm(enumerate(reader), desc='...processing rows'):
            # header row
            if i == 0:
                result_rows.append(row)
                continue
            # if participant is in nbgrader grade dictionary
            participant_id = row[0].split(' ')[-1]
            if participant_id in grade_dict:
                row[2] = grade_dict[participant_id].score
                row[6] = grade_dict[participant_id].feedback
                result_rows.append(row)

    if not result_rows:
        print('ERROR: There are no participants in the Moodle worksheet matching nbgrader database')
        return

    # write output back to moodle worksheet
    with open(args.moodle_worksheet, 'w') as out_csv:
        csv_writer = csv.writer(out_csv, delimiter=',', quotechar='"')
        for row in result_rows:
            csv_writer.writerow(row)

    print(f"...Done!... [ OK ]")


if __name__ == '__main__':
    print("#" * 80)
    print("# mstudent_import.py - Moodle student data import to nbgrader - v1.0")
    print("#" * 80)

    parser = argparse.ArgumentParser(description='Given a Moodle participant list, imports student data to nbgrader',
                                     add_help=True)
    parser.add_argument('assignment_id', type=str,
                        help='grades will be exported for this assignment')
    parser.add_argument('moodle_worksheet', type=str,
                        help='grading worksheet of the assignment downloaded from Moodle')
    parser.add_argument('-d', '--course_dir', type=str, default='.',
                        help='path to the nbgrader course directory (default: the current working directory)')
    parser.add_argument('-g', '--gradebook', type=str, default='gradebook.db',
                        help='gradebook database of the nbgrader environment (default: gradebook.db in current dir)')
    args = parser.parse_args()

    # check if gradebook exists
    if not Path(args.gradebook).is_file():
        raise FileNotFoundError(f"ERROR: The specified gradebook database file ({args.gradebook}) does not exist! ")

    # check if moodle worksheet exists
    if not Path(args.moodle_worksheet).is_file():
        raise FileNotFoundError(f"ERROR: The specified Moodle grading worksheet ({args.moodle_worksheet}) not found! ")

    export_grades_csv(args)
