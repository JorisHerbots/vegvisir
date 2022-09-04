from copy import deepcopy
import os
import subprocess
import json
import shutil
import glob
import logging


TEMPORARY_DIRECTORY = "/tmp/vegvisir"

def get_name_from_image(image):
	return image.split('/')[-1].split(':')[0]

def get_repo_from_image(image):
	repo = None
	try:
		repo = image.split('/')[-2]
	except:
		repo = None
	return repo

def get_tag_from_image(image):
	split = image.split(':')
	if len(split) == 1:
		return ""
	return split[-1]

# creates an imageset by tagging the implementations with vegvisir/{setname}:implementation_image_name and by creating a corresponding json file in the ./implementations folder of vegvisir
# pre:
#   imageset with the given setname does not yet exist
def docker_create_imageset(implementations, setname) -> int:
    returncode = 0
    
    for x in implementations:
        if "image" in implementations[x]:
            img = implementations[x]["image"]
            r = subprocess.run(
                "docker tag {} {}".format(img, "vegvisir" + "/" + get_name_from_image(img) + ":" + setname),
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            if r.returncode != 0:
                logging.info(
                    "Tagging docker image %s failed: %s", img, r.stdout.decode("utf-8")
                )
            returncode += r.returncode

    implementations_json = generate_imageset_json(implementations, setname)  
    output_file_url = os.path.join("./implementations/", setname.replace("/", "_") + ".json")


    with open(output_file_url, 'w') as output_file:
        output_file.write(json.dumps(implementations_json))

    return returncode

# Gets the image names from docker
# param:
#	name of the imageset
# returns:
#	list with strings representing the names of the loaded images
def imageset_get_images(imageset_name):
	images = set()

	proc = subprocess.run(
		"docker images | awk '{print $1, $2}'",
		shell=True,
		stdout=subprocess.PIPE,
		stderr=subprocess.STDOUT
	)
	local_images = proc.stdout.decode('utf-8').replace(' ', ':').split('\n')[1:]
	
	for img in local_images:
		repo = get_repo_from_image(img)
		if repo == "vegvisir":
			set_name = get_tag_from_image(img)
			if set_name == imageset_name:
				images.add(img)
		
	return list(images)

# generates the json for an imageset with the modified image names
def generate_imageset_json(implementations, setname) -> str:
    output_dictionary = {}
    implementations_dictionary = {}

    for x in implementations:
        if "image" in implementations[x]:
            img = implementations[x]["image"]

            implementations_dictionary[x] = deepcopy(implementations[x])
            implementations_dictionary[x]["image"] = "vegvisir" + "/" + get_name_from_image(img) + ":" + setname 

    output_dictionary["enabled"] = True 
    output_dictionary["implementations"] = implementations_dictionary

    return output_dictionary

# Exports/saves the imageset into a zip archive in the current working directory 
# pre: 
#   /tmp/vegvisir directory not created and not in use
# post:
#   the imageset is saved and any temporary files/folders are removed
# raises:
#   re-raises any filesystem/docker errors 
def docker_export_imageset(setname):
    
    try:
        os.mkdir(TEMPORARY_DIRECTORY)
    except:
        print("Error creating temporary dictionary")


    images_list = imageset_get_images(setname)
    images_list_string = ""

    for image in images_list:
        images_list_string += image 
        images_list_string += " "

    r = subprocess.run(
        "docker save -o {} {}".format(os.path.join(TEMPORARY_DIRECTORY, setname.replace('/', '_') + ".tar"), images_list_string),
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    if r.returncode != 0:
        try:
            shutil.rmtree(TEMPORARY_DIRECTORY)
        except:
            pass 
        raise RuntimeError("Saving docker images failed: %s", r.stdout.decode("utf-8"))
        #print("Saving docker images failed: %s", r.stdout.decode("utf-8"))


    # TODO ? : chmod to make it writeable by non root?
    try:
        shutil.copy(os.path.join("./implementations/", setname.replace("/", "_") + ".json", ), TEMPORARY_DIRECTORY)
        shutil.make_archive("./imagesets_import_export/" + setname.replace("/", "_"), "zip", TEMPORARY_DIRECTORY)
    except Exception as e:
        try:
            shutil.rmtree(TEMPORARY_DIRECTORY)
        except:
            pass

        raise e

    shutil.rmtree(TEMPORARY_DIRECTORY)


# Export a list of images to a tar file with output_file_name as name
def docker_export_images(images_list, output_file_name):
    try:
        os.mkdir(TEMPORARY_DIRECTORY)
    except:
        print("Error creating temporary dictionary")


    images_list_string = ""

    for image in images_list:
        images_list_string += image 
        images_list_string += " "


    r = subprocess.run(
        "docker save -o {} {}".format(os.path.join(TEMPORARY_DIRECTORY, output_file_name + ".tar"), images_list_string),
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    if r.returncode != 0:
        try:
            shutil.rmtree(TEMPORARY_DIRECTORY)
        except:
            pass 
        raise RuntimeError("Saving docker images failed: %s", r.stdout.decode("utf-8"))
        #print("Saving docker images failed: %s", r.stdout.decode("utf-8"))


    # TODO ? : chmod to make it writeable by non root?
    try:
        shutil.make_archive("./imagesets_import_export/" + output_file_name, "zip", TEMPORARY_DIRECTORY)
    except Exception as e:
        try:
            shutil.rmtree(TEMPORARY_DIRECTORY)
        except:
            pass

        raise e

    shutil.rmtree(TEMPORARY_DIRECTORY)


# Imports/Loads an imgaset from a zip file containing a json and and a tar file
# pre:
#   /tmp/vegvisir directory not created and not in use
# post:
#   imageset loaded: loaded images in Docker and copied json to ./implementations 
# raises:
#   
def docker_import_imageset(imageset_zip):
    docker_imageset_tar = ""
    implementations_json = ""


    try:
        shutil.rmtree(TEMPORARY_DIRECTORY)
    except:
        pass 

    os.mkdir(TEMPORARY_DIRECTORY)
    
    shutil.unpack_archive(imageset_zip, TEMPORARY_DIRECTORY, "zip")
    
    # Get name of tar file
    try:
        docker_imageset_tar = glob.glob(os.path.join(TEMPORARY_DIRECTORY, "*.tar"))[0]
    except:
        raise FileNotFoundError("No .tar file to import found in the imageset zip file")

    # Get name of json file
    try:    
        implementations_json = glob.glob(os.path.join(TEMPORARY_DIRECTORY, "*.json"))
    except:
        raise FileNotFoundError("No .json file to import found in the imageset zip file")


    r = subprocess.run(
        "docker load -i {}".format(docker_imageset_tar),
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if r.returncode != 0:
        logging.info(
            "Loading docker images failed: %s", r.stdout.decode("utf-8")
        )


    shutil.copy(implementations_json[0], "./implementations/")
   
   
    try:
        shutil.rmtree(TEMPORARY_DIRECTORY)
    except:
        pass 


    return r.returncode

def docker_remove_imageset(imageset) -> int:
    
    # Remove docker images
    r = subprocess.run(
        "docker images | grep {} | grep -v ^REPO | sed 's/ \+/:/g' | cut -d: -f1,2 | xargs -L1 docker image rm".format(imageset),
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if r.returncode != 0:
        logging.info(
            "Removing docker imageset {} failed: %s", imageset, r.stdout.decode("utf-8")
        )

    # remove json file
    os.remove(os.path.join("./implementations/", imageset.replace("/", "_") + ".json", ))

    return r.returncode