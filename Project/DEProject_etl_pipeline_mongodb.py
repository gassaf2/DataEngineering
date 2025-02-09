from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from datetime import datetime
import pandas as pd
from pymongo import MongoClient
import logging
import os
import requests
import urllib.error
# Configure logging
#logging.basicConfig(level=logging.INFO, filename="/home/gassaf/airflow/logs/pipeline.log", format='%(asctime)s - %(levelname)s - %(message)s',force=True)
#sales_df=None

#Define the logging
def setup_logging():
    logger = logging.getLogger("custom_pipeline_logger")
    logger.setLevel(logging.INFO)  # Only log INFO level

    log_file = "/home/gassaf/airflow/logs/pipeline.log"
    handler = logging.FileHandler(log_file, mode="a")  # Append mode
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    if not logger.handlers:  # Avoid duplicate handlers
        logger.addHandler(handler)

    return logger  # Return custom logger



def fetch_weather_data(city, date, api_key):
    base_url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}"
    response = requests.get(base_url)
    #print(response)
    data = response.json()
    #print(data)
    # Extract temperature, humidity, and weather description
    temperature = data['main']['temp'] - 273.15 # Convert from Kelvin to Celsius
    humidity = data['main']['humidity']
    weather_description = data['weather'][0]['description']
    return temperature, humidity, weather_description


api_key="ac40e378daf6601e197b09f6e4be945e"



#initiate the logger
logger=setup_logging()


# Define the pipeline
def extract_data(**kwargs):
     
     # sales_df=pd.read_csv("sales.csv")
     url="https://raw.githubusercontent.com/gassaf2/DataEngineering/refs/heads/main/Project/sample_data/sales_data_project.csv"
     try:
        sales_data=pd.read_csv(url)
        print ("+++++++++",os.getcwd())
        logger.info("+++++++++++Extracting data is successful ...")
        #defining the below  to share the extracted_df with load_data definition
        kwargs['ti'].xcom_push(key='extracted_df',value=sales_data)
     
     except urllib.error.HTTPError as e:
        logger.error(f"HTTP Erroorr: {e.code} - {e.reason}")
     except urllib.error.URLError as e:
        logger.error(f"URL Error: {e.reason}")
     except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")

def transform_data(**kwargs):
    ti=kwargs['ti']
    #defining this to pull the argument extraced_df from extract_data
    sales_df=ti.xcom_pull(task_ids='extract',key='extracted_df')
   
    #doing a transformation on the data and updating the sales amount of product P002 to 700  
    #sales_df.loc[sales_df["product id"] == "P002", "sales amount"]=700

    #transforming the data by adding the weather based on 
    for index, row in sales_df.iterrows():
        try:
            temp, humidity, description = fetch_weather_data(row["store_location"], row["date"],api_key)
            sales_df.at[index, "Temperature_celsius"] = temp
            sales_df.at[index, "Humidity_perc"] = humidity
            sales_df.at[index, "Weather_Description"] = description
        except Exception as e:
            logger.error(f"Error processing row {index}: {e}")
            raise
    #pushing the transformed dataframe and to use it in load_data
    kwargs['ti'].xcom_push(key='transformed_df',value=sales_df)
    logger.info("+++++++++Transforming data is successful...")
    

def load_data(retries=2,delay=5,**kwargs):
    try:
        ti=kwargs['ti']
        #defining this to pull the argument tranformed_df from transform_data
        sales_df=ti.xcom_pull(task_ids='transform',key='transformed_df')
        sales_dict=sales_df.to_dict(orient="records")
        #defining the connection to mongodb
        connection_string="mongodb+srv://gassaf2:dbUserPassword@cluster0.xjx2q.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
        client=MongoClient(connection_string)
        db=client['weather']
        sales=db['sales_weather']
        sales.insert_many(sales_dict)
        logger.info("++++++++++++Loading data is successful...")
    except ConnectionError as e:
        logger.error(f"Unexpected error during data insertion :{e}")
        time.sleep(delay)
    except Exception as e:
        logger.error(f"Error loading data into MongoDB: {e}")
        raise
default_args = {
    'owner': 'airflow',
    'start_date': datetime(2025, 1, 1),
    'retries': 1,
}
# Define the DAG
dag = DAG(
    'DEProject_etl_pipeline_mongodb',
    default_args=default_args,
    schedule_interval='0 6 * * *', # Run every day at 6:00 AM
)

# Create tasks
extract_task = PythonOperator(task_id='extract', python_callable=extract_data, dag=dag)
transform_task = PythonOperator(task_id='transform', python_callable=transform_data, dag=dag)
load_task = PythonOperator(task_id='load', python_callable=load_data, dag=dag)

# Set the order of tasks
extract_task>>transform_task>>load_task

