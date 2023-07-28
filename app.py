# Streamlit App to use Amazon Rekognition API

import streamlit as st
import os
from PIL import Image
import tempfile
import logging
import zipfile
import io
from io import BytesIO
import base64
import shutil
import datetime
import re
from zipfile import ZipFile, ZIP_STORED
import google.auth
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account
from datetime import datetime
import threading
from multiprocessing import Pool
from googleapiclient import errors
import time
from google_auth_oauthlib.flow import InstalledAppFlow
import requests
import json
from google.oauth2.credentials import Credentials
import webbrowser
import random
from PIL import ImageOps, ExifTags
import uuid
import glob
from streamlit_javascript import st_javascript
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from googleapiclient.http import MediaFileUpload
import traceback
import pyheif
from urllib.parse import urlparse, parse_qs
from pickle_functions import process_folder, process_file, process_file_wrapper, create_folder_wrapper, save_file_locally, delete_list, create_list, upload_file

logging.basicConfig(level=logging.INFO)

st.set_option('deprecation.showfileUploaderEncoding', False)
st.set_page_config(
    page_title='SmartLabel',
    page_icon='camera'
)   
hide_streamlit_style = """ <style> #MainMenu {visibility: hidden;} footer {visibility: hidden;} </style> """ 
st.markdown(hide_streamlit_style, unsafe_allow_html=True)


if 'last_uploaded_file' not in st.session_state:
    st.session_state['last_uploaded_file'] = None
    st.session_state['download_zip_created'] = False
    st.session_state['creds'] = None
    # delete_list('your-colleciton-id')
    st.session_state['begin_auth'] = False
    st.session_state['final_auth'] = False
    st.session_state['cache'] = {
                                    "links": [],
                                    "labeled_files": [],
                                    "file_progress": 0,
                                    "created_folders": [],
                                    "folder_progress": 0
                                }

st.title("Leadership Initiatives Photo Labeler")
st.caption("By Giacomo Pugliese")
with st.expander("Click to view full directions for this site"):
    st.subheader("User Credentials")
    st.write("- Either create or insert an existing program id to log into intern database. A program ID is needed for all parts of the site.")
    st.write("- If needed, there are options to view all programs in the system and delete uneeded accounts.")
    st.write("- Authenticate with Google before performing any actions. Google authentication is needed for all parts of this site.")
    st.subheader("Configure Training Data")
    st.write("- For the training data upload via google drive, upload a folder with all of the intern's folders, and ensure each folder has at least one solo image that begins with 'FIRST LAST - Bio' (i.e. Giacomo Pugliese  - Bio - Middle School Jumpstart Program - July 9th .jpg).")
    st.write("- Alternatively, create student profiles and upload solo images of them to train the AI. All names must be in format FIRST_LAST.")
    st.write("- Delete student profile to clear their training data if needed.")
    st.subheader("Interns in System")
    st.write("- Displays all of the interns currently in your program's AI.")
    st.subheader("Detect Interns in Photos")
    st.write("- Insert a comma seperated list of the folder links of your google drive containing intern photos.")
    st.write("- Add a destination drive folder if you want the labeled intern folders to go somewhere different than the folder containing the input photos.")
    st.write("- Click 'Start Labeling' and allow the AI to sort the images into individual student folders directly into the drive.")
    st.write("- When sorting, please don't leave the tab and keep background processes on your computer to a minimum. Note that a weak internet connection may cause unexpected behavior, so please ensure a stable connection.")
    st.subheader("Renaming tool")
    st.write("- Insert the folder link of your google drive folder containing program's students at a particular location. All images must be in format FIRST_LAST_YEAR_IMAGE_NAME (i.e. 'Giacomo_Pugliese_2023_img629.jpg).")
    st.write("- Choose the custom file ending for that location (i.e. ending would be '_Jumpstart_Group_1' for a file you want named 'Giacomo_Pugliese_2023_Jumpstart_Group_1').")
    st.write("- Click 'Start Renaming' and have the renamed pictures go right into the drive folder.")


