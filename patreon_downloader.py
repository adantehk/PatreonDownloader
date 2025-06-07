import patreon
import os
import json
import webbrowser
import http.server
# It's highly recommended to ensure your patreon library is up-to-date:
# pip install --upgrade patreon
# This can help resolve potential AttributeError issues and ensure proper exception handling.

import socketserver
from urllib.parse import urlparse, parse_qs
import requests
from bs4 import BeautifulSoup
import re
import traceback # For detailed error reporting

TOKEN_FILE = "patreon_tokens.json"
DOWNLOAD_DIR = "downloaded_posts"

# --- Token Management ---
def load_or_refresh_tokens():
    """Loads tokens from TOKEN_FILE or triggers authentication if not found/valid."""
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, 'r') as f:
                tokens = json.load(f)
                access_token = tokens.get('access_token')
                # refresh_token = tokens.get('refresh_token') # Store for future refresh logic

                if not access_token:
                    print("Access token not found in token file. Re-authenticating...")
                    return authenticate_and_get_token()

                # Placeholder: Add logic here to test token validity (e.g., simple API call)
                # If token is invalid and refresh_token exists, try to refresh it.
                # For now, we assume the token is valid if it exists.
                print("Tokens loaded successfully.")
                return access_token
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error reading token file {TOKEN_FILE}: {e}. Re-authenticating...")
            return authenticate_and_get_token()
    else:
        return authenticate_and_get_token()

def authenticate_and_get_token():
    """Runs the authentication process and returns the access token."""
    authenticate() # This function handles token saving internally
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, 'r') as f:
                tokens = json.load(f)
                return tokens.get('access_token')
        except (json.JSONDecodeError, IOError) as e:
            print(f"Failed to load tokens after authentication: {e}")
            return None
    return None

def exchange_code_for_tokens(code, client_id, client_secret, redirect_uri):
    """Exchanges the authorization code for access and refresh tokens."""
    try:
        oauth_client = patreon.OAuth(client_id, client_secret)
        tokens_response = oauth_client.get_tokens(code, redirect_uri)
        access_token = tokens_response['access_token']
        refresh_token = tokens_response.get('refresh_token')

        with open(TOKEN_FILE, 'w') as f:
            json.dump({'access_token': access_token, 'refresh_token': refresh_token}, f)
        print(f"Successfully authenticated and tokens stored in {TOKEN_FILE}")
        return True
    except Exception as e:
        print(f"Error exchanging code for tokens: {e}")
        return False

def authenticate():
    """Handles the OAuth authentication process. Saves tokens to TOKEN_FILE."""
    client_id = input("Enter your Patreon client_id: ")
    client_secret = input("Enter your Patreon client_secret: ")

    redirect_uri = "http://localhost:8080/oauth/redirect"
    print(f"\nPlease ensure you have registered the following redirect URI with your Patreon OAuth client: {redirect_uri}\n")

    auth_url = f"https://www.patreon.com/oauth2/authorize?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}"

    print(f"Opening browser for authentication: {auth_url}")
    webbrowser.open(auth_url)

    # Keep track of the server instance to shut it down
    httpd_instance = None

    class OAuthCallbackHandler(http.server.SimpleHTTPRequestHandler):
        # Make client_id, client_secret, redirect_uri available
        _client_id = client_id
        _client_secret = client_secret
        _redirect_uri = redirect_uri
        _server_instance = None # To store httpd instance

        def do_GET(self):
            global httpd_instance
            query_components = parse_qs(urlparse(self.path).query)
            if 'code' in query_components:
                code = query_components["code"][0]
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()

                if exchange_code_for_tokens(code, self._client_id, self._client_secret, self._redirect_uri):
                    self.wfile.write(b"Authentication successful! You can close this window.")
                else:
                    self.wfile.write(b"Authentication failed. Check the console for errors.")
            else:
                self.send_response(400)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(b"Failed to retrieve authorization code.")

            if self._server_instance:
                print("Attempting to shut down server from handler...")
                # self._server_instance.shutdown() # This can cause a deadlock if called from the handler thread
                # Instead, we'll set a flag or call server_close, and shutdown will be handled in the main thread
                self._server_instance.server_close()


    port = 8080
    # httpd = None # Replaced by httpd_instance
    try:
        # httpd = socketserver.TCPServer(("", port), OAuthCallbackHandler)
        with socketserver.TCPServer(("", port), OAuthCallbackHandler) as httpd:
            httpd_instance = httpd # Store instance for handler
            OAuthCallbackHandler._server_instance = httpd # Pass server instance to handler
            print(f"Starting local server on port {port} to listen for OAuth redirect...")
            httpd.serve_forever() # This will block until server_close is called from handler
            print("Server has been closed.") # This line will be reached after server_close()
    except OSError as e:
        if e.errno == 98: # Address already in use
            print(f"Error: Port {port} is already in use. Please close the application using it and try again.")
        else:
            print(f"Failed to start server: {e}")
    except KeyboardInterrupt:
        print("Server manually interrupted.")
    finally:
        if httpd_instance: # Check if httpd_instance was assigned
            print("Ensuring server is shut down...")
            httpd_instance.shutdown() # Cleanly shutdown
            httpd_instance.server_close() # Ensure it's closed
        else: # If server failed to start (e.g. port in use), httpd_instance might be None
            print("Server was not started or already shut down.")


