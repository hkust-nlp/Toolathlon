# Groundtruth
## MIT
https://oge.mit.edu/graduate-admissions/applications/international-applicants/
https://oge.mit.edu/programs/electrical-engineering-and-computer-science/
https://oge.mit.edu/graduate-admissions/applications/procedures/

Graduate Record Examination (GRE)
Not required

International English Language Testing System (IELTS)
Minimum score required: 7
Electronic scores send to: MIT Graduate Admissions

Test of English as a Foreign Language (TOEFL)
Minimum score required: 100 (iBT) 600 (PBT)
Institute code: 3514
Department code: 78 or 66

IELTS exam is preferred over the TOEFL. Waiver of TOEFL/IELTS may be available.

Fee: 90 dollars

Due on December 1st 11:59 PM Eastern Time

## Stanford
https://www.cs.stanford.edu/admissions/graduate-application-checklists
https://gradadmissions.stanford.edu/apply/test-scores
https://www.cs.stanford.edu/admissions-graduate-application-deadlines

GRE: GREs are NOT required for MSCS applicants. 

Fee: 125 dollars

Due on December 2nd 11:59 PM Eastern Time

## CMU

https://www.cs.cmu.edu/academics/graduate-admissions

TOEFL 100 (recommended)
IELTS 7

Fee:    Early application deadline fee $80 per program.
        Application fee after November 19, 2025, $100 per program.

Early Deadline: Nov. 19, 2025 (3 p.m. EST)
Final Deadline: Dec. 10, 2025 (3 p.m. EST) 

## Harvard
https://seas.harvard.edu/masters-computational-science-and-engineering/how-apply
https://seas.harvard.edu/prospective-students/prospective-graduate-students/how-apply
https://gsas.harvard.edu/program/computational-science-and-engineering

TOEFL 80
IELTS 6.5

Fee: 105 dollars

Due on December 1st 05:00 PM Eastern Time


## UCB

https://grad.berkeley.edu/admissions/application-process/requirements/#application-fee
https://grad.berkeley.edu/admissions/our-programs/
https://grad.berkeley.edu/admissions/application-process/

GRE is optional.

TOEFL	90
IELTS	7.0

Fee: 155 dollars

Due on December 1st, 08:59 PM Pacific Standard Time

# Preprocess

1. Delete the previous cs_top10_us_2025.xlsx in workspace
2. Copy the format.xlsx in initial_workspace to workspace

# Evaluation
1. Change the whole check_local.py to adapt to the xlsx format files
2. Test whether the agent fills in the excel according to the rules in the prompt：
    a. If the generated answer has the different number of university with groundtruth,
    b. If the type of data is incorrect,
    c. Most requirements are from MSCS of every university. If it provides information of other programs,
        it will fail the test immediately.
3. Make the comparison more robust eg:
    a. 105 and 105.0
    b. stanford and Stanford (lowercase, space and symbol (except "_") will not affect the comparison)
        will not affect the comparison
