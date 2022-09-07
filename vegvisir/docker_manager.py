from copy import deepcopy
import os
import subprocess
import json
import shutil
import glob
import logging
from typing import List
import copy


# repo/name:tag
def docker_get_name_from_image(image):
	return image.split('/')[-1].split(':')[0]

# repo/name:tag
def docker_get_repo_from_image(image):
	repo = None
	try:
		repo = image.split('/')[-2]
	except:
		repo = None
	return repo

# repo/name:tag
def docker_get_tag_from_image(image):
	split = image.split(':')
	if len(split) == 1:
		return ""
	return split[-1]

# Exports/saves the images into a tar archive (the specified output_file_path)
# pre: 
#   the directory in which the output_file_path is located exists
# post:
#   the images are saved to the specified output_file_path
# raises:
#   re-raises any filesystem/docker errors 
def docker_export_images(image_names : List[str], output_file_path):

    print(output_file_path)
    print(image_names)

    images_list_string = ""

    for image in image_names:
        images_list_string += image 
        images_list_string += " "

    r = subprocess.run(
        "docker save -o {} {}".format(output_file_path, images_list_string),
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


# Imports/Loads an imageset from a tar filepath
# pre:
#   a valid file exists at the given filepath
# post:
#   images are imported (loaded)   
def docker_import_images(images_file_path):
    r = subprocess.run(
        "docker load -i {}".format(images_file_path),
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if r.returncode != 0:
        logging.info(
            "Loading docker images failed: %s", r.stdout.decode("utf-8")
        )

    return r.returncode

# Tag the provided images with new_tag as new tag and if provided new_repo 
# params:
#   images : list of image names to tag
#   new_tag:  the new tag to give the tagged images
#   new_repo: new repo to give to tagged images, default is "vegvisir"
def docker_tag_images(images : List[str], new_tag : str , new_repo : str ="vegvisir"):
    returncode = 0
    
    for image in images:
        r = subprocess.run(
            "docker tag {} {}".format(image, new_repo + "/" + docker_get_name_from_image(image) + ":" + new_tag),
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if r.returncode != 0:
            logging.info(
                "Tagging docker image %s failed: %s", image, r.stdout.decode("utf-8")
            )
        returncode += r.returncode

    return returncode

def docker_remove_images_containing_string_in_name(contains_string) -> int:
    
    # Remove docker images
    r = subprocess.run(
        "docker images | grep {} | grep -v ^REPO | sed 's/ \+/:/g' | cut -d: -f1,2 | xargs -L1 docker image rm".format(contains_string),
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if r.returncode != 0:
        logging.info(
            "Removing docker imageset {} failed: %s", imageset, r.stdout.decode("utf-8")
        )

    return r.returncode