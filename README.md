# nbgutils  
Utility scripts and tools to support autograding of [moodle](https://moodle.org/) assignments with [nbgrader](https://nbgrader.readthedocs.io/en/stable/):
- importing moodle student information to nbgrader
- converting moodle submission archive to nbgrader directory and naming structure
- plagiarism checking on submitted Jupyter notebooks with MOSS
- exporting grades for uploading back to moodle.

---
## Environment
The scripts require an initialised nbgrader course directory with the usual
subdirectory structure and a gradebook database:
```
<nbg_course_dir>  
+-- source  
+-- release  
+-- submitted  
+-- autograded   
+-- feedback  
+-- gradebook.db
```
## Initialisation - import student information
```mstudent_import.py```  
As a preparation step to using nbgrader with Moodle this utility imports student information exported from Moodle into
the nbgrader gradebook database. The import is using create_or_update logic - so existing students are updated.
Typically, this needs to be executed once for the course, after student registrations have been completed. 
However, it can be run also as an update script during the course (late registrations, changes etc.).   
The Moodle numeric student IDs are converted to <*prefix*> + <*n-digit with leading zeros*> format
(eg. "k00987654"), optionally.

Usage:
1. Export student data from Moodle: 
   - go to **Participants** in the navigator,
   - select all with role **Student**,
   - use the **With selected** action at the bottom **Download table data as CSV**
2. Place the mstudent_import.py script and the downloaded CSV in the course directory
and start the script:  
```python3 mstudent_import.py <moodle_participant_csv>``` 
 
## Convert submissions from Moodle to nbgrader 
```moodle2nbg.py```  
Converts submissions from the Moodle directory and naming format to the one expected by nbgrader.
Takes a submissions ZIP archive downloaded from moodle as input and expects a prepared nbgrader environment 
(the assignment has been registered, the source notebook created and released).  

The script assumes a Moodle assignment setup with:
- identities not yet revealed in Moodle at the time of downloading the ZIP archive (Participant_XXXXXXXX folders),
- one submission notebook per participant with the student ID included in the filename (eg. A1_k00987654.ipynb).   

The script will verify the following:
- the specified <*assignment_id*> should exist in the nbgrader gradebook database (e.g. A1, A2 ...),
- assignment source notebook should be under the ```source/<assignment_id>``` directory
- the released version of the notebook should be under ```release/<assignment_id>```,
- the Moodle notebook filenames should contain student IDs that exist in the nbgrader gradebook
 (see [Initialisation - import student information](#initialisation---import-student-information)).

Usage:
1. Export the submissions from Moodle:
   - navigate to the preferred **Assignment** and select **View all submissions**
   - under **Grading action** select **Download all submissions**
   - create this subdirectory ```<course_dir>/moodle/<assignment_id>/``` and place the downloaded Moodle ZIP in it 

2. Place the ```moodle2nbg.py``` script in the nbgrader course root directory (where typically the gradebook.db is)
and start it with:  
```python3 moodle2nbg.py <assignment_id>```  

(...or alternatively, specify custom command line arguments, type -h for help)

3. The script will summarise the environment/arguments and request a confirmation 
prior to execution.
   
The notebooks will be placed under the ```<course_dir>/<submitted>/<student_id>/<assignment_id>```
directory for every submission with a student ID found in the gradebook. 
Unidentified notebooks will be reported as error for manual intervention. 
The target notebooks will be renamed to match the assignment notebook name as declared in nbgrader.
Existing folders/notebooks will be overwritten in case they already existed.

The script also creates and maintains an auxiliary table **moodle_part_student** in gradebook.db
which will contain the (assignment_id, student_id, participant_id) triplets for later use
in creating the grading CSV to upload back to Moodle (only required if identities are not revealed in Moodle).

## Plagiarism checking with MOSS  
```nb2py4moss.py```  
### Requirements
This script requires a [registered MOSS user ID](http://theory.stanford.edu/~aiken/moss/) and the 
[mosspy](https://github.com/soachishti/moss.py) python module installed in the environment.     
### Description
In order to effectively check student submissions for plagiarism, this script harvests the source code cells
of the Jupyter notebooks submitted by students and creates a reduced .py version of the content. The script is intended for
use in the nbgrader environment. Cells that are "locked" in nbgrader are not harvested, which helps with narrowing the
focus on the content created by the students. The script also pre-processes the assignment skeleton in a similar way.  

The prepared files are then uploaded to [Stanford's MOSS software similarity checker](http://theory.stanford.edu/~aiken/moss/), which generates an HTML report.
The assignment skeleton file is also taken into account as a base file by MOSS, as the pre-contained code blocks 
are legitimately reused and should be ignored.

The script will output the .py code versions and the MOSS report URL at the end of execution.  
It optionally downloads the report and the belonging difference files to the local filesystem.

The submissions are retrieved from: ```<course_dir>/submitted/<student_id>/<assignment_id>/<assignment>.ipynb``` 
for all students who submitted a notebook for the specified assignment.  

The skeleton notebook is taken from ```<course_dir>/release/<assignment_id>/<assignment>.ipynb```.

The pre-processed submission files are saved as
```<course_dir>/moss/<student_id>/<assignment_id>/<assignment>.py```

The pre-processed skeleton file is saved as
```<course_dir>/moss/basefile/<assignment_id>/<assignment>.py```

The report can be opened online with the URL provided at the end of execution. If the option to download the
reports locally has been selected, they are going to be saved under this folder:
```<course_dir>/moss/reports/<assignment_id>/...``` with index.html as the default page

### Usage
1. Place the ```nb2py4moss.py``` script in the nbgrader course root directory and start it with:  
```python3 nb2py4moss.py <assignment_id> <moss_user_id>```  

2. Use the --download switch if you wish to download the report to your local filesystem. The online reports are
typically deleted after 14 days.

Remark: *option -i <N> will allow for setting the preferred ignore limit for repetitions (nr. of occurence of a repeating pattern before 
it is ignored - ie. after this limit the repeating pattern should be considered legitimate sharing). The default is set to 3.*  

## Export grades and upload to Moodle   
```grades2moodle.py```

This script exports the grades and feedback for a given assignment from nbgrader to a Moodle grading worksheet.
This grading approach assumes that participant identities were not revealed, and the nbgrader gradebook.db
contains an auxiliary participant_id-student_id lookup table, which should have been created by moodle2nbg.py
when the submissions were converted to nbgrader format. The result is written back to the Moodle grading worksheet
and will only contain rows for submitted assignments, which were also processed in nbgrader.

### Usage
1. Place this script in the nbgrader course root directory (where typically the gradebook.db is).
2. Download the Moodle grading worksheet for the given assignment (e.g. into <course_dir>/moodle/grading/<...>.csv)
3. Start the script with:
```python3 grades2moodle.py <assignment_id> <moodle_grading_worksheet>```

Check the worksheet before uploading back to Moodle.