st.header('User Credentials')
st.subheader("Program Login")

col1, col2= st.columns(2)
deleted_list = 0
display_programs = 0

with col1:
    list_id = st.text_input("Enter your program ID to sign in", "")
    if list_id == '':
        list_id = 'your-default-list-id'
    create_list(list_id)
    if st.button("View programs"):
        lists = list_lists()
        if lists:
            display_programs = 1
        else:
            display_programs = 2

with col2:
    deleted_program = st.text_input("Enter program ID to delete")
    if st.button("Delete this program") and deleted_program != 'your-default-list-id':
            if(deleted_program not in list_lists()):
                st.error("Program ID doesn't exist")
            else:
                delete_list(deleted_program)
                list_id = 'your-default-list-id'
                deleted_list = 1

if(display_programs == 1):
    st.info(f"Current programs: {', '.join(lists)}")
    display_programs = 0
elif(display_programs == 2):
    st.info("No programs created yet!")

if(deleted_list == 1):
    st.info("Program deleted from system")
    deleted_list = 0



st.subheader("Google authentication")

def nav_to(url):
    nav_script = """
        <meta http-equiv="refresh" content="0; url='%s'">
    """ % (url)
    st.write(nav_script, unsafe_allow_html=True)
try:
    if st.button("Authenticate Google Account"):
        st.session_state['begin_auth'] = True
        # Request OAuth URL from the FastAPI backend
        response = requests.get(f"{'https://photo-labeler-842ac8d73e7a.herokuapp.com'}/auth?user_id={list_id}")
        if response.status_code == 200:
            # Get the authorization URL from the response
            auth_url = response.json().get('authorization_url')
            st.markdown(f"""
                <a href="{auth_url}" target="_blank" style="color: #8cdaf2;">
                    Click to continue to authentication page (before finalizing)


                </a>
                """, unsafe_allow_html=True)
            st.text("\n\n\n")
            # Redirect user to the OAuth URL
            # nav_to(auth_url)

    if st.session_state['begin_auth']:    
        if st.button("Finalize Google Authentication"):
            with st.spinner("Finalizing authentication..."):
                for i in range(6):
                    # Request token from the FastAPI backend
                    response = requests.get(f"{'https://photo-labeler-842ac8d73e7a.herokuapp.com'}/token/{list_id}")
                    if response.status_code == 200:
                        st.session_state['creds'] = response.json().get('creds')
                        print(st.session_state['creds'])
                        st.success("Google account successfully authenticated!")
                        st.session_state['final_auth'] = True
                        break
                    time.sleep(1)
            if not st.session_state['final_auth']:
                st.error('Experiencing network issues, please refresh page and try again.')
                st.session_state['begin_auth'] = False
except:
    pass


# Add a person or image, or delete a person
st.header('Configure Training Data')


# Create a directory named after the list
os.makedirs(list_id, exist_ok=True)

st.subheader("Add training data using google drive folder")
# Drive directory link for bulk training data
training_data_directory_link = st.text_input("Enter a Google Drive directory link for bulk training data")

