"""
+----------------------------------------------------------------------------------------------------------------------+
moodle2nbg.py
=============
Converts submissions from Moodle directory & naming format to the one expected by nbgrader.
Takes a submissions ZIP archive from moodle as input, and expects prepared nbgrader environment and released assignment
(imported student ids, source and release subdirectories for the given assignment, functioning nbgrader database).
Assumes there is one submission file per participant/student and the student ID included in the filename (kXXXXXXXX).

Usage:
- place this script in the nbgrader course root directory (where typically the gradebook.db is),
- download and place the moodle ZIP into a subdirectory: <course_dir>/moodle/<assignment_id>/<...>.zip
- start the script with:    python3 moodle2nbg.py <assignment_id>

(...or alternatively, specify custom command line arguments, use -h for help)

Author: Jozsef KOVACS
Created: 31/03/2023
+----------------------------------------------------------------------------------------------------------------------+
"""
from zipfile import ZipFile
from pathlib import Path
import re
import sqlite3
from nbgrader.api import Gradebook
import nbgrader.api
import click

PARTICIPANT_REGEX = 'Participant_([0-9]+)_'
STUDENT_PREFIX = "k"
STUDENT_REGEX = "_" + STUDENT_PREFIX + "([0-9]+)"


def process_moodle_archive(args):
    """ processes Moodle ZIP and extracts submission to nbgrader format, updates participant/student id mapping"""
    with ZipFile(args.moodle_zip) as zipped, sqlite3.connect(args.gradebook) as db_conn,\
        Gradebook("sqlite:///" + args.gradebook) as gb:
        prepare_db(db_conn, args.assignment_id)

        processed = 0
        for info in zipped.infolist():
            # skip entries not matching submission ext.
            if not info.filename.endswith(args.extension):
                continue

            print(f"...processing submission: {info.filename}")
            # retrieve participant ID from directory name
            participant_id = re.search(PARTICIPANT_REGEX, info.filename).group(1)

            # retrieve student ID from submitted file name
            match = re.search(STUDENT_REGEX, info.filename.lower())
            if not match:
                print("ERROR: Submission file naming incorrect: " + info.filename)
                continue
            student_id = f"k{int(str(match.group(1))):08d}"

            # check if student is registered in gradebook (validate inferred student ID)
            try:
                gb.find_student(student_id)
            except nbgrader.api.MissingEntry:
                print("ERROR: Cannot process file, student ID not found in Gradebook: " + info.filename)
                continue

            # create new directory under submitted and extract submission file under expected name
            out_path = Path(args.subdir, student_id, args.assignment_id)
            out_path.mkdir(parents=True, exist_ok=True)
            out_file = Path(out_path, args.nb_file)
            out_file.write_bytes(zipped.read(info))
            db_conn.execute("INSERT INTO moodle_part_student VALUES(?, ?, ?)",
                            (args.assignment_id, student_id, participant_id))
            processed += 1
        print(f"...nr. of submissions processed successfully: {processed}")
        print(f"...exiting... [ OK ]")


def prepare_db(db_conn, assignment_id):
    """ prepare gradebook database for storing the participant number / student ID mapping"""
    try:
        db_conn.execute("CREATE TABLE moodle_part_student(assignment_id, student_id, participant_id)")
    except:
        print('WARN: Moodle participant-student lookup table already exists.')
    db_conn.execute(f"DELETE FROM moodle_part_student where assignment_id = '{assignment_id}'")


