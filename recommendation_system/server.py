from flask import Flask, request, jsonify
from flask_cors import CORS  # Import CORS
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

def get_purchase_link(phone_name):
    phone_name = phone_name.replace(" ","%20")
    return f"https://www.amazon.in/s?k={phone_name}"

@app.route('/get-link/<phone_name>', methods=['GET'])
def get_link(phone_name):
    print("hello")
    
    if not phone_name:
        return jsonify({"error": "Phone name is required"}), 400
    
    link = get_purchase_link(phone_name)
    
    if link:
        return jsonify({"phone_name": phone_name, "purchase_link": link}), 200
    else:
        return jsonify({"error": "Could not find a link to purchase the phone"}), 404

if __name__ == '__main__':
    app.run(debug=True)
