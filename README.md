

# SecurityProject - File Virus Scanner

## How to Run

### 1. Download or Clone the Project

- Download the ZIP folder and extract it  
  **OR**
- Clone the repository using:

```bash
git clone https://github.com/yourusername/securityproject.git
2. Start the App
Open the terminal in your code editor

Run the following command:
python app.py
3. Open the Application
Open your browser and go to:
  http://127.0.0.1:5000/login

4. Upload Test Files
Upload a .txt file containing known patterns or suspicious code
(e.g. eval(, EICAR string, or binary test signatures)

If there is no threat, it will display:
✅ No threats found

If there is a threat, it will display:
❌ Threat Detected: [Threat Name]
