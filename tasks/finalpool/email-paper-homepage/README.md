# Publication Update Workflow

This document outlines the workflow for updating accepted publication details and code repository links on your personal academic homepage. It leverages a local email server and GitHub tools to streamline the process from identifying acceptance notifications to committing changes.

## Task Overview

**Objective**: Update the acceptance information for papers currently marked as "preprint" or "under review" on your personal homepage based on email search results. Additionally, update the status of code open-sourcing by adding repository links for papers that have already been released.

## Tools Required

* **Local Email MCP**: Access and filter emails from a local email server to find paper acceptance notifications.
* **GitHub MCP**: List and access repositories, open the `My-Homepage` repository, and edit publication files.
* **Terminal**: For additional file operations and system commands if needed.

## Key Requirements

1. **Paper Status Updates**: Change venue information from "Under review" or "Preprint" to actual conference/journal names based on acceptance emails.

2. **Code Repository Links**: Add `codeurl` fields to publications that have corresponding released GitHub repositories.

3. **Repository Release Status**: Only link to repositories that are **actually released and finished**. Do not add code links for papers that are still under review or have repositories that are not yet ready for public release.

4. **Remote Operations**: All modifications must be made directly to the GitHub repository, not local files.

## Workflow Steps

1. **Access Email System**
   * Connect to the local email server using the Email MCP tool.
   * Check connection status and retrieve available email folders.
   * Access the INBOX to scan for relevant messages.

2. **Identify Acceptance Emails**
   * Search through emails for acceptance notifications containing keywords like "accepted", "camera-ready", "congratulations", etc.
   * Extract relevant details such as:
     - Paper title
     - Conference/journal name  
     - Acceptance status
     - Any deadline information

3. **Analyze GitHub Repositories**
   * Use GitHub MCP to list all your repositories.
   * Identify the `My-Homepage` repository containing your academic website.
   * Search for paper-related code repositories that correspond to your publications.
   * **Important**: Verify which repositories are actually released and ready for public access.

4. **Determine Files to Modify**
   * Navigate to the `/_publications` directory within the homepage repository.
   * Each publication has its own Markdown file named after the paper (e.g., `2025-06-01-paper-name.md`).
   * Match extracted paper information to corresponding Markdown files.

5. **Update Publication Entries**
   * For accepted papers:
     - Update the `venue` field from "Under review" or "Preprint" to the official conference/journal name.
     - Update citation information accordingly.
   
   * For code repository links:
     - Add `codeurl: 'https://github.com/username/repo-name'` field **only** for papers with released repositories.
     - **Do not** add code URLs for papers that are still under review or have unreleased repositories.

6. **Commit Changes**
   * Use GitHub MCP to commit and push all updates to the `My-Homepage` repository.
   * Provide meaningful commit messages describing the changes made.

## Important Notes

* **Verification is Critical**: Always verify that a GitHub repository is actually released and contains finished work before adding it to a publication entry.

* **Status Consistency**: Ensure that code repository links are only added for papers that have been officially published or accepted, not for papers still under review.

* **Email Analysis**: Carefully read email content to distinguish between different types of notifications (acceptance, camera-ready deadlines, oral presentation notifications, etc.).

* **File Format**: Maintain consistent YAML front matter format in publication Markdown files.

## Expected Outcome

After completion, your academic homepage should have:
- Updated venue information for all newly accepted papers
- Appropriate code repository links for released projects
- Consistent and accurate publication metadata
- All changes properly committed to the GitHub repository