# PhD Application Email Task

## Overview

This task simulates a PhD application process where an AI agent needs to process an email from a professor and organize application materials according to specific requirements. The agent must find the relevant email, organize files into a structured format, and submit the materials via email.

## Task Workflow

### 1. Find Kaiming's Email
- **Objective**: Locate the email from sender "kaiming" in the inbox
- **Key Information**: The email contains detailed instructions for PhD application material submission
- **Email Subject**: "Re: PhD Application - Application Materials Submission Guidelines"
- **Target Email Address**: The email specifies to send materials to `myersj@mcp.com`

### 2. Analyze Email Requirements
- **Folder Structure**: Create a specific directory structure with the format:
  ```
  Application_Materials_[YourName]_[YourStudentID]/
  ├── 01_Personal_Information/
  │   ├── ID_Card.pdf
  │   ├── Photo.jpg
  │   └── Resume.pdf
  ├── 02_Academic_Materials/
  │   ├── Awards_Certificates/
  │   │   └── All_Awards_Certificates.pdf
  │   ├── Enrollment_Certificate.pdf
  │   └── Transcript.pdf
  ├── 03_Recommendation_Letters/
  │   ├── Recommendation_Letter_ProfessorName-1.pdf
  │   └── Recommendation_Letter_ProfessorName-2.pdf
  └── 04_Supplementary_Materials/
      ├── Portfolio.pdf
      └── Project_Report.pdf
  ```

### 3. Organize Personal Information Files
- **Location**: Files are initially in `Application_Materials_flat/` directory
- **Required Actions**:
  - Move `ID_Card.pdf` to `01_Personal_Information/`
  - Move `Photo.jpg` to `01_Personal_Information/`
  - Rename `CV.pdf` to `Resume.pdf` and move to `01_Personal_Information/`

### 4. Process Academic Materials
- **Enrollment Certificate**: Move `Enrollment_Certificate.pdf` to `02_Academic_Materials/`
- **Transcript**: Move `Transcript.pdf` to `02_Academic_Materials/`
- **Awards Processing**: This is a critical step requiring:
  - Identify all award certificates by date:
    - `Outstanding_Student_Award_2021.pdf` (2021)
    - `Research_Competition_First_Place_2022.pdf` (2022)
    - `Academic_Excellence_Award_2023.pdf` (2023)
  - Sort certificates chronologically by date
  - Merge all award PDFs into a single file: `All_Awards_Certificates.pdf`
  - Ensure one award per page in the merged PDF
  - Place the merged file in `02_Academic_Materials/Awards_Certificates/`

### 5. Process Recommendation Letters
- **Critical Task**: Read the content of recommendation letter PDFs to identify professor names
- **Files to Process**:
  - `Recommendation_Letter_1.pdf` - Extract professor name from content
  - `Recommendation_Letter_2.pdf` - Extract professor name from content
- **Renaming Convention**: 
  - Rename based on professor names found in the content
  - Format: `Recommendation_Letter_[ProfessorName].pdf`
  - Move renamed files to `03_Recommendation_Letters/`

### 6. Organize Supplementary Materials
- **Required Actions**:
  - Move `Portfolio.pdf` to `04_Supplementary_Materials/`
  - Move `Project_Report.pdf` to `04_Supplementary_Materials/`

### 7. Retrieve Personal Information
- **Memory Access**: Use the memory system to retrieve personal details
- **Required Information**:
  - Full name (for folder naming)
  - Student ID (for folder naming)
  - Use format: `Application_Materials_[Name]_[StudentID]`
  - Example: `Application_Materials_MaryCastillo_2201210606`

### 8. Create ZIP Archive
- **Final Step**: Compress the entire organized folder structure into a ZIP file
- **Naming**: Use the same name as the folder for the ZIP file
- **Verification**: Ensure all required files are included in the correct structure

### 9. Send Email Submission
- **Recipient**: Send to `myersj@mcp.com` (as specified in kaiming's email)
- **Subject**: Use "submit_material" as the email subject
- **Attachment**: Include the ZIP file containing all organized materials
- **Email Body**: Professional submission message

## Key Technical Requirements

### File Processing Capabilities
- **PDF Manipulation**: Ability to merge multiple PDF files while maintaining quality
- **Content Reading**: Extract text from PDF files to identify professor names
- **File Organization**: Move and rename files according to specific patterns

### Email Operations
- **Email Reading**: Parse email content to extract requirements
- **Email Sending**: Send emails with attachments to specified recipients
- **Subject Line**: Use exact subject specified in requirements

### Memory Integration
- **Personal Data**: Access stored personal information (name, student ID)
- **Data Formatting**: Format personal data according to naming conventions

## Success Criteria

### Structure Validation
- All files must be in the correct directory structure
- Folder naming must follow the exact format with personal information
- All required files must be present

### Content Validation
- `All_Awards_Certificates.pdf` must contain exactly 3 pages (one award per page)
- Awards must be in chronological order (2021, 2022, 2023)
- Recommendation letters must be renamed with actual professor names
- Each page of the awards PDF must contain the expected award text

### Email Validation
- Email must be sent to the correct recipient (`myersj@mcp.com`)
- Subject line must be exactly "submit_material"
- ZIP attachment must be properly formatted and complete

## Tools Required
- **filesystem**: For file operations and organization
- **memory**: To retrieve personal information
- **emails**: For reading and sending emails
- **pdf-tools**: For PDF manipulation and content extraction
- **terminal**: For command-line operations if needed

## Notes
- The task requires attention to detail in file naming and organization
- PDF content extraction is crucial for proper recommendation letter renaming
- The chronological ordering of awards is specifically validated
- All file names must be in English without special characters or spaces