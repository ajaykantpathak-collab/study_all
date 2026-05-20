try:
    import streamlit
    import pandas
    import datasets
    import google.genai
    import tqdm
    import numpy
    import matplotlib
    import razorpay
    print("ALL PACKAGES INSTALLED SUCCESSFULLY")
except ImportError as e:
    print(f"MISSING PACKAGE: {e}")