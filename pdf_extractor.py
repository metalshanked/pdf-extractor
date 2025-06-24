"""
PDF Extractor - A Streamlit application to extract metadata from PDF files.

This application allows users to:
- Upload one or multiple PDF files
- Extract and view metadata from each PDF
- Extract and view the text content of each PDF
- Export metadata from all PDFs to a CSV file

To run this application from a base path called "/pdf":
1. Navigate to the directory containing this file
2. Run the following command:
   streamlit run pdf_extractor.py --server.baseUrlPath="/pdf"

This will start the Streamlit server with the application accessible at:
http://localhost:8501/pdf
"""

import streamlit as st
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdftypes import resolve1
from pdfminer.high_level import extract_text
import tempfile
import os
import pandas as pd
import io
from typing import List, Dict, Tuple, Any, Optional, BinaryIO, Union
from datetime import datetime

def metadata_to_dataframe(files_metadata: List[Tuple[str, Dict[str, Any], List[str], Optional[str]]], 
                      include_data: bool = False) -> pd.DataFrame:
    """
    Convert metadata from multiple PDF files to a pandas DataFrame for CSV export.

    This function takes the extracted metadata from multiple PDF files and organizes it
    into a structured DataFrame format suitable for CSV export. It handles special cases
    like XML metadata and optionally includes the full text content of the PDFs.

    Args:
        files_metadata: A list of tuples containing (filename, metadata, metadata_types, pdf_content)
                        where metadata is a dictionary of key-value pairs
        include_data: Boolean indicating whether to include PDF text data in the export

    Returns:
        A pandas DataFrame with the metadata in a format suitable for CSV export
    """
    rows = []

    for file_info in files_metadata:
        filename, metadata, _ = file_info[:3]
        # Base row with filename
        base_row = {"Filename": filename}

        # Add all metadata to the row
        for key, value in metadata.items():
            # Skip XML content as it's not suitable for CSV format
            if "XML" not in key:
                base_row[key] = value
            else:
                base_row["Contains_XML_Metadata"] = "Yes"

        # Include PDF text data if requested
        if include_data and len(file_info) > 3:
            pdf_content = file_info[3]
            base_row["PDF_Text_Data"] = pdf_content

        rows.append(base_row)

    # Create DataFrame from rows
    df = pd.DataFrame(rows)
    return df

def extract_pdf_content(pdf_path: str) -> str:
    """
    Extract text content from a PDF file using PDFminer.

    This function uses PDFminer's high-level extract_text function to extract
    all text content from a PDF file. It handles exceptions and returns an error
    message if the extraction fails.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        A string containing the text content of the PDF or an error message
    """
    try:
        text = extract_text(pdf_path)
        return text
    except Exception as e:
        return f"Error extracting PDF content: {str(e)}"

def extract_metadata(pdf_file: BinaryIO) -> Tuple[Dict[str, Any], List[str]]:
    """
    Extract metadata from a PDF file using PDFminer.

    This function extracts both standard document information and XMP metadata 
    (if available) from a PDF file. It handles binary data conversion and 
    character encoding issues.

    Args:
        pdf_file: A file-like object containing the PDF in binary mode

    Returns:
        A tuple containing:
            - A dictionary with all extracted metadata (keys are metadata fields, values are their content)
            - A list of metadata types found in the document (for compatibility with existing code)
    """
    # Create a PDF parser object
    parser = PDFParser(pdf_file)

    # Create a PDF document object
    document = PDFDocument(parser)

    # Get the metadata from the document
    metadata = {}
    metadata_types = []  # Keep for compatibility with existing code

    # Extract embedded XML metadata if available
    if 'Metadata' in document.catalog:
        metadata_types.append("XMP")  # Keep for compatibility
        xml_metadata = resolve1(document.catalog['Metadata']).get_data()
        metadata['XML Metadata'] = xml_metadata.decode('utf-8', errors='ignore')

    # Extract document info if available
    if document.info:
        metadata_types.append("Info")
        for info in document.info:
            for key, value in info.items():
                if isinstance(value, bytes):
                    try:
                        metadata[key] = value.decode('utf-8', errors='ignore')
                    except:
                        metadata[key] = str(value)
                else:
                    metadata[key] = str(value)

    return metadata, metadata_types

