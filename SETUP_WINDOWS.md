# Setup guide (Windows)

Run these in Command Prompt, one block at a time.

## 1. Create a project folder and go into it
```
cd %USERPROFILE%\Documents
mkdir dora-capstone
cd dora-capstone
```
Now copy all the project files into this folder (app\, tests\, .github\, run.py, seed.py, requirements.txt, README.md).

## 2. Create a virtual environment
A virtual environment keeps this project's packages separate from the rest of your system.
```
python -m venv venv
venv\Scripts\activate
```
Your prompt should now start with `(venv)`.

## 3. Install the dependencies
```
pip install -r requirements.txt
```

## 4. Load the synthetic data
```
python seed.py
```
Expected output:
```
Database seeded with synthetic data.
Logins:  admin/admin123  editor/editor123  viewer/viewer123
```

## 5. Run the tests
```
pytest -v
```
All seven tests should pass.

## 6. Start the application
```
python run.py
```
Open a browser at http://127.0.0.1:5000 and log in as `admin` / `admin123`.

Press CTRL+C in the terminal to stop the server.

## If something fails
- `'python' is not recognized` : Python is not on your PATH. Reinstall Python and tick "Add python.exe to PATH".
- A package fails to build on Python 3.14 : tell Claude the exact error message.
- Port 5000 already in use : change the last line of run.py to `app.run(debug=True, port=5001)`.
