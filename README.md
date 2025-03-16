# Image-Processing-API
## Overview

This Image Processing API allows users to upload images, extract metadata, generate AI-based captions, create thumbnails, and store processed data in MongoDB. It provides endpoints to retrieve image details, thumbnails, and processing statistics. This is shown in an HTML format where users can view the metadata, AI caption, and the generated thumbnails of the image uploaded. Only jpg, jpeg, and png pictures are allowed to be uploaded.

## Setup Instructions
After downloading the project from the repository:

### Install Dependencies

```bash
pip install -r requirements.txt
```
### Restore MongoDB Database from JSON
1. Download the `compass-connections.json` file.
2. Import the .json file into MonogoDB Compass Application

### Run the Flask Application
1. Run the 'main.py' by command or the run function in Visual Studio Code (top right corner)
```bash
python main.py
```

## API documentation
### Upload Image (POST)
1. Locate the image to be uploaded. Directly upload into the HTML or go to the command prompt and  navigate to the folder
```bash
cd "C:\Users\your\image\location"
```
then run the command
```bash
curl -X POST -F "file=@your-image.jpg" http://localhost:5000/
```
2. After running the image in the command prompt, an HTML result will be displayed. In the browser, view the metadata, AI caption, and generated thumbnail. This information will be generated into the MongoDB.

### Get Image Details
```bash
curl -X GET http://localhost:5000/api/images/image-name.jpg
```
**Response:**

```json
{
  "status": "success",
  "data": {
    "Image_ID": "image",
    "filename": "image.jpg",
    "Metadata": {"Format": "JPEG", "Dimensions": "1920 x 1080 pixels", "Size": "2048.57 KB"},
    "AI Caption": "A beautiful scenery with mountains and sky",
    "Thumbnails": {
      "100x100": "http://localhost:5000/static/uploads/thumb_100x100_image.jpg",
      "300x300": "http://localhost:5000/static/uploads/thumb_300x300_image.jpg"
    },
    "Status": "processed",
    "Processing Time": 2.45
  },
  "error": null
}
```
