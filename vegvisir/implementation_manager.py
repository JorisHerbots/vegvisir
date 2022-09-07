from vegvisir.filesystem_handler import * 
from vegvisir.docker_manager import *

IMPLEMENTATIONS_DIRECTORY = "./implementations"
IMAGESETS_IMPORT_EXPORT_DIRECTORY = "./imagesets_import_export"


def get_implementations_from_test(test):
    implementations = copy.deepcopy(test["configuration"]["clients"])
    implementations += (test["configuration"]["shapers"])
    implementations += (test["configuration"]["servers"])

    return implementations



# Works for both lists (used in tests) and dictionaries (used in files)
def get_docker_imagesnames_from_implementations(implementations):

    if type(implementations) is dict:
        docker_imagenames : List[str] = []

        for impl in implementations:
            if "image" in implementations[impl]:
                docker_imagenames.append(implementations[impl]["image"])
                
        return docker_imagenames

    if type(implementations) is list:
        docker_imagenames : List[str] = []

        for impl in implementations:
            if "image" in impl:
                docker_imagenames.append(impl["image"])
                
        return docker_imagenames

    raise Exception("get_docker_imagenames_from_implementations() is not implemented for the type " + type(implementations))

def get_imageset_json(imageset_name : str):
    imageset_json = None
    
    with open(os.path.join(IMPLEMENTATIONS_DIRECTORY, imageset_name + ".json"), "r") as imageset_json_file:
        imageset_json = json.load(imageset_json_file) 

    return imageset_json
    

def get_imageset_implementations(imageset_name : str):

    imageset_json = get_imageset_json(imageset_name)
    return imageset_json["implementations"]


def export_imageset(imageset_name : str):
    unique_directory = TemporaryUniqueDirectory()

    imageset_implementations = get_imageset_implementations(imageset_name)
    docker_export_images(get_docker_imagesnames_from_implementations(imageset_implementations), os.path.join(unique_directory.get_path(), imageset_name + ".tar"))

    shutil.copy(os.path.join(IMPLEMENTATIONS_DIRECTORY, imageset_name + ".json"), os.path.join(unique_directory.get_path(),  imageset_name + ".json"))
    shutil.make_archive(os.path.join(IMAGESETS_IMPORT_EXPORT_DIRECTORY, imageset_name), "zip", unique_directory.get_path())

def import_imageset(imageset_name : str):
    zip_file_path = os.path.join(IMAGESETS_IMPORT_EXPORT_DIRECTORY, imageset_name + ".zip")

    unique_directory = TemporaryUniqueDirectory()

    shutil.unpack_archive(zip_file_path, unique_directory.get_path())

    docker_import_images(os.path.join(unique_directory.get_path(), imageset_name + ".tar"))
    shutil.copy(os.path.join(unique_directory.get_path(), imageset_name + ".json"), os.path.join(IMPLEMENTATIONS_DIRECTORY, imageset_name + ".json"))

# Create an imageset  
def create_imageset(implementations, imageset_name : str):
    # Tag docker images
    docker_imagenames = get_docker_imagesnames_from_implementations(implementations)

    print("tagging the following images:")
    print(docker_imagenames)

    docker_tag_images(docker_imagenames, imageset_name)
    print("docker create imageset")

    # Create json file
    imageset_json = generate_imageset_json(implementations, imageset_name)
    
    json_output_filepath = os.path.join(IMPLEMENTATIONS_DIRECTORY, imageset_name + ".json")
    with open(json_output_filepath, "w") as json_output_file:
        json.dump(imageset_json, json_output_file)

def remove_imageset(imageset_name : str):
    docker_remove_images_containing_string_in_name(imageset_name)
    os.remove(os.path.join(IMPLEMENTATIONS_DIRECTORY, imageset_name + ".json"))

# generates the json for an imageset with the modified image names
def generate_imageset_json(implementations, imageset_name : str) -> str:
    output_dictionary = {}
    implementations_dictionary = {}

    for x in implementations:
        if "image" in implementations[x]:
            img = implementations[x]["image"]

            implementations_dictionary[x] = deepcopy(implementations[x])
            implementations_dictionary[x]["image"] = "vegvisir" + "/" + docker_get_name_from_image(img) + ":" + imageset_name

    output_dictionary["enabled"] = True 
    output_dictionary["implementations"] = implementations_dictionary

    return output_dictionary


# Given a test move it to another imageset (assumes all the docker implementations exist in the new implementation)
def move_test_to_other_imageset(test, new_imageset_name):

    for implementation in test["configuration"]["clients"]:
        
        # If is docker implementation
        if "image" in implementation:
            new_image_name = "vegvisir/" + docker_get_name_from_image(implementation["image"]) + ":" + new_imageset_name  
            old_imageset_name = implementation["id"].split(":")[-1]
            new_id = implementation["id"].split(":")[0] + ":" + new_imageset_name
            new_active_id = implementation["active_id"].replace(old_imageset_name, new_imageset_name)

            implementation["image"] = new_image_name
            implementationp["id"] = new_id
            implementation["active_id"] = new_active_id

    for implementation in test["configuration"]["shapers"]:
        
        # If is docker implementation
        if "image" in implementation:


            new_image_name = "vegvisir/" + docker_get_name_from_image(implementation["image"]) + ":" + new_imageset_name  
            old_imageset_name = implementation["id"].split(":")[-1]
            new_id = implementation["id"].split(":")[0] + ":" + new_imageset_name
            new_active_id = implementation["active_id"].replace(old_imageset_name, new_imageset_name)

            implementation["image"] = new_image_name
            implementation["id"] = new_id
            implementation["active_id"] = new_active_id
    
    for implementation in test["configuration"]["servers"]:
        
        # If is docker implementation\\w
        if "image" in implementation:


            new_image_name = "vegvisir/" + docker_get_name_from_image(implementation["image"]) + ":" + new_imageset_name  
            old_imageset_name = implementation["id"].split(":")[-1]
            new_id = implementation["id"].split(":")[0] + ":" + new_imageset_name
            new_active_id = implementation["active_id"].replace(old_imageset_name, new_imageset_name)

            implementation["image"] = new_image_name
            implementation["id"] = new_id
            implementation["active_id"] = new_active_id
