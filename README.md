# nbgutils  
Utility scripts and tools for using nbgrader with moodle assignments.

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
(eg. "k00987654").

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
Converts submissions from Moodle directory and naming format to the one expected by nbgrader.
Takes a submissions ZIP archive from moodle as input, and expects prepared nbgrader environment.  

The script assumes a Moodle/assignment setup with:
- identities not yet revealed in Moodle at the time of downloading the ZIP archive (Participant_XXXXXXXX folders),
- one submission notebook per participant with the student ID included in the filename (eg. A1_k00987654.ipynb).   

The script will verify the following:
- the specified <assignment_id> should exist in the nbgrader gradebook database,
- assignment source notebook should be under the ```source/<assignment_id>``` directory
- the released version of the notebook should be under ```release/<assignment_id>```,
- the Moodle notebook filenames should contain a student IDs that exists in the nbgrader gradebook.

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
Existing folders/notebooks will be overwritted in case they already existed.

The script also creates and maintains an auxiliary table **moodle_part_student** in gradebook.db
which will contain the (assignment_id, student_id, participant_id) triplets for later use
in creating the grading CSV to upload back to Moodle (only required if identities are not revealed in Moodle).

