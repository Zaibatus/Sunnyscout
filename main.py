from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float
from dotenv import load_dotenv
import os
import requests

'''
Make sure the required packages are installed. Type: pip3 install -r requirements.txt

This will install the packages from the requirements.txt for this project.
'''

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")


if __name__ == '__main__':
    app.run(debug=False)