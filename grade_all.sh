#!/bin/bash
#######################################################################################################################+
# grade_all.sh
# ============
# Bulk (sequential) grading of all submitted notebooks for a given assignment with nbgrader.
# Used to avoid/monitor GPU memory usage and other resource related issues that might originate from batch grading with
# the standard nbgrader operation.
#
# Usage:    grade_all.sh <assignment>
# - it should be placed in the nbgrader course root directory and given execution permission
# - before using configure the variables below for nbgrader bin directory and the nvidia-smi tool
# - redirect both stdout and stderr to a log file to allow for analysing the output later
#######################################################################################################################+
NBG_BIN=/usr/local/bin
NVIDIA_SMI=/usr/bin/nvidia-smi
COURSE_DIR=.

ASSIGNMENT=${1}

# outputs a timestamped message to stdout
function consmsg() {
  echo "[`date +'%Y.%m.%d %H:%M:%S'`] $1" 
}

if [ -z "${ASSIGNMENT}" ] || [ ! -d "${COURSE_DIR}/release/${ASSIGNMENT}" ];then
  echo "Please provide assignment name - eg. A1, A2 ..."
  echo "Usage:    grade.sh <assingment_name>"
  echo
  exit 1
fi

cnt=0
total=`find ${COURSE_DIR}/submitted -type d -name "${ASSIGNMENT}" | wc -l`
consmsg "${total} submitted notebooks found for assignment ${ASSIGNMENT}"
find ./submitted -type d -name "${ASSIGNMENT}" | while read SUB_FOLD
do
  ((cnt+=1))
  STUDENT=`echo ${SUB_FOLD} | cut -f 3 -d '/'`
  consmsg "#------------------------------------------------------"
  consmsg "# grade.sh - processing submission ${cnt} of ${total}"
  consmsg "#------------------------------------------------------"
  consmsg "started grading assignment ${ASSIGNMENT} for student: ${STUDENT}"
  #${NBG_BIN}/nbgrader autograde ${ASSIGNMENT} --student ${STUDENT}
  consmsg "finished grading assignment ${ASSIGNMENT} for student: ${STUDENT}"
  ${NVIDIA_SMI}
done
