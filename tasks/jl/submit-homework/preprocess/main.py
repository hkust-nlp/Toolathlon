import asyncio
from argparse import ArgumentParser
import os
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


async def main():
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()

    # Load Google credentials
    credentials_path = "configs/google_credentials.json"
    if not os.path.exists(credentials_path):
        print(f"Error: Credentials file not found at {credentials_path}")
        return

    with open(credentials_path, 'r') as f:
        cred_data = json.load(f)
    
    # Create credentials object
    credentials = Credentials(
        token=cred_data.get('token'),
        refresh_token=cred_data.get('refresh_token'),
        token_uri=cred_data.get('token_uri'),
        client_id=cred_data.get('client_id'),
        client_secret=cred_data.get('client_secret'),
        scopes=cred_data.get('scopes')
    )

    # Initialize Google Forms API
    forms_service = build('forms', 'v1', credentials=credentials)
    drive_service = build('drive', 'v3', credentials=credentials)

    form_title = "NLP Summer Course Homework Submit Form"
    
    # Delete existing forms with the same name
    try:
        results = drive_service.files().list(
            q=f"name='{form_title}' and mimeType='application/vnd.google-apps.form'",
            fields="files(id, name)"
        ).execute()
        
        for file in results.get('files', []):
            print(f"Deleting existing form: {file['name']} (ID: {file['id']})")
            drive_service.files().delete(fileId=file['id']).execute()
    except HttpError as e:
        print(f"Error deleting existing forms: {e}")

    # Create new form (only title allowed during creation)
    try:
        form = {
            "info": {
                "title": form_title
            }
        }
        
        result = forms_service.forms().create(body=form).execute()
        form_id = result['formId']
        form_url = result['responderUri']
        
        print(f"Created form with ID: {form_id}")
        print(f"Form URL: {form_url}")

        # Add questions to the form using batchUpdate
        requests = []
        
        # First, update the form description
        requests.append({
            "updateFormInfo": {
                "info": {
                    "title": form_title,
                    "description": "Submit your NLP course homework assignments"
                },
                "updateMask": "description"
            }
        })
        
        # Question 1: Name (required text field)
        requests.append({
            "createItem": {
                "item": {
                    "title": "Name",
                    "questionItem": {
                        "question": {
                            "required": True,
                            "textQuestion": {
                                "paragraph": False
                            }
                        }
                    }
                },
                "location": {"index": 0}
            }
        })

        # Question 2: StudentID (required text field)
        requests.append({
            "createItem": {
                "item": {
                    "title": "StudentID",
                    "questionItem": {
                        "question": {
                            "required": True,
                            "textQuestion": {
                                "paragraph": False
                            }
                        }
                    }
                },
                "location": {"index": 1}
            }
        })

        # Question 3: June 10th homework (file upload)
        requests.append({
            "createItem": {
                "item": {
                    "title": "Please name the homework from June 10th in the format: Name-StudentID-NLP1.pdf, and submit it via the link below.",
                    "questionItem": {
                        "question": {
                            "required": True,
                            "fileUploadQuestion": {
                                "folderId": "root",
                                "maxFiles": 1,
                                "maxFileSize": 10485760,  # 10MB in bytes
                                "types": ["PDF"]
                            }
                        }
                    }
                },
                "location": {"index": 2}
            }
        })

        # Question 4: June 20th homework (file upload)
        requests.append({
            "createItem": {
                "item": {
                    "title": "Please name the homework from June 20th in the format: Name-StudentID-NLP2.doc, and submit it via the link below.",
                    "questionItem": {
                        "question": {
                            "required": True,
                            "fileUploadQuestion": {
                                "folderId": "root",
                                "maxFiles": 1,
                                "maxFileSize": 10485760,  # 10MB in bytes
                                "types": ["DOCUMENT"]
                            }
                        }
                    }
                },
                "location": {"index": 3}
            }
        })

        # Question 5: June 30th homework (file upload for ZIP)
        requests.append({
            "createItem": {
                "item": {
                    "title": "Please compress the two Excel files from June 30th into a ZIP file, rename it as Name-StudentID-NLP3.zip, and upload it via the link below.",
                    "questionItem": {
                        "question": {
                            "required": True,
                            "fileUploadQuestion": {
                                "folderId": "root",
                                "maxFiles": 1,
                                "maxFileSize": 10485760,  # 10MB in bytes
                                "types": ["ANY"]
                            }
                        }
                    }
                },
                "location": {"index": 4}
            }
        })

        # Question 6: Late submission reason (optional text field)
        requests.append({
            "createItem": {
                "item": {
                    "title": "Do not fill in this information unless you are unable to submit the assignment on time. Please provide the reason for the delay here.",
                    "questionItem": {
                        "question": {
                            "required": False,
                            "textQuestion": {
                                "paragraph": True
                            }
                        }
                    }
                },
                "location": {"index": 5}
            }
        })

        # Batch update to add all questions
        forms_service.forms().batchUpdate(
            formId=form_id,
            body={"requests": requests}
        ).execute()
        
        print("Successfully added all questions to the form")

        # Update the nlp_summer_course_info.md file in agent_workspace
        if args.agent_workspace:
            nlp_info_path = os.path.join(args.agent_workspace, "nlp_summer_course_info.md")
            if os.path.exists(nlp_info_path):
                with open(nlp_info_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Replace placeholder with actual form URL
                updated_content = content.replace("{homework_submit_url}", form_url)
                
                with open(nlp_info_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
                    
                print(f"Updated {nlp_info_path} with form URL")

        # Save form URL to groundtruth workspace
        groundtruth_workspace = os.path.join(os.path.dirname(__file__), "..", "groundtruth_workspace")
        os.makedirs(groundtruth_workspace, exist_ok=True)
        
        form_url_file = os.path.join(groundtruth_workspace, "targeted_form_url.txt")
        with open(form_url_file, 'w', encoding='utf-8') as f:
            f.write(form_url)
            
        print(f"Saved form URL to {form_url_file}")
        
    except HttpError as e:
        print(f"Error creating form: {e}")
        return


if __name__ == "__main__":
    asyncio.run(main())