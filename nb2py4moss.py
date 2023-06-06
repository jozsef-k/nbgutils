"""
+----------------------------------------------------------------------------------------------------------------------+
nb2py4moss.py
=============
In order to effectively check student submissions for plagiarism, this script harvests the source code cells content
of the Jupyter notebooks submitted by students and creates a .py version of the submission. The script is intended for
use in the nbgrader environment. Cells that are "locked" in nbgrader are not harvested, which helps with narrowing the
focus on the content created by the students. The script also pre-processes the assignment skeleton in a similar way.
The prepared files are then uploaded to Stanford's MOSS software similarity checker , which generates an HTML report.
The assignment skeleton file is also taken into account as a base file by MOSS - those code blocks are ignored.
The script optionally downloads the report and the belonging difference files to the local filesystem.

The script assumes an nbgrader environment and requires a MOSS user ID. The pre-processed files are saved as
<course_dir>/moss/<student_id>/<assignment_id>/<assignment_py>

Usage:
- place this script in the nbgrader course root directory,
- start the script with:    python3 nb2py4moss.py <assignment_id> <moss_user_id>

(...use -h for help if you wish to specify further parameters or change the defaults)

Author: Jozsef KOVACS
Created: 03/04/2023
+----------------------------------------------------------------------------------------------------------------------+
"""
import json
from pathlib import Path
import mosspy

MOSS_LANG = "python"


def harvest_source_for_moss(nbfile, pyfile):
    """ copies relevant Jupyter notebook cells to a plain python script """

    with open(nbfile) as nb, open(pyfile, 'w') as py:
        json_data = json.load(nb)
        cnt = 1
        for d in json_data['cells']:
            copy_source = False
            if d['cell_type'] != 'code' or 'source' not in d: continue       # only harvest code cells

            try:
                copy_source = not d['metadata']['nbgrader']['locked']       # copy for moss if unlocked (exp.solution)
            except:
                copy_source = True         # missing nbgrader metadata - probably added by student, copy it for moss

            if copy_source:
                py.writelines(f"\n\n# {pyfile}-«c:{cnt}»-\n")   # cell separator line
                py.writelines(d['source'])                      # source from notebook cell
                py.writelines("\n\n\n\n")                       # separation from next code snippet
                cnt += 1


def process_submissions(args):
    """ process submitted notebooks for the specified assignment & check with MOSS """

    # the root dir of the nbgrader course
    course_path = Path(args.course_dir)

    # setup MOSS configuration
    mp = mosspy.Moss(args.moss_user_id, MOSS_LANG)
    mp.setIgnoreLimit(args.ignore_limit)
    mp.setNumberOfMatchingFiles(args.nr_matching_files)

    # prepare basefile for MOSS - notebook skeleton released to students
    # (to be able to ignore code blocks present in the skeleton)
    basefile_path = course_path / "release" / args.assignment_id
    output_path = course_path / "moss" / "basefile" / args.assignment_id
    basefile = next(basefile_path.glob("*.ipynb"))
    output_path.mkdir(parents=True, exist_ok=True)
    basefile_out = output_path / f"{basefile.parts[-1].split('.')[0]}.py"
    print(f"...harvesting source and adding to MOSS as basefile: {basefile_out}")
    harvest_source_for_moss(basefile, basefile_out)
    mp.addBaseFile(str(basefile_out))

    # prepare student notebooks for MOSS (saves .py versions under moss directory)
    submitted_path = course_path / "submitted" 
    for path in submitted_path.rglob(f'**/{args.assignment_id}/*.ipynb'):
        output_path = course_path / "moss" / Path("/".join(path.parts[1:3]))
        output_path.mkdir(parents=True, exist_ok=True)
        output = output_path / f"{path.parts[-1].split('.')[0]}.py"
        print(f"...harvesting source and adding to MOSS as submission: {output}")
        harvest_source_for_moss(path, output)
        mp.addFile(str(output))

    # send to moss and retrieve result URL
    print("...sending to MOSS and retrieving report ")
    url = mp.send(lambda file_path, display_name: print('*', end='', flush=True))
    print("\nMOSS plagiarism check report: " + url)

    # save report
    if args.download:
        report_path = course_path / "moss" / "report" / args.assignment_id
        report_path.mkdir(parents=True, exist_ok=True)
        print("...Downloading MOSS reports and diff results into ", report_path)
        mp.saveWebPage(url, report_path / "report.html")
        mosspy.download_report(url, report_path, connections=8, log_level=20,
                               on_read=lambda url: print('*', end='', flush=True))

    print("\nDone! [ OK ]")


if __name__ == '__main__':
    print("#" * 80)
    print("# Notebook source harvester for MOSS plagiarism check - v1.0")
    print("#" * 80)

    import argparse

    # parse the command line arguments
    parser = argparse.ArgumentParser(description='harvests code cell content of nbgrader Jupyter notebooks for MOSS',
                                     add_help=True)
    parser.add_argument('assignment_id', type=str,
                        help='nbgrader assignment ID (e.g. A1, A2 ...)')
    parser.add_argument('moss_user_id', type=str,
                        help='user ID registered with MOSS plagiarism tool')
    parser.add_argument('-c', '--course_dir', type=str, default='.',
                        help='path to the nbgrader course directory (default: the current working directory)')
    parser.add_argument('-i', '--ignore_limit', type=int, default=3,
                        help='ignores matching passages appearing in more than the specified nr. of submissions')
    parser.add_argument('-n', '--nr_matching_files', type=int, default=100,
                        help='limit of matching file-pairs listed after MOSS checking')
    parser.add_argument('--download', action='store_true', help='downloads the MOSS report and the diff reports')
    args = parser.parse_args()

    process_submissions(args)