# --- Patreon API Interaction ---
def sanitize_filename(filename):
    """Sanitizes a string to be a valid filename."""
    return re.sub(r'[^\w\.-]', '_', filename)

def get_creator_id_from_url(patreon_url):
    """
    Placeholder function to extract creator ID from URL.
    For now, prompts the user for Campaign ID directly.
    """
    # A more robust implementation would parse the URL.
    # e.g. https://www.patreon.com/creatorName -> creatorName
    # However, campaign IDs are numerical and not always the same as username.
    print("\n--- Campaign Selection ---")
    print("To fetch posts, you need the Campaign ID of the creator (this is a number).")
    print("You can usually find this by:")
    print("1. Going to the creator's Patreon page.")
    print("2. Looking at the URL. If it's like `https://www.patreon.com/campaigns/123456/overview` the ID is `123456`.")
    print("3. Or by inspecting network requests in your browser's developer tools when viewing their page or posts.")
    print("If you are a patron, the campaign ID is often part of the URL when you view their posts or membership details.")
    campaign_id = input("Please enter the numerical Patreon Campaign ID: ")
    return campaign_id.strip()

def download_image(url, folder_path, filename_prefix="image"):
    """Downloads an image from a URL into the specified folder."""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status() # Raise an exception for HTTP errors

        # Try to get original filename from URL or Content-Disposition
        original_filename = ""
        if 'content-disposition' in response.headers:
            disp = response.headers['content-disposition']
            fn_match = re.search(r'filename="?([^"]+)"?', disp)
            if fn_match:
                original_filename = fn_match.group(1)
        if not original_filename:
            original_filename = url.split('/')[-1].split('?')[0] # Get from URL path

        sanitized_original_filename = sanitize_filename(original_filename)
        if not sanitized_original_filename: # if original name was all invalid chars
             sanitized_original_filename = f"{filename_prefix}_{urlparse(url).path.split('/')[-1]}"


        # Ensure filename has an extension, default to .jpg if not obvious
        if not os.path.splitext(sanitized_original_filename)[1]:
            content_type = response.headers.get('content-type')
            if content_type:
                if 'jpeg' in content_type: sanitized_original_filename += '.jpg'
                elif 'png' in content_type: sanitized_original_filename += '.png'
                elif 'gif' in content_type: sanitized_original_filename += '.gif'
                else: sanitized_original_filename += '.jpg' # Default
            else:
                 sanitized_original_filename += '.jpg' # Default

        filepath = os.path.join(folder_path, sanitize_filename(sanitized_original_filename))

        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"    Downloaded image: {filepath}")
        return filepath
    except requests.exceptions.RequestException as e:
        print(f"    Error downloading image {url}: {e}")
        return None
    except IOError as e:
        print(f"    Error saving image {url}: {e}")
        return None


