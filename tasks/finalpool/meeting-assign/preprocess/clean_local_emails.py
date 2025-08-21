import imaplib
import json
import sys

def clean_emails(config, clean=True):
    """
    Connects to an IMAP server and deletes all emails in the INBOX.

    Args:
        config (dict): A dictionary containing the connection details.
    """
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

        # Select the INBOX
        status, messages = imap.select("INBOX")
        if status != "OK":
            print("Error selecting INBOX")
            return

        print(f"Total emails in INBOX: {messages[0].decode('utf-8')}")

        if clean == False:
            return
        # Search for all emails in the INBOX
        status, email_ids = imap.search(None, "ALL")
        if status != "OK":
            print("Error searching for emails")
            imap.close()
            imap.logout()
            return

        email_id_list = email_ids[0].split()

        if not email_id_list:
            print("No emails to delete.")
        else:
            print(f"Marking {len(email_id_list)} emails for deletion...")
            # Mark all emails for deletion
            for email_id in email_id_list:
                imap.store(email_id, "+FLAGS", "\\Deleted")

            # Permanently delete the marked emails
            print("Permanently deleting emails...")
            imap.expunge()
            print("All emails have been deleted.")

        # Close the mailbox and logout
        imap.close()
        imap.logout()
        print("Logged out.")

    except imaplib.IMAP4.error as e:
        print(f"An IMAP error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    config = receiver_config={
        "email": "jjones@mcp.com",
        "password": "jessica1987%",
        "name": "Meeting Assignment Agent",
        "imap_server": "localhost",
        "imap_port": 1143,
        "smtp_server": "localhost",
        "smtp_port": 1587,
        "use_ssl": False,
        "use_starttls": False
    }

    clean_emails(config, clean=False)
