import datetime
import webbrowser
import os

def startup_assistant():
    # Greet the user
    print("Good day! Here's your startup routine...\n")

    # Show the date and time
    now = datetime.datetime.now()
    print(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}")

    # Open a to-do list (can be a file or website)
    todo_file = "todo.txt"  # Change path as needed
    if os.path.exists(todo_file):
        os.system(f"xdg-open {todo_file}")
    else:
        print("No to-do file found.")

    # Open important websites
    webbrowser.open("https://calendar.google.com")
    webbrowser.open("https://mail.google.com")

    # Run a work-related script (edit the path)
    work_script = "daily_tasks.py"
    if os.path.exists(work_script):
        os.system(f"python3 {work_script}")
    else:
        print("No work script found.")

if __name__ == "__main__":
    startup_assistant()