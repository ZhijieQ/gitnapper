from flask import Flask, jsonify, request, render_template
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
import base64
import os

key_map = {}
app = Flask(__name__)

# Generate a public/private key pair
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
)
public_key = private_key.public_key()


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

        # Generate a random id to store the password
        random_id = os.urandom(16).hex()
        key_map[random_id] = decrypted_password
        message = f"Your data has been stolen!\nTo retrieve it, please send the ID '{random_id}' to the following URL: http://localhost:5000/get_password"
        return jsonify({"message": message}), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/get_password", methods=["GET", "POST"])
def get_password():
    """
    Displays a form to enter an ID and shows the corresponding password.
    """
    password_to_display = None
    error_message = None

    if request.method == "POST":
        retrieval_id = request.form.get("retrieval_id")
        if retrieval_id:
            password_to_display = key_map.get(retrieval_id)
            if not password_to_display:
                error_message = "Invalid ID or password not found."
        else:
            error_message = "Please provide an ID."

    return render_template("password_retrieval.html", password=password_to_display, error=error_message)


if __name__ == "__main__":
    # Create a 'templates' directory if it doesn't exist
    if not os.path.exists('templates'):
        os.makedirs('templates')
    app.run(debug=True) # Run in debug mode for easier development