if st.button('Process Training Data'):
    if not st.session_state['final_auth']:
        st.error("Please authenticate with google!")
    elif list_id == 'your-default-list-id':
        st.error("Please enter a program id!")
    else:
        with st.spinner("Downloading training data..."):
            # Add a list to keep track of interns without training data
            interns_without_training_data = []
            
            # Google Drive service setup
            CLIENT_SECRET_FILE = 'credentials.json'
            API_NAME = 'drive'
            API_VERSION = 'v3'
            SCOPES = ['https://www.googleapis.com/auth/drive']

            with open(CLIENT_SECRET_FILE, 'r') as f:
                client_info = json.load(f)['web']

            creds_dict = st.session_state['creds']
            creds_dict['client_id'] = client_info['client_id']
            creds_dict['client_secret'] = client_info['client_secret']
            creds_dict['refresh_token'] = creds_dict.get('_refresh_token')

            # Create Credentials from creds_dict
            creds = Credentials.from_authorized_user_info(creds_dict)

            # Call the Drive v3 API
            service = build(API_NAME, API_VERSION, credentials=creds)
            # Extracting the folder ID from the link
            training_data_directory_id = training_data_directory_link.split('/')[-1]

            # Step 1: Get the 'Training Images' directory ID
            query = f"'{training_data_directory_id}' in parents and trashed = false and mimeType = 'application/vnd.google-apps.folder' and name = 'Training Images'"
            Training_Images = service.files().list(q=query).execute().get('files', [])

                
            query = f"'{training_data_directory_id}' in parents and trashed = false and mimeType = 'application/vnd.google-apps.folder'"
            intern_folders = service.files().list(q=query).execute().get('files', [])

            progress_report = st.empty()
            progress_report.text(f"Initializing training data...")
            i = 1
            # Check if 'Training Images' folder exists in the parent directory. If not, create it.
            query = f"'{training_data_directory_id}' in parents and name='Training Images' and trashed = false"
            results = service.files().list(q=query).execute().get('files', [])
            total_interns = len(intern_folders)

            if results:
                training_images_folder_id = results[0]['id']
                total_interns = total_interns - 1
            else:
                file_metadata = {
                    'name': 'Training Images',
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents': [training_data_directory_id]
                }
                training_images_folder = service.files().create(body=file_metadata, fields='id').execute()
                training_images_folder_id = training_images_folder['id']
            with ProcessPoolExecutor(max_workers=15) as executor:
                futures = []
                for folder in intern_folders:
                    future = executor.submit(process_folder, folder, service, list_id, training_data_directory_id)
                    futures.append(future)

                interns_without_training_data = []
                for future in as_completed(futures):
                    # If process_folder returns a result, handle it here
                    result = future.result()  # result is either None or the error_name
                    if result is not None:  # if the result is not None, an error has occurred
                        interns_without_training_data.append(result)
                    progress_report.text(f"Training progress: {i}/{len(intern_folders)}")
                    i = i +1

        # After all interns have been processed, if there were interns without training data, display a Streamlit error
        if interns_without_training_data:
            interns_without_training_data = [intern for intern in interns_without_training_data if intern != 'Training Images']
            st.error(f"The following interns have no properly formatted training data: {', '.join(interns_without_training_data)}")
        st.success("Program training complete!")

st.subheader("Add training data manually")
person_name = st.text_input("Enter the intern's name")
person_image = st.file_uploader('Upload a solo image of the intern', type=['jpg', 'png'])

col1, col2, col3, col4, col5 = st.columns(5)

if st.button('Add this image'):
    if(list_id == 'your-default-list-id'):
        st.error("Please enter a program id!")
    elif not re.match(r"^[A-Za-z]+_[A-Za-z]+$", person_name):  
        st.error("Please enter the person's name in the format Firstname_Lastname")
    else:
        if person_name and person_image and list_id:
            # Save the image locally
            file_path = save_file_locally(person_image, person_name)
            with open(file_path, "rb") as f:
                upload_success = upload_file(f, 'giacomo', person_name)
            if upload_success:
                # Check if person already exists
                if person_name not in list_faces_in_list(list_id):
                    add_faces_to_list('giacomo', person_name, list_id, person_name)
                    st.write('Intern added successfully')
                else:
                    # If person already exists, just add the image to the person's existing images in the list
                    st.write('Image added to existing person')
                # Clear the input fields
                person_name = None
                person_image = None
            else:
                st.write('Failed to upload image')
        else:
            st.error('Please enter a name, upload an image, and provide a program id')