def validate_args(args):
    """ validates environment and command line arguments before processing"""

    # check if nbgrader course directory exists
    if not Path(args.course_dir).is_dir():
        raise FileNotFoundError(f"ERROR: The nbgrader course directory ({args.course_dir}) does not exist! ")

    # check if gradebook exists
    if not Path(args.gradebook).is_file():
        raise FileNotFoundError(f"ERROR: The specified gradebook database file ({args.gradebook}) does not exist! ")

    # if moodle ZIP was not specified - take the first matching: moodle/<assignment_id>/*.zip
    if not args.moodle_zip:
        input_path = Path(args.course_dir) / "moodle" / args.assignment_id
        if not Path(input_path).is_dir():
            raise FileNotFoundError(f"ERROR: Moodle ZIP not specified and directory does not exist: {input_path}")

        try:
            args.moodle_zip = next(input_path.glob("*.zip"))
        except Exception:
            raise ValueError(f"ERROR: There is no Moodle ZIP file in directory: {input_path}")

    # check if ZIP exists
    if not Path(args.moodle_zip).is_file():
        raise FileNotFoundError(f"ERROR: The specified Moodle ZIP archive ({args.moodle_zip}) does not exist! ")

    # check if ZIP can be read and number of submissions
    try:
        with ZipFile(args.moodle_zip) as zipfile:
            nr_files = sum([f.filename.endswith(args.extension) for f in zipfile.infolist()])
    except Exception:
        print("ERROR: unable to read the Moodle ZIP archive.")
        raise

    if nr_files == 0:
        raise ValueError(f"The specified Moodle ZIP archive does not contain files with extension {args.extension}")

    # try to open gradebook and check if the specified assignment exists
    args.nb_file = None
    try:
        with Gradebook("sqlite:///" + args.gradebook) as gb:
            assgn = gb.find_assignment(args.assignment_id)
            args.nb_file = assgn.notebooks[0].name + args.extension
    except nbgrader.api.MissingEntry:
        print(f"ERROR: The specified assignment: {args.assignment_id} does not exist in the gradebook!")
        raise
    except Exception:
        print(f"ERROR: cannot open {args.gradebook} as a gradebook database!")
        raise

    # try to create "submitted" folder
    try:
        subdir = Path(args.course_dir) / "submitted"
        subdir.mkdir(parents=False, exist_ok=True)
        args.subdir = subdir.__str__()
    except Exception:
        print(f"ERROR: unable to create the output directory: {subdir}")
        raise

    # check if source and released notebook files exist
    nb_path = Path(args.course_dir) / 'source' / args.assignment_id / args.nb_file
    if not nb_path.is_file():
        raise FileNotFoundError(f"ERROR: Unable to find the source notebook: {nb_path}")
    rel_path = Path(args.course_dir) / 'release' / args.assignment_id / args.nb_file
    if not rel_path.is_file():
        raise FileNotFoundError(f"ERROR: Unable to find the released notebook: {rel_path}")

    print("The environment and provided arguments are valid [ OK ]")
    print(f"... course directory:    {args.course_dir}")
    print(f"... gradebook db:        {args.gradebook}")
    print(f"... assignment ID:       {args.assignment_id}")
    print(f"... notebook filename:   {args.nb_file}")
    print(f"... Moodle ZIP archive:  {args.moodle_zip}")
    print(f"... nr. of submissions:  {nr_files}")
    print(f"... target directory:    {args.subdir}")


if __name__ == '__main__':
    print("#" * 80)
    print("# Moodle-to-nbgrader utility - v1.0")
    print("#" * 80)

    import argparse
    # parse the command line arguments
    parser = argparse.ArgumentParser(description='Converts directory structure and filenames to nbgrader format',
                                     add_help=True)
    parser.add_argument('assignment_id', type=str,
                        help='nbgrader assignment ID (e.g. A1, A2 ...)')
    parser.add_argument('-m', '--moodle_zip', type=str, default=None,
                        help='Moodle ZIP archive containing the submissions (default: <course_dir>/moodle/<assignment_id>/*.zip)')
    parser.add_argument('-d', '--course_dir', type=str, default='.',
                        help='path to the nbgrader course directory (default: the current working directory)')
    parser.add_argument('-g', '--gradebook', type=str, default='gradebook.db',
                        help='path and filename of the gradebook database (default: gradebook.db in current dir)')
    parser.add_argument('-x', '--extension', type=str, default='.ipynb',
                        help='the expected extension of the submitted file (default: Jupyter notebook - ".ipynb"')

    args = parser.parse_args()

    try:
        validate_args(args)
    except Exception as ex:
        print("\nAborting script - error during argument & environment validation: ", ex)
        exit(1)

    if not click.confirm("\nDo you wish to continue with these settings?", default=False):
        print("Execution cancelled.")
        exit(2)

    process_moodle_archive(args)



