# Patreon Downloader Script

## Description
This script downloads posts (including text, images, and attachments) from a specified Patreon campaign for your personal archival. It authenticates using OAuth2, fetches post data, and saves each post as an HTML file along with its associated media.

## Features
*   OAuth2 authentication with Patreon.
*   Downloads post content (HTML), images, and attachments.
*   Organizes downloads into per-post, human-readable HTML files.
*   Handles pagination to fetch all posts from a campaign.
*   Stores authentication tokens (`patreon_tokens.json`) for easy reuse after initial setup.
*   Basic CSS styling for readable HTML output.
*   Creates local directories for downloaded content, structured by campaign and post.

## Prerequisites
*   Python 3.7+
*   `pip` (Python package installer)
*   Install necessary Python libraries by running:
    ```bash
    pip install -r requirements.txt
    ```

## Setup - Patreon OAuth Client
To use this script, you need to register an OAuth client on Patreon:

1.  **Go to the Patreon Client Registration Page**:
    *   Navigate to [https://www.patreon.com/portal/registration/register-clients](https://www.patreon.com/portal/registration/register-clients) (or if this link changes, go to your Patreon profile/settings and look for "Apps", "API Clients", or "Developer" sections).
2.  **Create a New Client**:
    *   Click "Register client" or "Create Client".
3.  **Fill in the Client Details**:
    *   **Client Name**: Choose any name (e.g., "My Patreon Downloader Script").
    *   **Description**: Optional.
    *   **Redirect URIs**: This is crucial. Add **exactly** `http://localhost:8080/oauth/redirect`.
    *   **Client type**: Select "Confidential".
    *   **Scopes**: The script requires access to campaigns, posts, user identity, and memberships. While the `patreon-python` library often requests a default set of scopes, ensure your client on Patreon has permissions that cover at least:
        *   `identity` (to get your user info)
        *   `identity.memberships` (to potentially list campaigns you're a member of, though this script doesn't auto-list them yet)
        *   `campaigns` (to access campaign information)
        *   `campaigns.posts` (to access posts within a campaign)
        *   `users` (to get user attributes, like author names)
        *   *Note: Patreon's scope names can change. Refer to the official Patreon API documentation for the most current scope definitions if you encounter permission issues.*
4.  **Save and Get Credentials**:
    *   Save your client settings.
    *   Patreon will provide you with a `Client ID` and a `Client Secret`. **Copy these securely.** You will need them to run the script.

## How to Run
1.  Open your terminal or command prompt.
2.  Navigate to the directory where you saved `patreon_downloader.py` and `requirements.txt`.
3.  Run the script using:
    ```bash
    python patreon_downloader.py
    ```
4.  **First Run (Authentication)**:
    *   You will be prompted to enter your `Client ID` and `Client Secret` (obtained from the Patreon client setup).
    *   Your default web browser will automatically open to a Patreon authorization page.
    *   Log in to Patreon (if you aren't already) and click "Allow" or "Authorize" to grant the script access.
    *   After authorization, you'll be redirected to a local web page (e.g., `http://localhost:8080/oauth/redirect?...`). The script will automatically capture the necessary authorization code from this redirect.
    *   A success message ("Authentication successful! You can close this window.") should appear in your browser tab, and the local server will shut down.
    *   Your authentication tokens will be saved in a file named `patreon_tokens.json` in the same directory as the script.
5.  **Subsequent Runs**:
    *   The script will automatically load and use the saved tokens from `patreon_tokens.json`. You won't need to re-enter your Client ID/Secret or re-authorize via the browser unless the token file is deleted or the tokens become invalid.
6.  **Enter Campaign ID**:
    *   After successful authentication (or token loading), you will be prompted to enter the **numerical Campaign ID** of the creator whose posts you wish to download. See the section below on how to find this.

## How to Find Campaign ID
The Campaign ID is a **numerical ID** associated with a creator's Patreon page. Here are a few ways to find it:

1.  **Check the URL (Less Common Now)**: Sometimes, the campaign ID might be directly in the URL, like `https://www.patreon.com/campaigns/123456`. If you see `/campaigns/` followed by a number, that number is the Campaign ID.
2.  **View Page Source**:
    *   Go to the creator's main Patreon page (e.g., `https://www.patreon.com/creatorname`).
    *   Right-click on the page and select "View Page Source" (or use a shortcut like `Ctrl+U` on Windows/Linux, `Cmd+Option+U` on Mac).
    *   In the new tab/window showing the HTML source code, use the find function (`Ctrl+F` or `Cmd+F`) and search for `"campaign_id":`.
    *   You should find something like `"campaign_id":1234567`, where `1234567` is the numerical Campaign ID.
3.  **Browser Developer Tools**:
    *   Go to the creator's main Patreon page.
    *   Open your browser's developer tools (usually by pressing `F12`, or right-clicking and selecting "Inspect" or "Inspect Element").
    *   Go to the "Network" tab.
    *   Refresh the Patreon page or navigate to their "Posts" section.
    *   Look for requests made to the Patreon API (e.g., requests to `www.patreon.com/api/...`). Click on these requests and look at the "Response" or "Preview" tab for JSON data. You might find the `campaign_id` within this data.

*This script currently requires you to find and enter this ID manually.*

## Output Structure
Downloaded content is organized as follows:

*   `patreon_tokens.json`: Stores your OAuth access and refresh tokens. **Keep this file secure and do not share it.**
*   `downloaded_posts/`: Main directory for all downloaded content.
    *   `{campaign_id}/`: A subdirectory is created for each campaign, named with its numerical ID.
        *   `{post_id}/`: Inside each campaign folder, a subdirectory is created for each post, named with its numerical post ID.
            *   `index.html`: The main HTML file for the post, containing its text content and links to local media.
            *   `images/`: Contains all images downloaded for this specific post.
            *   `attachments/`: Contains any other files (e.g., PDFs, ZIPs) attached to this specific post.

## Troubleshooting
*   **Port 8080 in use**:
    *   During the first-time authentication, the script starts a temporary web server on port 8080. If another application is using this port, the script will fail. Close any other applications using port 8080 (e.g., other development servers) and try again.
*   **Authentication Fails / Invalid Tokens**:
    *   Double-check that your `Client ID` and `Client Secret` were entered correctly.
    *   Ensure the `Redirect URI` in your Patreon client settings is **exactly** `http://localhost:8080/oauth/redirect`.
    *   If `patreon_tokens.json` exists and you're still having issues, try deleting it and re-running the script to force a new authentication.
*   **"Campaign not found", "Forbidden", or Access Issues**:
    *   Verify the Campaign ID is correct and is a number.
    *   Ensure the Patreon account you used to authenticate the script has active access to that creator's posts (e.g., you are a patron of the required tier, or the posts are public).
    *   The scopes defined for your OAuth client on Patreon might be insufficient. Review the "Setup - Patreon OAuth Client" section.
*   **Images/Attachments Not Displaying in HTML**:
    *   Check if the media files were downloaded correctly into the respective `images/` or `attachments/` subfolders for that post.
    *   The HTML file uses relative paths (e.g., `images/filename.jpg`). Ensure the `index.html` and its associated media folders are kept together in their generated structure.
*   **Script Errors after Patreon Website/API Changes**:
    *   Patreon may update its website or API. Such changes can break the script. Check the project's source for updates or consider searching for similar issues reported by other users.

## Disclaimer
*   This script is intended for **personal, archival purposes only**.
*   Please respect Patreon's Terms of Service and the intellectual property rights of creators on the platform. Do not misuse downloaded content.
*   This script interacts with Patreon's API and website. Changes by Patreon may break the script's functionality. Use at your own risk. The maintainers of this script are not responsible for how you use it.