def main() -> None:
    """
    Main application function that handles the Streamlit UI and application logic.

    This function:
    1. Sets up the file upload interface in the sidebar
    2. Creates tabs for each uploaded PDF file
    3. Extracts and displays metadata and content for each PDF
    4. Provides export functionality for the extracted metadata

    Returns:
        None
    """
    # Initialize session state for storing metadata across reruns
    if 'all_files_metadata' not in st.session_state:
        st.session_state.all_files_metadata = []

    with st.sidebar:
        st.header("Upload Files")
        uploaded_files = st.file_uploader("Choose PDF files", type="pdf", accept_multiple_files=True)

        # Clear metadata when new files are uploaded
        if uploaded_files and len(uploaded_files) != len(st.session_state.all_files_metadata):
            st.session_state.all_files_metadata = []

        # # Add explanation about PDF metadata
        # with st.expander("About PDF Metadata", expanded=False):
        #     st.markdown("""
        #     ### PDF Metadata
        #
        #     PDFs can contain various metadata such as title, author, creation date, and more.
        #     This application extracts and displays all available metadata from your PDF files.
        #     """)

    if uploaded_files:
        # Create a container for tab navigation controls
        tab_nav_container = st.container()

        # Create a row with a tabs column
        tabs_col = tab_nav_container.columns(1)[0]  # Create a single column


        # Create tabs for each file
        with tabs_col:
            file_names = [file.name for file in uploaded_files]
            # Add info note about keyboard navigation when there are multiple tabs
            if len(file_names) > 1:
                st.info("💡 Tip: Use keyboard ⬅️ and ➡️ arrow keys to navigate through tabs.")

            tabs = st.tabs(file_names)


        # Process each file and display in its tab
        for i, uploaded_file in enumerate(uploaded_files):
            with tabs[i]:

                # Create a temporary file to handle the PDF
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                    temp_file.write(uploaded_file.getvalue())
                    temp_file_path = temp_file.name

                # Extract PDF content
                try:
                    pdf_content = extract_pdf_content(temp_file_path)
                except Exception as e:
                    pdf_content = f"Error extracting PDF content: {str(e)}"

                # Extract metadata from the temporary file
                with open(temp_file_path, 'rb') as pdf_file:
                    try:
                        metadata, metadata_types = extract_metadata(pdf_file)

                        if not metadata:
                            st.warning("No metadata found in this PDF.")
                        else:
                            # Store metadata and PDF content in session state for export
                            file_metadata = (uploaded_file.name, metadata, metadata_types, pdf_content)
                            # Check if this file's metadata is already in the list
                            if not any(item[0] == uploaded_file.name for item in st.session_state.all_files_metadata):
                                st.session_state.all_files_metadata.append(file_metadata)

                            # Display PDF content in a collapsable section
                            with st.expander("PDF DATA", expanded=False):
                                st.text_area("PDF Content", pdf_content, height=300, key=f"pdf_content_{uploaded_file.name}")

                            # Display metadata in an expandable section
                            with st.expander("PDF METADATA", expanded=True):
                                # Generate a unique timestamp for this upload instance
                                timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
                                for idx, (key, value) in enumerate(metadata.items()):
                                    st.text_area(f"{key}", value, height=200 if "XML" in key else 100, key=f"metadata_{uploaded_file.name}_{key}_{idx}_{timestamp}")
                    except Exception as e:
                        st.error(f"Error extracting metadata: {str(e)}")

                # Clean up the temporary file
                try:
                    os.unlink(temp_file_path)
                except Exception as e:
                    st.error(f"Error deleting temporary file: {str(e)}")

        # Add export button in sidebar if there's metadata to export
        if st.session_state.all_files_metadata:
            # Move export functionality to sidebar
            with st.sidebar:
                st.markdown("---")
                st.subheader("Export Metadata")

                # Add checkbox for including PDF text data
                include_data = st.checkbox("Include Data", value=False, 
                                          help="Include PDF text data in the exported CSV file")

                try:
                    # Convert metadata to DataFrame, passing the checkbox value
                    df = metadata_to_dataframe(st.session_state.all_files_metadata, include_data=include_data)

                    # Generate CSV
                    csv = df.to_csv(index=False)

                    # Generate timestamp for filename
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"pdf_metadata_export_{timestamp}.csv"

                    # Create download button that directly exports the metadata
                    if st.download_button(
                        label="📊 Export Metadata",
                        data=csv,
                        file_name=filename,
                        mime="text/csv",
                        help="Export and download metadata as CSV file"
                    ):
                        st.success(f"Metadata from {len(st.session_state.all_files_metadata)} files exported successfully!")
                except Exception as e:
                    st.error(f"Error exporting metadata: {str(e)}")
    else:
        st.info("Please upload PDF files using the sidebar to extract.")

    # Add Ko-fi donate button at the bottom of the sidebar
    with st.sidebar:
        st.markdown("---")
        st.markdown('<a href="https://ko-fi.com/Z8Z7X4MZG" target="_blank"><img height="36" style="border:0px;height:36px;" src="https://storage.ko-fi.com/cdn/kofi6.png?v=6" border="0" alt="Buy Me a Coffee at ko-fi.com" /></a>', unsafe_allow_html=True)

