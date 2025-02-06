Install WSL2 (if not already installed):
Open PowerShell as Administrator and run:


wsl --install


Install Airflow in WSL2: (go to the home directory of python virtual env create in my machine under ./home/gassaf/pythonvenv


sudo apt update && sudo apt install python3-pip
python3 -m venv /home/gassaf/pythonvenv

go to the folder where the virtual python env is created

./pip install apache-airflow

source /home/gassaf/pythonvenv/bin/activate
airflow db migrate
airflow scheduler & airflow webserver --port 8080 &




create a user name 
airflow users create --username custom_user --lastname User --firstname Custom --email custom_user@example.org --role CustomRole --password secure_password

created a user name :gassaf2/gassaf2