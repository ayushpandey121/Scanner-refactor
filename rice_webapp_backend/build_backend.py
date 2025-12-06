import os
import PyInstaller.__main__

# Get the directory of this script
current_dir = os.path.dirname(os.path.abspath(__file__))


def add_data_dir(relative_path: str, target_name: str):
    """Helper to register folders that must exist on disk at runtime."""
    source_path = os.path.join(current_dir, relative_path)
    if os.path.exists(source_path):
        datas.append(f'{source_path}{os.pathsep}{target_name}')


# Define all the data files and directories that need to be included
datas = []

# These folders need to exist physically because parts of the app read files
# next to __file__ (e.g. activation keys).
add_data_dir('routes', 'routes')
add_data_dir('services', 'services')
add_data_dir('utils', 'utils')
add_data_dir('data', 'data')

# Build the PyInstaller command
entry_script = os.path.join(current_dir, 'app.py')
pyinstaller_args = [
    entry_script,
    '--name=app',
    '--onedir',  # Changed from --onefile to --onedir
    '--noconsole',
    '--clean',
    f'--distpath={os.path.join(current_dir, "dist")}',
    f'--workpath={os.path.join(current_dir, "build")}',
    f'--specpath={current_dir}',
]

# Add all data files
for data in datas:
    pyinstaller_args.append(f'--add-data={data}')

# Add hidden imports for Flask and other modules that PyInstaller misses
hidden_imports = [
    'flask',
    'flask_cors',
    'werkzeug',
    'jinja2',
    'click',
    'itsdangerous',
    'PIL',
    'cv2',
    'numpy',
    'pandas',
    'openpyxl',
    'scipy',
    'imutils',
    'skimage',
]

for imp in hidden_imports:
    pyinstaller_args.append(f'--hidden-import={imp}')

print("Building backend executable...")
print(f"PyInstaller args: {pyinstaller_args}")

PyInstaller.__main__.run(pyinstaller_args)

print("\nBackend build complete! Check the 'dist' folder.")