import streamlit as st
import pandas as pd
import joblib
import json
import os

# Set page configuration
st.set_page_config(page_title="FreshBasket Delay Predictor", page_icon="🚚", layout="wide")

# ==========================================
# 1. Load Artifacts (Cached for performance)
# ==========================================
@st.cache_resource
def load_artifacts():
    try:
        model = joblib.load('artifacts/xgboost_model.pkl')
        encoder = joblib.load('artifacts/encoder.pkl')
        scaler = joblib.load('artifacts/scaler.pkl')
        
        with open('artifacts/model_metadata.json', 'r') as f:
            metadata = json.load(f)
            
        return model, encoder, scaler, metadata
    except Exception as e:
        st.error(f"Error loading artifacts: {e}")
        st.info("Make sure 'xgboost_model.pkl', 'encoder.pkl', 'scaler.pkl', and 'model_metadata.json' exist in the 'artifacts/' directory.")
        st.stop()

model, encoder, scaler, metadata = load_artifacts()

# Extract column groupings from metadata
CONTINUOUS_COLS = metadata['continuous_cols']
CATEGORICAL_COLS = metadata['categorical_cols']
BINARY_ORDINAL_COLS = metadata['binary_ordinal_cols']

# ==========================================
# 2. Application Header
# ==========================================
st.title("🚚 FreshBasket Delivery Delay Predictor")
st.markdown("""
Enter the trip, driver, and weather details below to predict if the shipment is at risk of being delayed.
""")

# ==========================================
# 3. User Input Form
# ==========================================
with st.form("prediction_form"):
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("🛣️ Trip & Route Info")
        distance = st.number_input("Route Distance (miles)", min_value=0.0, value=500.0)
        average_hours = st.number_input("Average Route Hours", min_value=0.0, value=10.0)
        avg_no_of_vehicles = st.number_input("Daily Avg Vehicles on Route", min_value=0, value=1500)
        accident = st.selectbox("Accident Reported?", [0, 1], format_func=lambda x: "Yes" if x == 1 else "No")
        is_midnight = st.selectbox("Crosses Midnight?", [0, 1], format_func=lambda x: "Yes" if x == 1 else "No")
        
    with col2:
        st.subheader("🚛 Driver & Truck Info")
        truck_age = st.number_input("Truck Age (years)", min_value=0, value=5)
        load_capacity_pounds = st.number_input("Load Capacity (lbs)", min_value=0.0, value=10000.0)
        mileage_mpg = st.number_input("Mileage (mpg)", min_value=0.0, value=15.0)
        fuel_type = st.selectbox("Fuel Type", ["diesel", "gas", "electric", "Unknown"])
        
        age = st.number_input("Driver Age", min_value=18, value=40)
        experience = st.number_input("Driver Experience (years)", min_value=0, value=10)
        gender = st.selectbox("Driver Gender", ["male", "female", "Unknown"])
        driving_style = st.selectbox("Driving Style", ["proactive", "conservative", "aggressive", "Unknown"])
        ratings = st.slider("Driver Rating", min_value=1, max_value=10, value=5)
        average_speed_mph = st.number_input("Average Speed (mph)", min_value=0.0, value=55.0)

    with col3:
        st.subheader("🌤️ Weather Conditions")
        # Route Weather
        route_avg_temp = st.number_input("Route Avg Temp (F)", value=60.0)
        route_avg_wind_speed = st.number_input("Route Wind Speed", value=10.0)
        route_avg_precip = st.number_input("Route Precip", value=0.0)
        route_avg_humidity = st.number_input("Route Humidity (%)", value=50.0)
        route_avg_visibility = st.number_input("Route Visibility", value=10.0)
        route_avg_pressure = st.number_input("Route Pressure", value=1015.0)
        route_description = st.selectbox("Route Weather Desc", ["Clear", "Cloudy", "Rain", "Snow", "Unknown"])
        
        # We simplify Origin and Destination weather inputs here to keep the UI clean, 
        # but map them to the required feature names.
        st.markdown("**(Origin & Destination defaults set to route conditions for simplicity)**")
        origin_description = st.selectbox("Origin Weather Desc", ["Clear", "Cloudy", "Rain", "Snow", "Unknown"])
        dest_description = st.selectbox("Dest Weather Desc", ["Clear", "Cloudy", "Rain", "Snow", "Unknown"])

    submit_button = st.form_submit_button(label="Predict Delay Risk", type="primary")

