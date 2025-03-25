#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Peter Simeth's basic flask pretty youtube downloader (v1.3)
https://github.com/petersimeth/basic-flask-template
© MIT licensed, 2018-2023
"""

from flask import Flask, render_template, jsonify, request
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
import base64

DEVELOPMENT_ENV = True

app = Flask(__name__)

# Generate a public/private key pair
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
)
public_key = private_key.public_key()

app_data = {
    "name": "Peter's Starter Template for a Flask Web App",
    "description": "A basic Flask app using bootstrap for layout",
    "author": "Peter Simeth",
    "html_title": "Peter's Starter Template for a Flask Web App",
    "project_name": "Starter Template",
    "keywords": "flask, webapp, template, basic",
}

@app.route("/")
def index():
    return render_template("index.html", app_data=app_data)


@app.route("/about")
def about():
    return render_template("about.html", app_data=app_data)


@app.route("/service")
def service():
    return render_template("service.html", app_data=app_data)


@app.route("/contact")
def contact():
    return render_template("contact.html", app_data=app_data)


@app.route("/get_key", methods=["GET"])
def get_key():
    """
    Returns the public key in PEM format.
    """
    pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return jsonify({"public_key": pem.decode("utf-8")})


@app.route("/password", methods=["POST"])
def password():
    """
    Accepts the encrypted password and returns a success message.
    """
    encrypted_password = request.json.get("encrypted_password")

    if not encrypted_password:
        return jsonify({"error": "No encrypted password provided"}), 400
    
    try:
        # Decode the base64 encoded encrypted password
        encrypted_password_bytes = base64.b64decode(encrypted_password.strip())

        # Decrypt the password using the private key with OAEP padding
        decrypted_password = private_key.decrypt(
            encrypted_password_bytes,
            padding=padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        decrypted_password = decrypted_password.decode("utf-8")
        print(f"Decrypted password: {decrypted_password}")
        return jsonify({"message": "Password successfully decrypted"}), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=DEVELOPMENT_ENV)