if st.button('Delete intern'):
    if(list_id == 'your-default-list-id'):
        st.error("Please enter a program id!")
    else:
        if person_name and list_id:
            # Find the faceId of the person to delete
            face_id = next((face['FaceId'] for face in client.list_faces(listId=list_id)['Faces'] 
                            if face['ExternalImageId'] == person_name), None)
            if face_id:
                delete_face_from_list(list_id, face_id)
                st.write(f'Intern {person_name} deleted successfully')
            else:
                st.write(f'Intern {person_name} not found')
        else:
            st.write('Please enter an intern name and program id to delete')


# Display the list of person names
person_names = list_faces_in_list(list_id)
st.header(f'Interns in System ({len(person_names)})')
st.write(', '.join(person_names))
if len(person_names) == 0:
    'No interns added yet.'
st.button("Refresh page")

########################################################################################
#    DETECT SECTION


st.header('Detect Interns in Photos')
folder_links = st.text_area('Enter Google Drive Folder links (comma separated)')
destination_folder_link = st.text_input('Enter Google Drive Destination Folder link (Optional)')
st.caption("Warning: A weak wifi connection can lead to unexpected behavior, so please ensure a stable connection.")
start_processing = st.button('Start Labeling')

try:
    links = [folder_links, destination_folder_link]
    if links != st.session_state['cache']['links']:
        st.session_state['cache'] = {
                                        "links": links,
                                        "labeled_files": [],
                                        "file_progress": 0,
                                        "created_folders": [],
                                        "folder_progress": 0
                                    }
except:
    pass

