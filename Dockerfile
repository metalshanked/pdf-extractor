# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container
COPY pdf_extractor.py .

# Make port 8501 available to the world outside this container
EXPOSE 8501

# Define environment variables
ENV STREAMLIT_SERVER_HEADLESS=true
ENV BASE_URL_PATH=""

# Run the application when the container launches
CMD if [ -z "${BASE_URL_PATH}" ]; then \
    streamlit run pdf_extractor.py --server.address=0.0.0.0 --server.port=8501; \
    else \
    streamlit run pdf_extractor.py --server.address=0.0.0.0 --server.port=8501 --server.baseUrlPath=${BASE_URL_PATH}; \
    fi
