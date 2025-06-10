#!/usr/bin/env python3
import json
from supabase import create_client, Client

# Load config
with open('config.json', 'r') as f:
    config = json.load(f)

# Initialize Supabase client
supabase = create_client(
    config['SUPABASE']['URL'],
    config['SUPABASE']['KEY']
)

def push_test_job():
    # Example job for printing text
    text_job = {
        "text": "Hello World!\nTest Label",
        "font_size": 70,
        "label_size": "62",
        "orientation": "standard",
        "align": "center"
    }
    
    # Push the job to the queue
    result = supabase.schema('pgmq_public').rpc('send', {
        'queue_name': 'label_print_jobs',
        'message': text_job
    }).execute()
    
    print("Job pushed to queue:", result)

    # Example job for printing an image (if you want to test image printing)
    with open('../test.bmp', 'rb') as img_file:
        import base64
        img_base64 = base64.b64encode(img_file.read()).decode('utf-8')
        
        image_job = {
            "image": img_base64,
            "label_size": "62",
            "rotate": "auto"
        }
        
        result = supabase.schema('pgmq_public').rpc('send', {
            'queue_name': 'label_print_jobs',
            'message': image_job
        }).execute()
        
        print("Image job pushed to queue:", result)

if __name__ == "__main__":
    push_test_job() 