if __name__ == "__main__":
    # Configure the Streamlit page settings
    st.set_page_config(
        page_title="PDF Extractor",
        layout="wide",  # Can be "centered" or "wide"
        initial_sidebar_state="expanded",  # Can be "auto", "expanded", "collapsed"
        # page_icon can be added here if needed
    )

    st.header(':beginner: :grey[PDF Extractor]',
              divider='rainbow',
              anchor=False, help='Extract text and metadata from PDF files...')

    # Custom CSS to improve the UI appearance and hide default Streamlit elements
    hide_streamlit_style = """
                     <style>  
                     /* Reduce Top header padding for a more compact layout */
                    .block-container {
                        padding-top: 1rem;
                        padding-bottom: 0rem;
                        padding-left: 5rem;
                        padding-right: 5rem;
                    }

                    /*Reduce Spacing between widgets*/
                    div[data-testid="stVerticalBlock"] {
                     gap: 0.5rem;
                     }

                    /*Hide Streamlit Menu and various Hides*/
                    div[data-testid="stToolbar"] {
                    visibility: hidden;
                    height: 0%;
                    position: fixed;
                    }

                    div[data-testid="stDecoration"] {
                    visibility: hidden;
                    height: 0%;
                    position: fixed;
                    }
                    div[data-testid="stStatusWidget"] {
                    visibility: hidden;
                    height: 0%;
                    position: fixed;
                    }
                    #MainMenu {
                    visibility: hidden;
                    height: 0%;
                    }
                    header {
                    visibility: hidden;
                    height: 0%;
                    }
                    footer {
                    visibility: hidden;
                    height: 0%;
                    }

                    /*Make columns only as wide as the buttons (Eg:- for play and reset buttons in SQL)*/
                    div[data-testid="column"] {
                        width: fit-content !important;
                        flex: unset;
                    }
                    div[data-testid="column"] * {
                        width: fit-content !important;
                    }

                    /*Disable input instructions*/
                    div[data-testid="InputInstructions"] > span:nth-child(1) {
                       visibility: hidden; }

                    /* Disable fullscreen button on images */ 
                    button[title="View fullscreen"]{
                    visibility: hidden;}

                    /* Display Footer elements*/

                    .footer {
                     position: fixed;
                     left: 0;
                     bottom: 0;
                     width: 100%;
                     background-color: white;
                     color: grey;
                     text-align: center;
                     }

                     /* Remove link underline from some buttons like Share */
                     a:link, a:visited {
                        color: inherit;
                        background-color: transparent;
                        text-decoration: none;
                        }

                    /* Style Tabs*/
                    .stTabs [data-baseweb="tab-list"] {
                    gap: 2px;
                     }

                    .stTabs [data-baseweb="tab"] {
                        height: 50px;
                        white-space: pre-wrap;
                        background-color: #F0F2F6;
                        border-radius: 4px 4px 0px 0px;
                        gap: 1px;
                        padding-top: 10px;
                        padding-bottom: 10px;
                        padding-left: 15px;
                        padding-right: 15px;
                    }

                    .stTabs [aria-selected="true"] {
                        background-color: #FFFFFF;
                    }


                    </style>


        """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)

    main()
