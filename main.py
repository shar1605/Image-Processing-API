# importing packages
import os
import urllib.request
import requests
import time

from app import app
from flask import Flask, flash, request, redirect, url_for, render_template, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from PIL import Image
from PIL.ExifTags import TAGS
from transformers import BlipProcessor, BlipForConditionalGeneration
from pymongo import MongoClient


#Connect to MongoDB
client= MongoClient("mongodb://localhost:27017/")
db= client.image_processing
collection = db.image_metadata


ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}

#######################
#defining api endpoints
#######################

#Defining file extensions allowed 
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

#Defining extracting metadata
def extract_metadata(image, file_path):
    file_size = os.path.getsize(file_path) / 1024
    metadata = {
        "Format": image.format,
        "Dimensions": f"{image.width} x {image.height} pixels",
        "Size": f"{file_size:.2f} KB"
    }
    exif_data = image._getexif()

    if exif_data:
        metadata["EXIF Data"] = {TAGS.get(tag, tag): value for tag, value in exif_data.items()}
    else:
        metadata["EXIF Data"] = "No EXIF metadata available"

    return metadata

#Defining AI cpation model
def generate_AIcaption(file_path):
    processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-large")
    model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-large")

    image = Image.open(file_path).convert("RGB")
    inputs = processor(image, return_tensors="pt")

    out = model.generate(**inputs)
    caption = processor.decode(out[0], skip_special_tokens=True)
     
    return caption

#Defining Database storage
def mongo_db_save(image_id, filename, metadata, caption, thumbnails,processing_time,status= "processed"):
    thumbnails_urls = {
        "small": f"http://localhost:8000/api/images/{image_id}/thumbnails/small",
        "medium": f"http://localhost:8000/api/images/{image_id}/thumbnails/medium"
    }
    data= {
        "Image_ID": image_id,
        "filename" : filename,
        "Metadata" : metadata,
        "AI Caption" : caption,
        "Thumbnails" : thumbnails,
        "Status": status,
        "Processing Time": processing_time
    }

    collection.insert_one(data)
    print("Data stored in MongoDB", data)

#######################
# Route for upload form
#######################
@app.route('/')
def upload_form():
    return render_template('index.html', metadata=None, filename=None, thumbnails={})

#######################
# Route to upload image
#######################
@app.route('/', methods=['POST'])
def upload_image():
    metadata = None
    thumbnails = {}

    if 'file' not in request.files:
        flash('No file uploaded')
        return redirect(request.url)

    file = request.files['file']

    if file.filename == '':
        flash("No image selected")
        return redirect(request.url)

    if file and allowed_file(file.filename):
        start_time = time.time()
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Open image and extract metadata
        image = Image.open(file_path)
        metadata = extract_metadata(image, file_path)
        image.save(file_path, quality=100, optimize=True)

        #generate AI caption
        caption = generate_AIcaption(file_path)

        # Generating thumbnails
        thumbnail_sizes = [(100, 100), (300, 300)]
        for size in thumbnail_sizes:
            thumb = image.copy()
            thumb.thumbnail(size)
            thumbnail_filename = f"thumb_{size[0]}x{size[1]}_{filename}"
            thumbnail_path = os.path.join(app.config['UPLOAD_FOLDER'], thumbnail_filename)
            thumb.save(thumbnail_path, quality=100, optimize=True)

            thumbnails[f"{size[0]}x{size[1]}"] = thumbnail_filename



 # Convert keys to strings
        #Process time
        
        processing_time = round(time.time() - start_time, 2)

        # save into database
        image_id = filename.split('.')[0]
        mongo_db_save(image_id, filename, metadata, caption, thumbnails, processing_time, "processed")




        flash('Image successfully uploaded!')
        return render_template('index.html', filename=filename, thumbnails=thumbnails, metadata=metadata, caption=caption)
    

    flash('Allowed Formats: jpg, jpeg, png')
    return redirect(request.url)

###########################################################
# List processed or processing images and processing status
###########################################################
@app.route('/api/images', methods=['GET'])
def image_list():
    images= list(collection.find({}, {"_id":0}))
    return jsonify(({"status": "success", "data": images, "error": None}))

#####################
# Get image details
#####################
@app.route('/api/images/<filename>', methods=['GET'])
def image_details(filename):
    image_data= collection.find_one({"filename": filename}, {"_id": 0})
    if not image_data:
        return jsonify({"status": "error", "data": None, "error": "Image not found"}), 404
    # Construct URLs for thumbnails
    base_url = url_for('static', filename='uploads/', _external=True)
    image_data["Thumbnails"] = {size: base_url + path for size, path in image_data["Thumbnails"].items()}
    
    return jsonify({"status": "success", "data": image_data, "error": None})

#######################
#Get thumbnail
######################
@app.route('/api/images/<filename>/thumbnails/<size>', methods=['GET'])
def get_thumbnails(filename, size):
    # Ensure correct filename format
    image_data = collection.find_one({"filename": filename + ".jpg"}, {"_id": 0})

    if not image_data or "Thumbnails" not in image_data:
        return jsonify({"status": "error", "data": None, "error": "Thumbnail not found"}), 404

    # Ensure correct size format
    thumbnail_filename = image_data["Thumbnails"].get(size)
    if not thumbnail_filename:
        return jsonify({"status": "error", "data": None, "error": "Thumbnail not available"}), 404

    # Return the thumbnail
    return send_from_directory(app.config['UPLOAD_FOLDER'], thumbnail_filename)


#####################
#Getting stats
###################
@app.route('/api/stats', methods=['GET'])
def processing_stats():
    total_images = collection.count_documents({})
    successful_images = collection.count_documents({"Status": "processed"})
    failed_images = total_images - successful_images
    
    processing_time = [
        doc.get("Processing Time", 0) 
        for doc in collection.find({}, {"Processing Time": 1, "_id": 0}) 
        if doc.get("Processing Time") is not None
    ]
    
    avg_processing_time = round(sum(processing_time) / len(processing_time), 2) if processing_time else 0.0
    
    
    stats = {
        "Total Images Processed": total_images,
        "Successful Uploads": successful_images,
        "Failed Uploads": failed_images,
        "Average Processing Time (s)": avg_processing_time
    }
    return jsonify(stats)



###############################
# Display the uploaded image   
############################### 
@app.route('/display/<filename>')
def display_image(filename):
    return redirect(url_for('static', filename='uploads/' + filename), code=301)

if __name__ == "__main__":
    app.run(debug=True)