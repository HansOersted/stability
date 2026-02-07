import os
import subprocess
import threading

def delete_file_if_exists(file_path):
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"Deleted {file_path}")
    else:
        print(f"{file_path} not found, skipping deletion.")

def run_flight_rolling():
    subprocess.run(["python", "flight_rolling.py"])

def run_tracking_error_rolling():
    subprocess.run(["python", "tracking_error_rolling.py"])

def run_update_input():
    subprocess.run(["python", "update_input.py"])

def run_usr_receiver():
    subprocess.run(["python", "usr_receiver.py"])

def main():
    delete_file_if_exists("input_data.npz")
    delete_file_if_exists("formula_from_srv.txt")

    thread0 = threading.Thread(target=run_usr_receiver, daemon=True)
    thread1 = threading.Thread(target=run_flight_rolling)
    thread2 = threading.Thread(target=run_tracking_error_rolling)
    thread3 = threading.Thread(target=run_update_input)

    thread0.start()
    thread1.start()
    thread2.start()
    thread3.start()

    thread1.join()
    thread2.join()
    thread3.join()

if __name__ == "__main__":
    main()
