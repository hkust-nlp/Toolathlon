from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from argparse import ArgumentParser
import json
import sys
from pathlib import Path
from datetime import datetime
import os

from utils.app_specific.google_form.ops import clear_google_forms
from utils.app_specific.google_oauth.ops import get_credentials

GOOGLE_CREDENTIAL_FILE = "configs/google_credentials.json"
GOOGLE_FORM_NAME = "Freshmen Welcome Party"

def create_google_form(service, form_name):
    """Create a new Google Form with specified questions"""
    
    # Create the form structure
    form = {
        "info": {
            "title": form_name,
            "documentTitle": form_name
        }
    }
    
    # Create the form
    result = service.forms().create(body=form).execute()
    form_id = result["formId"]
    
    # Define all the questions
    requests = []
    
    # Question 1: Name (Required, Text)
    requests.append({
        "createItem": {
            "item": {
                "title": "Name",
                "questionItem": {
                    "question": {
                        "required": True,
                        "textQuestion": {}
                    }
                }
            },
            "location": {"index": 0}
        }
    })
    
    # Question 2: Email (Required, Text)
    requests.append({
        "createItem": {
            "item": {
                "title": "Email",
                "questionItem": {
                    "question": {
                        "required": True,
                        "textQuestion": {}
                    }
                }
            },
            "location": {"index": 1}
        }
    })
    
    # Question 3: Address (Required, Text)
    requests.append({
        "createItem": {
            "item": {
                "title": "Address",
                "questionItem": {
                    "question": {
                        "required": True,
                        "textQuestion": {}
                    }
                }
            },
            "location": {"index": 2}
        }
    })
    
    # Question 4: Session preference (Required, Multiple Choice)
    requests.append({
        "createItem": {
            "item": {
                "title": "Do you want to attend the morning session or the afternoon session?",
                "questionItem": {
                    "question": {
                        "required": True,
                        "choiceQuestion": {
                            "type": "CHECKBOX",
                            "options": [
                                {"value": "Morning"},
                                {"value": "Afternoon"}
                            ]
                        }
                    }
                }
            },
            "location": {"index": 3}
        }
    })
    
    # Question 5: Dietary Restrictions (Required, Multiple Choice)
    requests.append({
        "createItem": {
            "item": {
                "title": "Dietary Restrictions",
                "questionItem": {
                    "question": {
                        "required": True,
                        "choiceQuestion": {
                            "type": "RADIO",
                            "options": [
                                {"value": "None"},
                                {"value": "Vegan"},
                                {"value": "Kosher"},
                                {"value": "No Seafood"},
                                {"value": "No Spicy Food"}
                            ]
                        }
                    }
                }
            },
            "location": {"index": 4}
        }
    })
    
    # Question 6: Phone (Optional, Text)
    requests.append({
        "createItem": {
            "item": {
                "title": "Phone",
                "questionItem": {
                    "question": {
                        "required": False,
                        "textQuestion": {}
                    }
                }
            },
            "location": {"index": 5}
        }
    })
    
    # Question 7: Anxiety level (Required, Multiple Choice)
    requests.append({
        "createItem": {
            "item": {
                "title": "How anxious are you feeling?",
                "questionItem": {
                    "question": {
                        "required": True,
                        "choiceQuestion": {
                            "type": "RADIO",
                            "options": [
                                {"value": "1"},
                                {"value": "2"},
                                {"value": "3"},
                                {"value": "4"},
                                {"value": "5"}
                            ]
                        }
                    }
                }
            },
            "location": {"index": 6}
        }
    })
    
    # Question 8: Activities (Required, Multiple Choice - assuming single choice based on context)
    requests.append({
        "createItem": {
            "item": {
                "title": "Are you good at these activities?",
                "questionItem": {
                    "question": {
                        "required": True,
                        "choiceQuestion": {
                            "type": "RADIO",
                            "options": [
                                {"value": "swimming"},
                                {"value": "running"},
                                {"value": "basketball"},
                                {"value": "football"},
                                {"value": "Computer programming"}
                            ]
                        }
                    }
                }
            },
            "location": {"index": 7}
        }
    })
    
    # Question 9: Student ID (Required, Text)
    requests.append({
        "createItem": {
            "item": {
                "title": "Student ID",
                "questionItem": {
                    "question": {
                        "required": True,
                        "textQuestion": {}
                    }
                }
            },
            "location": {"index": 8}
        }
    })
    
    # Question 10: Birthday (Optional, Date)
    requests.append({
        "createItem": {
            "item": {
                "title": "Birthday",
                "questionItem": {
                    "question": {
                        "required": False,
                        "dateQuestion": {
                            "includeTime": False,
                            "includeYear": True
                        }
                    }
                }
            },
            "location": {"index": 9}
        }
    })
    
    # Question 11: Highest degree earned (Required, Multiple Choice)
    requests.append({
        "createItem": {
            "item": {
                "title": "Highest degree earned",
                "questionItem": {
                    "question": {
                        "required": True,
                        "choiceQuestion": {
                            "type": "RADIO",
                            "options": [
                                {"value": "bachelor"},
                                {"value": "master"},
                                {"value": "doctor"}
                            ]
                        }
                    }
                }
            },
            "location": {"index": 10}
        }
    })
    
    # Execute batch update to add all questions
    service.forms().batchUpdate(
        formId=form_id,
        body={"requests": requests}
    ).execute()
    
    return form_id

if __name__=="__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--launch_time", required=True, help="Launch time")
    args = parser.parse_args()

    # Get credentials
    creds = get_credentials(GOOGLE_CREDENTIAL_FILE)
    service = build('forms', 'v1', credentials=creds)
    
    # Part 0: Delete existing forms with the same name
    clear_google_forms(GOOGLE_FORM_NAME)
    
    # Part 1: Create the new form
    form_id = create_google_form(service, GOOGLE_FORM_NAME)
    
    # Generate URLs
    form_public_url = f"https://docs.google.com/forms/d/{form_id}/viewform"
    form_drive_url = f"https://docs.google.com/forms/d/{form_id}/edit"
    
    # Part 2: Save the public form link
    if args.agent_workspace:
        agent_workspace_path = Path(args.agent_workspace)
        agent_workspace_path.mkdir(parents=True, exist_ok=True)
        
        with open(agent_workspace_path / "form_link_for_public.txt", "w") as f:
            f.write(form_public_url)
        print(f"Public form link saved to: {agent_workspace_path / 'form_link_for_public.txt'}")
    
    # Part 3: Save the drive edit link
    file_path = os.path.dirname(__file__)
    groundtruth_workspace_path = Path(os.path.join(file_path, "..", "groundtruth_workspace"))
    groundtruth_workspace_path.mkdir(parents=True, exist_ok=True)
    
    with open(groundtruth_workspace_path / "form_link_for_drive.txt", "w") as f:
        f.write(form_drive_url)
    print(f"Drive edit link saved to: {groundtruth_workspace_path / 'form_link_for_drive.txt'}")
    
    # Print the links for confirmation
    print(f"\nForm created successfully!")
    print(f"Public form URL: {form_public_url}")
    print(f"Drive edit URL: {form_drive_url}")
    print(f"Launch time: {args.launch_time}")