def generate_post_html(post_data, downloaded_image_details, campaign_download_dir, post_id_str):
    """Generates an HTML file for the post."""
    title = post_data.get('title', 'Untitled Post')
    content_html = post_data.get('content_html', '<p>No content.</p>')
    author_name = post_data.get('author_name', 'Unknown Author')
    published_date = post_data.get('published_at', 'Unknown Date')
    patreon_post_url = post_data.get('patreon_post_url', '#')

    # Modify image paths in content_html to be local
    soup = BeautifulSoup(content_html, 'html.parser')
    # It's complex to map embedded images to downloaded ones without unique IDs.
    # For now, we'll primarily focus on images from the 'images' relationship or attachments.
    # If an image in content_html has a src matching a downloaded image's original URL, we could replace it.
    # This part is a placeholder for more advanced src replacement.
    # For now, we will list downloaded images separately if they are not already in the content.

    # Append images that were downloaded via relationships if not obviously in content
    # This is a simplification. A robust solution would check if an image (by URL)
    # is already present in soup before appending.
    appended_images_html = ""
    for img_detail in downloaded_image_details:
        # Construct a relative path from the post's HTML file to the image
        # HTML is in post_id_str/index.html, images are in post_id_str/images/filename
        relative_img_path = os.path.join("images", img_detail['filename'])
        appended_images_html += f'<p><img src="{relative_img_path}" alt="{sanitize_filename(img_detail["filename"])}"></p>\n'


    html_structure = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 0; padding: 0; background-color: #f9f9f9; color: #333; }}
        .page-container {{ display: flex; justify-content: center; padding: 20px; }}
        .post-container {{ background-color: #fff; width: 100%; max-width: 800px; border: 1px solid #e1e1e1; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); overflow: hidden; }}
        .post-header {{ padding: 25px 30px; border-bottom: 1px solid #e1e1e1; }}
        .post-title {{ font-size: 2.2em; margin: 0 0 10px; color: #111; }}
        .post-meta {{ font-size: 0.95em; color: #555; margin-bottom: 10px; }}
        .post-meta a {{ color: #0576b9; text-decoration: none; }}
        .post-meta a:hover {{ text-decoration: underline; }}
        .post-content-container {{ padding: 25px 30px; }}
        .post-content {{ font-size: 1.1em; line-height: 1.7; }}
        .post-content img, .post-content video, .post-content iframe {{ max-width: 100%; height: auto; display: block; margin: 20px auto; border-radius: 4px; }}
        .post-content pre {{ background-color: #f3f3f3; padding: 15px; border-radius: 4px; overflow-x: auto; }}
        .post-content blockquote {{ border-left: 3px solid #0576b9; margin-left: 0; padding-left: 20px; color: #444; font-style: italic; }}
        .downloaded-media-section {{ margin-top: 30px; padding-top: 20px; border-top: 1px dashed #ccc; }}
        .downloaded-media-section h3 {{ font-size: 1.5em; color: #333; margin-bottom: 15px; }}
        /* Add more styles as needed */
    </style>
</head>
<body>
    <div class="page-container">
        <div class="post-container">
            <div class="post-header">
                <h1 class="post-title">{title}</h1>
                <p class="post-meta">By {author_name} on {published_date}</p>
                <p class="post-meta">Original Patreon Post: <a href="{patreon_post_url}" target="_blank">{patreon_post_url}</a></p>
            </div>
            <div class="post-content-container">
                <div class="post-content">
                    {content_html}
                </div>
                <div class="downloaded-media-section">
                    <h3>Downloaded Media:</h3>
                    {appended_images_html if appended_images_html else "<p>No separate media files were downloaded for this post (they may be embedded above, or there were none).</p>"}
                </div>
            </div>
        </div>
    </div>
</body>
</html>
    """

    post_html_path = os.path.join(campaign_download_dir, post_id_str, "index.html")
    try:
        with open(post_html_path, 'w', encoding='utf-8') as f:
            f.write(html_structure)
        print(f"  Saved HTML: {post_html_path}")
        return post_html_path
    except IOError as e:
        print(f"  Error saving HTML for post {post_id_str}: {e}")
        return None

def fetch_posts(api_client, campaign_id):
    """Fetches posts, downloads assets, and saves them as HTML."""
    print(f"\nFetching posts for campaign ID: {campaign_id}...")

    campaign_download_dir = os.path.join(DOWNLOAD_DIR, sanitize_filename(str(campaign_id)))
    os.makedirs(campaign_download_dir, exist_ok=True)

    all_posts_processed_count = 0
    cursor = None

    try:
        while True:
            print(f"\nFetching page of posts (cursor: {cursor})...")
            # Include more fields for content and relationships for media
            try:
                response = api_client.get_posts_by_campaign(
                    campaign_id,
                    params={'page[cursor]': cursor if cursor else '', 'sort': '-published_at'},
                    includes=['user', 'images', 'attachments'], # 'images' for post images, 'attachments' for other files
                    fields={
                        'post': ['title', 'content', 'published_at', 'url', 'embed_data', 'embed_url', 'is_public'], # 'content' is usually HTML
                        'user': ['full_name'],
                        'attachment': ['name', 'url'], # For attachments
                        'media': ['download_url', 'file_name', 'mimetype'] # For images often under 'images' relationship or via media API
                    }
                )
                # response.load() # Not always necessary, data() call below usually loads.
            except AttributeError as e:
                if 'get_posts_by_campaign' in str(e).lower(): # Make check case-insensitive
                    print("\nERROR: Your version of the 'patreon' library is outdated and missing the 'get_posts_by_campaign' feature.")
                    print("This is essential for fetching posts.")
                    print("Please update the library by running: pip install --upgrade patreon")
                    print(f"Details: {e}\n")
                else:
                    # An AttributeError not related to get_posts_by_campaign occurred
                    print(f"An unexpected AttributeError occurred during API call setup or execution: {e}")
                    print(traceback.format_exc())
                return # Exit fetch_posts if this critical call fails

            posts_data = response.data()
            if not posts_data:
                print("No more posts found on this page or campaign.")
                break

            # Process included data for easier lookup
            included_data = {item.id(): item for item in response.included()} if response.included() else {}


            for post_obj in posts_data:
                all_posts_processed_count += 1
                title = post_obj.attribute('title') or "Untitled Post"
                published_at = post_obj.attribute('published_at')
                patreon_post_url = post_obj.attribute('url')
                content_html = post_obj.attribute('content') or ""
                post_id_str = post_obj.id()

                print(f"\nProcessing Post ID: {post_id_str} - Title: {title}")

                # Create post-specific directory
                post_download_dir = os.path.join(campaign_download_dir, sanitize_filename(post_id_str))
                post_images_dir = os.path.join(post_download_dir, "images")
                os.makedirs(post_images_dir, exist_ok=True)

                author_name = "Unknown Author"
                if post_obj.relationship('user'):
                    user_id = post_obj.relationship('user').data()['id']
                    author_data = included_data.get(user_id)
                    if author_data:
                        author_name = author_data.attribute('full_name') or author_name

                post_data_for_html = {
                    'title': title,
                    'content_html': content_html,
                    'author_name': author_name,
                    'published_at': published_at,
                    'patreon_post_url': patreon_post_url,
                    'id': post_id_str
                }

                downloaded_asset_details = []

                # Download images explicitly listed in 'images' relationship
                if post_obj.relationship('images') and post_obj.relationship('images').data():
                    print("  Found images in 'images' relationship...")
                    for img_ref in post_obj.relationship('images').data():
                        img_data = included_data.get(img_ref['id'])
                        if img_data and img_data.type() == 'media': # Ensure it's a media object
                            img_url = img_data.attribute('download_url')
                            img_filename = img_data.attribute('file_name')
                            if img_url and img_filename:
                                local_path = download_image(img_url, post_images_dir, filename_prefix=sanitize_filename(img_filename))
                                if local_path:
                                    downloaded_asset_details.append({'type': 'image', 'path': local_path, 'filename': os.path.basename(local_path)})
                            else:
                                print(f"    Skipping image data with missing URL or filename: {img_data.id()}")

                # Download attachments (if any)
                if post_obj.relationship('attachments') and post_obj.relationship('attachments').data():
                    print("  Found attachments...")
                    for att_ref in post_obj.relationship('attachments').data():
                        att_data = included_data.get(att_ref['id'])
                        # Assuming attachments also use 'download_url' and 'file_name' or similar
                        # The schema for 'attachment' might differ, adjust if necessary
                        if att_data: # Check if attachment data is present in included
                            att_url = att_data.attribute('url') # This is often the case for attachments
                            att_name = att_data.attribute('name') # Filename
                            if att_url and att_name:
                                # Attachments go into the main post_download_dir, not 'images' unless they are images
                                # For simplicity, putting all in 'images' for now if they are downloadable files
                                # Or create an 'attachments' folder
                                attachment_folder = os.path.join(post_download_dir, "attachments")
                                os.makedirs(attachment_folder, exist_ok=True)
                                local_path = download_image(att_url, attachment_folder, filename_prefix=sanitize_filename(att_name))
                                if local_path:
                                     downloaded_asset_details.append({'type': 'attachment', 'path': local_path, 'filename': os.path.basename(local_path)})
                            else:
                                print(f"    Skipping attachment with missing URL or name: {att_data.id()}")

                generate_post_html(post_data_for_html, downloaded_asset_details, campaign_download_dir, sanitize_filename(post_id_str))

            cursor = api_client.extract_cursor(response)
            if not cursor:
                print("\nNo more pages of posts.")
                break

        print(f"\nProcessed a total of {all_posts_processed_count} posts for campaign {campaign_id}.")
        if all_posts_processed_count == 0:
            print("No posts were found for this campaign, or you may not have access to them (or the campaign is empty).")

    except requests.exceptions.HTTPError as e:
        print(f"A Patreon API HTTP error occurred while fetching posts: {e}")
        if e.response is not None:
            print(f"Status Code: {e.response.status_code}")
            try:
                error_details = e.response.json()
                print(f"Error details: {error_details}")
            except ValueError: # If response is not JSON
                print(f"Error response (text): {e.response.text}")

            if e.response.status_code == 401:
                print(f"Authentication error (401): Your access token might be invalid or expired. Consider deleting {TOKEN_FILE} and re-running the script.")
            elif e.response.status_code == 403:
                print("Forbidden (403): You may not have permission to access these posts or campaign details. Check your patronage status for this creator.")
            elif e.response.status_code == 404:
                print("Not Found (404): The campaign or posts could not be found. Please verify the Campaign ID.")
        else:
            print("HTTPError occurred but e.response is None.")

    except requests.exceptions.RequestException as e: # Handles network errors like DNS failure, refused connection
        print(f"A network error occurred during posts fetching or asset download: {e}")
    except Exception as e:
        print(f"An unexpected error occurred in fetch_posts: {e}")
        print(traceback.format_exc())


# --- Main Execution ---
if __name__ == "__main__":
    # Ensure download directory exists
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    access_token = load_or_refresh_tokens()

    if access_token:
        print("\nSuccessfully obtained access token.")
        api_client = patreon.API(access_token)

        # --- Get User Identity (Optional, good for checking token) ---
        # Advise user to update patreon library if AttributeErrors occur here.
        try:
            print("Fetching user identity to confirm token validity (ensure 'patreon' library is up-to-date)...")
            user_response = api_client.get_identity(includes=['memberships'])
            user_data = user_response.data()
            if user_data:
                user_name = user_data.attribute('full_name')
                print(f"Authenticated as: {user_name}")
            else:
                # This case might happen if the token is technically valid but yields no data.
                print("Could not retrieve user data with the current token, though the call was successful.")
            # Future enhancement: Use user_response.data().relationship('memberships') to help find campaign_id
        except requests.exceptions.HTTPError as e:
            print(f"A Patreon API HTTP error occurred while fetching user identity: {e}")
            if e.response is not None:
                print(f"Status Code: {e.response.status_code}")
                try:
                    error_details = e.response.json()
                    print(f"Error details: {error_details}")
                except ValueError:
                    print(f"Error response (text): {e.response.text}")
                if e.response.status_code == 401:
                    print(f"Authentication error (401): The access token is invalid or expired. Please delete {TOKEN_FILE} and re-run to authenticate.")
                else:
                    print("The token might be invalid or there could be network issues.")
            else:
                print("HTTPError occurred but e.response is None.")
            # Potentially exit if identity check fails critically
            # print("Exiting due to identity check failure.")
            # exit()
        except AttributeError as e:
            print(f"An AttributeError occurred while fetching user identity: {e}")
            print("This might be due to an outdated 'patreon' library. Try running: pip install --upgrade patreon")
        except Exception as e:
            print(f"An unexpected error occurred in main fetch_posts loop: {e}")
            print(traceback.format_exc())


        # --- Fetch Posts from a Campaign ---
        campaign_id_input = get_creator_id_from_url(None) # URL not used yet

        if campaign_id_input and campaign_id_input.isdigit():
            fetch_posts(api_client, campaign_id_input)
        else:
            print("Invalid or no Campaign ID provided. Exiting. Campaign ID should be a number.")

    else:
        print("Could not obtain access token. Exiting.")
