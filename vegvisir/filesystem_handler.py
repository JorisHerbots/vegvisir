import uuid
import os


# This package includes the functions used to create temporary directories 
# All the temporary directories reside inside the GLOBAL_TEMPORARY_DIRECTORY 


GLOBAL_TEMPORARY_DIRECTORY = "/tmp/vegvisir"



# Creates a temporary, unique, directory that is automatically cleaned up (removed) when the object is remove / goes out of scope.
class TemporaryUniqueDirectory:

    def __init__(self):
        self._unique_path = create_unique_temporary_directory()

    def get_path(self):
        return self._unique_path

    def __del__(self):
        print("Temporary directory cleanup called")
        cleanup_unique_temporary_directory(self._unique_path)


# Create a unique folder path in the global temporary directory
# The folder itself is not created, only a path where the folder CAN BE created
def generate_unique_path():
    id = str(uuid.uuid1())
    
    path = os.path.join(GLOBAL_TEMPORARY_DIRECTORY, id)
    return path

# Throw FileExistsError if already created
def create_global_temporary_directory():
    try:
        os.mkdir(GLOBAL_TEMPORARY_DIRECTORY)
    except FileExistsError:
        pass 

# Create a unique temporary directory in the global temporary directory
def create_unique_temporary_directory():
    if not os.path.isdir(GLOBAL_TEMPORARY_DIRECTORY):
        create_global_temporary_directory()

    unique_path = generate_unique_path()

    os.mkdir(unique_path)

    return unique_path

# Cleans up a unique temporary directory by removing the directory and all contained files and subdirectories
def cleanup_unique_temporary_directory(path):
    try:
        shutil.rmtree(path)
    except:
        pass