# ==========================================
# 4. Prediction Logic
# ==========================================
if submit_button:
    # 4a. Create a DataFrame from the inputs
    input_dict = {
        'distance': distance, 'average_hours': average_hours, 'avg_no_of_vehicles': avg_no_of_vehicles,
        'truck_age': truck_age, 'load_capacity_pounds': load_capacity_pounds, 'mileage_mpg': mileage_mpg,
        'age': age, 'experience': experience, 'average_speed_mph': average_speed_mph,
        'route_avg_temp': route_avg_temp, 'route_avg_wind_speed': route_avg_wind_speed, 
        'route_avg_precip': route_avg_precip, 'route_avg_humidity': route_avg_humidity, 
        'route_avg_visibility': route_avg_visibility, 'route_avg_pressure': route_avg_pressure,
        
        # Defaulting origin and dest to route metrics based on form above
        'origin_avg_temp': route_avg_temp, 'origin_avg_wind_speed': route_avg_wind_speed, 
        'origin_avg_precip': route_avg_precip, 'origin_avg_humidity': route_avg_humidity, 
        'origin_avg_visibility': route_avg_visibility, 'origin_avg_pressure': route_avg_pressure,
        
        'dest_avg_temp': route_avg_temp, 'dest_avg_wind_speed': route_avg_wind_speed, 
        'dest_avg_precip': route_avg_precip, 'dest_avg_humidity': route_avg_humidity, 
        'dest_avg_visibility': route_avg_visibility, 'dest_avg_pressure': route_avg_pressure,
        
        'route_description': route_description, 'origin_description': origin_description, 'dest_description': dest_description,
        'fuel_type': fuel_type, 'gender': gender, 'driving_style': driving_style,
        'accident': accident, 'ratings': ratings, 'is_midnight': is_midnight
    }
    
    input_df = pd.DataFrame([input_dict])
    
    # 4b. Preprocessing: Match Lab C's exact pipeline
    try:
        # Scale continuous features
        X_cont = pd.DataFrame(
            scaler.transform(input_df[CONTINUOUS_COLS]),
            columns=CONTINUOUS_COLS
        )
        
        # Encode categorical features
        X_cat = pd.DataFrame(
            encoder.transform(input_df[CATEGORICAL_COLS]),
            columns=encoder.get_feature_names_out(CATEGORICAL_COLS)
        )
        
        # Binary/Ordinal features
        X_bin = input_df[BINARY_ORDINAL_COLS].reset_index(drop=True)
        
        # Assemble final matrix (Exact order from Lab C)
        X_final = pd.concat([X_cont, X_cat, X_bin], axis=1)
        
        # Ensure column order matches the model's expected feature names
        X_final = X_final[metadata['feature_names']]
        
        # 4c. Predict
        prediction = model.predict(X_final)[0]
        probability = model.predict_proba(X_final)[0][1] * 100
        
        # 4d. Display Results
        st.divider()
        st.subheader("Prediction Result")
        
        if prediction == 1:
            st.error(f"⚠️ **AT RISK OF DELAY** (Probability: {probability:.1f}%)")
            st.markdown("Operations should consider pre-warning the customer or preemptively checking the route.")
        else:
            st.success(f"✅ **ON TIME** (Probability of delay: {probability:.1f}%)")
            st.markdown("This shipment is on track.")
            
    except Exception as e:
        st.error(f"An error occurred during prediction: {e}")