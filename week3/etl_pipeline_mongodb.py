from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from datetime import datetime
import pandas as pd
from pymongo import MongoClient
import logging

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

#initiate the logger
logger=setup_logging()


# Define the pipeline
def extract_data(**kwargs):

     sales_df=pd.read_csv("sales.csv")
     logger.info("+++++++++++Extracting data...")
     #defining the below  to share the extracted_df with load_data definition
     kwargs['ti'].xcom_push(key='extracted_df',value=sales_df)
     #return sales_df

def transform_data(**kwargs):
    ti=kwargs['ti']
    #defining this to pull the argument transformed_df from transform_data
    sales_df=ti.xcom_pull(task_ids='extract',key='extracted_df')
    sales_df['total_revenue']=sales_df['quantity']*sales_df['price']
    kwargs['ti'].xcom_push(key='transformed_df',value=sales_df)
    logger.info("+++++++++Transforming data...")
    logger.info("+++++++++Transforming data...")

def load_data(**kwargs):
    ti=kwargs['ti']
    #defining this  to pull the argument extracted_df from extract_data
    sales_df=ti.xcom_pull(task_ids='extract',key='extracted_df')
    sales_dict=sales_df.to_dict(orient="records")

#defining the connection to mongodb
    connection_string="mongodb+srv://gassaf2:dbUserPassword@cluster0.xjx2q.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    client=MongoClient(connection_string)
    db=client['test_dag']
    sales=db['sales']

    sales.insert_many(sales_dict)
    logger.info("++++++++++++Loading data...")

# Define default arguments for the DAG
default_args = {
    'owner': 'airflow',
    'start_date': datetime(2025, 1, 1),
    'retries': 1,
}
# Define the DAG
dag = DAG(
    'etl_pipeline_mongodb',
    default_args=default_args,
    schedule_interval='0 6 * * *', # Run every day at 6:00 AM
)

# Create tasks
extract_task = PythonOperator(task_id='extract', python_callable=extract_data, dag=dag)
transform_task = PythonOperator(task_id='transform', python_callable=transform_data, dag=dag)
load_task = PythonOperator(task_id='load', python_callable=load_data, dag=dag)

# Set the order of tasks
extract_task>>transform_task>>load_task