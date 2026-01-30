import shutil
import os
import datetime

def backup_project():
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"c:/bus-gps/backups/alpha_1.0_{timestamp}"
    
    os.makedirs(backup_dir, exist_ok=True)
    
    files_to_backup = [
        "c:/bus-gps/web_app.py",
        "c:/bus-gps/listener.py",
        "c:/bus-gps/Dockerfile",
        "c:/bus-gps/docker-compose.yml",
        "c:/bus-gps/requirements.txt",
        "c:/bus-gps/templates/super_admin.html",
        "c:/bus-gps/templates/school_admin.html",
        "c:/bus-gps/templates/parent_dashboard.html",
        "c:/bus-gps/templates/index.html",
        "c:/bus-gps/templates/login.html"
    ]
    
    print(f"📦 Backing up to {backup_dir}...")
    
    for file_path in files_to_backup:
        if os.path.exists(file_path):
            shutil.copy(file_path, backup_dir)
            print(f" - Copied {os.path.basename(file_path)}")
            
    print("✅ Backup Complete")

if __name__ == "__main__":
    backup_project()
