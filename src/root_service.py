import os
import subprocess



def main():
    # Set the PYTHONPATH environment variable
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    python_path = os.environ.get('PYTHONPATH', '')
    print(python_path)
    if project_root not in python_path.split(os.pathsep):
        new_python_path = f"{project_root}:{python_path}"
        os.environ['PYTHONPATH'] = new_python_path
        print(f"Updated PYTHONPATH: {new_python_path}")
    else:
        print("PYTHONPATH is already set correctly.")
    print(new_python_path) 
    from run import run
    subprocess.run("run.py")
        
if __name__ == "__main__":
    main()