if start_processing:
    try:
        flag = False
        if not folder_links:
            st.error("Please upload your google drive folders")
        elif list_id == 'your-default-list-id':
            st.error("Please enter a program id!")
        elif not st.session_state['final_auth']:
            st.error("Please authenticate with google!")
        else:
            folders = [x.strip() for x in folder_links.split(',')]
            match_dest = re.search(r'\/([a-zA-Z0-9-_]+)$', destination_folder_link) if destination_folder_link else None
            folder_ids = []
            error = False
            for folder_link in folders:
                match = re.search(r'\/([a-zA-Z0-9-_]+)$', folder_link)
                if(match is None):
                    st.error(f'Invalid Google Drive link: {folder_link}. Please make sure the link is correct.')
                    error = True
                    break
                else:
                    folder_id = match.group(1)
                    folder_ids.append(folder_id)
            if not error:
                # If destination_folder_link is provided and valid, replace folder_id with destination_folder_id
                destination_folder_id = match_dest.group(1) if match_dest else folder_ids[0]

                CLIENT_SECRET_FILE = 'credentials.json'
                API_NAME = 'drive'
                API_VERSION = 'v3'
                SCOPES = ['https://www.googleapis.com/auth/drive']

                with open(CLIENT_SECRET_FILE, 'r') as f:
                    client_info = json.load(f)['web']

                creds_dict = st.session_state['creds']
                creds_dict['client_id'] = client_info['client_id']
                creds_dict['client_secret'] = client_info['client_secret']
                creds_dict['refresh_token'] = creds_dict.get('_refresh_token')
                try:
                    # Create Credentials from creds_dict
                    creds = Credentials.from_authorized_user_info(creds_dict)

                    # Call the Drive v3 API
                    service = build(API_NAME, API_VERSION, credentials=creds)
                except:
                    st.error("Please refresh the page and retry Google authentication.")

                
                with st.spinner("Creating folders"):
                    progress_report_folder = st.empty()
                    progress_report_folder.text("Processing folders...")
                    person_folder_dict = {}
                    removed_folders = [person for person in person_names if person not in st.session_state['cache']['created_folders']] 
                    removed_folders.append("Group Photos")
                    arguments = [(service, destination_folder_id, person) for person in removed_folders]
                    completed_folders = 0
                    
                    with ProcessPoolExecutor(max_workers=15) as executor:
                        futures = {executor.submit(create_folder_wrapper, arg): arg for arg in arguments}
                        for future in as_completed(futures):
                            try:
                                person, folder = future.result()
                                person_folder_dict[person] = folder
                                st.session_state['cache']['created_folders'].append(folder['name'])
                                st.session_state['cache']['folder_progress'] +=1
                                completed_folders += 1
                                progress_report_folder.text(f"Folder creation progress: {max(st.session_state['cache']['folder_progress'], completed_folders)}/{len(arguments)}")
                            except:
                                pass

                with st.spinner("Labeling images.."):
                    progress_report = st.empty()
                    if not os.path.exists(f'{list_id}/labels'):
                        os.makedirs(f'{list_id}/labels')
                    total_files = 0
                    labeled_files = 0
                    person_images_dict = {
                        'Group Photos': []
                    }
                    group_photo_threshold = 13
                    for folder_id in folder_ids:
                        page_token = None

                        # retrieve total amount of files
                        while True:  # added loop for pagination
                            response = make_request_with_exponential_backoff(service.files().list(q=f"'{folder_id}' in parents and trashed=false and mimeType != 'application/vnd.google-apps.folder'",
                                                                                                spaces='drive',
                                                                                                fields='nextPageToken, files(id, name)',
                                                                                                pageToken=page_token,
                                                                                                pageSize=200))
                            items = response.get('files', [])
                            total_files += len(items)

                            page_token = response.get('nextPageToken', None)
                            if page_token is None:
                                break

                    progress_report.text(f"Processing photos...")

                    for folder_id in folder_ids:
                        try:
                            page_token = None

                            while True:
                                response = make_request_with_exponential_backoff(service.files().list(q=f"'{folder_id}' in parents and trashed=false and mimeType != 'application/vnd.google-apps.folder'",
                                                                                                    spaces='drive', 
                                                                                                    fields='nextPageToken, files(id, name)',
                                                                                                    pageToken=page_token,
                                                                                                    pageSize=1000))
                                items = response.get('files', [])
                                print(items)
                                new_items = [file for file in items if file['name'] not in st.session_state['cache']['labeled_files']]
                                items = new_items
                                print(st.session_state['cache']['labeled_files'])

                                arguments = [(file, service, destination_folder_id, person_images_dict, group_photo_threshold, list_id, person_folder_dict,) for file in items]
                                with ProcessPoolExecutor(max_workers=15) as executor:
                                    futures = {executor.submit(process_file_wrapper, arg): arg for arg in arguments}
                                    for future in as_completed(futures):
                                        try:
                                            # Handling the future completion
                                            result = future.result()  # replace with appropriate handling if process_file_wrapper returns something
                                            st.session_state['cache']['labeled_files'].append(result)
                                            print('result: ' + result)
                                            labeled_files += 1
                                            st.session_state['cache']['file_progress'] += 1
                                            print(st.session_state['cache']['file_progress'])
                                            remaining_time = (total_files - max(labeled_files, st.session_state['cache']['file_progress'])) * (1/30)
                                            flag = True
                                            progress_report.text(f"Labeling progress: {max(labeled_files, st.session_state['cache']['file_progress'])}/{total_files} ({round(remaining_time, 1)} minutes remaining)")
                                        except Exception as e:
                                            print (e)
                                        

                                page_token = response.get('nextPageToken', None)
                                if page_token is None:
                                    break
                        except:
                            pass
                    consolidate_labels(list_id)

                    if not flag:
                        progress_report.text("")
                        progress_report_folder.text("")

                    st.session_state['download_zip_created'] = True  
                    st.success("All photos labeled successfully!")
    except Exception as e:
        st.error(f'Experiencing network issues, please refresh page and try again: {e}')


