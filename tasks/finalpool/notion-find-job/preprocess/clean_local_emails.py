import imaplib
import json
import sys

def clean_emails(config, folders=None, clean=True):
    """
    Connects to an IMAP server and deletes all emails in specified folders.

    Args:
        config (dict): A dictionary containing the connection details.
        folders (list): List of folder names to clean. If None, uses default folders.
        clean (bool): Whether to actually delete emails or just count them.
    """
    if folders is None:
        folders = ["INBOX", "Sent", "Trash", "Junk", "Drafts"]

    try:
        # Connect to the IMAP server
        if config.get("use_ssl"):
            imap = imaplib.IMAP4_SSL(config["imap_server"], config["imap_port"])
        else:
            imap = imaplib.IMAP4(config["imap_server"], config["imap_port"])

        if config.get("use_starttls"):
            imap.starttls()

        # Login to the account
        imap.login(config["email"], config["password"])
        print(f"Logged in as {config['email']}")

        total_deleted = 0

        # Process each folder
        for folder in folders:
            print(f"\n--- Processing folder: {folder} ---")
            try:
                # Select the folder
                status, messages = imap.select(folder)
                if status != "OK":
                    print(f"Error selecting folder '{folder}' or folder does not exist")
                    continue

                email_count = int(messages[0].decode('utf-8'))
                print(f"Total emails in {folder}: {email_count}")

                if email_count == 0:
                    print(f"No emails in {folder}")
                    continue

                if clean == False:
                    continue

                # Search for all emails in the folder
                status, email_ids = imap.search(None, "ALL")
                if status != "OK":
                    print(f"Error searching for emails in {folder}")
                    continue

                email_id_list = email_ids[0].split()

                if not email_id_list:
                    print(f"No emails to delete in {folder}")
                else:
                    print(f"Marking {len(email_id_list)} emails for deletion in {folder}...")
                    # Mark all emails for deletion
                    for email_id in email_id_list:
                        imap.store(email_id, "+FLAGS", "\\Deleted")

                    # Permanently delete the marked emails
                    print(f"Permanently deleting emails from {folder}...")
                    imap.expunge()
                    print(f"All emails in {folder} have been deleted.")
                    total_deleted += len(email_id_list)

            except imaplib.IMAP4.error as e:
                print(f"IMAP error processing folder '{folder}': {e}")
                continue
            except Exception as e:
                print(f"Unexpected error processing folder '{folder}': {e}")
                continue

        if clean:
            print(f"\nTotal emails deleted across all folders: {total_deleted}")

        # Close the connection and logout
        imap.close()
        imap.logout()
        print("Logged out.")

    except imaplib.IMAP4.error as e:
        print(f"An IMAP error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

# Example usage:
if __name__ == "__main__":
    config = {
        "email": "rkelly27@mcp.com",
        "password": "ronald_81q2O", 
        "name": "Ronald Kelly",
        "imap_server": "localhost",
        "imap_port": 1143,
        "smtp_server": "localhost",
        "smtp_port": 1587
    }
    # To clean all default folders (INBOX, Sent, Trash, Junk, Drafts)
    clean_emails(config, clean=True)

    # To clean specific folders only
    # clean_emails(config, folders=["INBOX", "Sent"], clean=True)

    # To just count emails without deleting
    # clean_emails(config, clean=False)