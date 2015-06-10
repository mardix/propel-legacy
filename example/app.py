"""
This is a simple Flask example

===

This example contains the following files:

app.py - The application file
requirements.txt
propel.yml - The deployment file

===

Install Propel on the server you intend to run the websites or apps, and run:

-> pip install propel
-> propel-setup

===

cd into the directory containing the propel.yml file

run: propel -w

Voila!

"""

from flask import Flask

app = Flask(__name__)

@app.route("/")
def index():
    return "Hello Propel!"

