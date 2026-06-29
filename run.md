To run the project locally on your system, please follow these step-by-step instructions in your terminal:

1. Stop any running server
If you have a server running in your terminal, stop it by pressing Ctrl + C.

2. Activate the virtual environment
Ensure you are in the project folder (c:\Users\DELL\Desktop\aforro) and run:

In PowerShell:
powershell
.\venv\Scripts\Activate.ps1
3. Apply migrations and seed sample data
Run the following commands to make sure the database is up to date and populated with test data:

powershell
python manage.py migrate
python manage.py seed_data
4. Start the Django development server
Since port 8000 is in use by another process (wslrelay.exe), run the server on port 8080:

powershell
python manage.py runserver 127.0.0.1:8080
5. Access the application dashboard
Once the server starts up, open your web browser and navigate to: 👉 http://127.0.0.1:8080/