if 'download_zip_created' in st.session_state and st.session_state['download_zip_created']:  
    try:
        drive_link = destination_folder_link if destination_folder_link != '' else folders[0]
        st.markdown(f"""
                <a href="{drive_link}" target="_blank" style="color: #8cdaf2;">
                    Click to view sorted photos


                </a>
                """, unsafe_allow_html=True)
        st.text("\n\n\n")        
        with open(f'{list_id}/labels.txt', 'r') as f:
            st.download_button(
                label="Download all textual labels",
                data=f.read(),
                file_name='labels.txt',
                mime='text/plain'
            )
    except:
        pass


 
##############################################################################################

def extract_drive_id(drive_link):
    """
    Extract the Google Drive ID from a URL

    Args:
    drive_link : str : Google Drive URL

    Returns:
    str : Google Drive ID extracted from the URL
    """
    url_parsed = urlparse(drive_link)

    if url_parsed.netloc == "drive.google.com":
        if url_parsed.path.startswith('/drive/folders/'):
            return url_parsed.path.split('/')[3]
        if url_parsed.path.startswith('/open'):
            return parse_qs(url_parsed.query)['id'][0]

    return None

# Initial Streamlit layout
st.header('Naming Tool')
folder_link_or_id = st.text_input('Enter Google Drive Folder Link for Renaming')
file_name_ending = st.text_input('Enter your custom file name ending')
start_renaming = st.button('Start Renaming')

if start_renaming and folder_link_or_id:
    if not folder_link_or_id:
        st.error("Please upload your Google Drive folder")
    elif not st.session_state.get('final_auth'):
        st.error("Please authenticate with Google!")
    else:
        # Parse folder id from link or use direct id
        match = re.search(r'\/([a-zA-Z0-9-_]+)$', folder_link_or_id)
        if match is not None:
            folder_id_rename = match.group(1)
        else:
            folder_id_rename = folder_link_or_id


        # Load client info from the oauth credentials file
        with open('credentials.json', 'r') as f:
            client_info = json.load(f)['web']

        creds_dict = st.session_state.get('creds')
        creds_dict['client_id'] = client_info['client_id']
        creds_dict['client_secret'] = client_info['client_secret']
        creds_dict['refresh_token'] = creds_dict.get('_refresh_token')

        # Create Credentials from creds_dict
        creds = Credentials.from_authorized_user_info(creds_dict)

        # Build the service
        service = build('drive', 'v3', credentials=creds)

        try:
            # Request files in the folder
            results = service.files().list(q=f"'{folder_id_rename}' in parents").execute()
            items = results.get('files', [])

            if not items:
                st.error("No files found.")
            else:
                total_files = len(items)
                progress_report = st.empty()  # Create a placeholder for the progress report

                # Define a function to perform the renaming
                def rename_file(file, curr_year):
                    try:
                        # Extract file extension
                        file_ext = os.path.splitext(file['name'])[1]
                        year_str = f'_{curr_year}_'

                        if year_str in file['name']:
                            # Remove all characters past '_{curr_year}_' in the file name
                            new_file_name = re.sub(rf'{year_str}.*', '', file['name'])

                            # Append the custom file name ending and the file extension
                            new_file_name += f'{year_str}{file_name_ending}{file_ext}'

                            # Rename the file
                            service.files().update(fileId=file['id'], body={"name": new_file_name}).execute()

                    except Exception as e:
                        st.write(f"Error renaming {file['name']}: {e}")


                # Use a ThreadPoolExecutor to perform the renames in parallel
                with ProcessPoolExecutor(max_workers=10) as executor:
                    curr_year =  datetime.now().year  # replace with the current year or however you are getting the current year
                    futures = {executor.submit(rename_file, file, curr_year): file for file in items}
                    for i, future in enumerate(as_completed(futures), start=1):
                        progress_report.text(f"Renaming progress: ({i}/{total_files})")  # Update the text in the placeholder


                st.success("All files renamed successfully!")
                st.markdown(f"""
                <a href="{folder_link_or_id}" target="_blank" style="color: #8cdaf2;">
                    Click to continue to view renamed images


                </a>
                """, unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Please enter a valid and properly formatted drive folder!")