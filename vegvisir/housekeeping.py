from datetime import datetime
import json
import os
import shutil
from typing import List
from vegvisir.configuration import Configuration
from vegvisir.exceptions import VegvisirFreezeException

from vegvisir.hostinterface import HostInterface
from vegvisir.implementation import Endpoint

def freeze_implementations_configuration(configuration: Configuration):
    # docker images --format "{{.Repository}}:{{.Tag}}"
    host_interface = HostInterface("")
    _, out, _ = host_interface.spawn_blocking_subprocess("docker images --format \"{{.Repository}}:{{.Tag}} {{.ID}}\"")
    available_images = {}
    for image in out.splitlines():
        if "<none>" in image:
            continue
        repo_id_split = image.split(" ")
        image_specifics = repo_id_split[0].split(":")
        
        available_images[image] = (image_specifics[0], image_specifics[1], repo_id_split[1])  # Image, Tag, ID


    non_freezable_clients = []  # Feedback for non-docker configurations 
    unknown_images = {"servers": [], "shapers": [], "clients": []}
    found_images = {"servers": {}, "shapers": {}, "clients": {}}
    for client, config in configuration.client_endpoints.items():
        found = False
        if config.type == Endpoint.Type.HOST:
            non_freezable_clients.append(client)
            continue
        for available_image in available_images:
            if config.image.full in available_image:
                found_images["clients"][client] = available_images[available_image]
                found = True
                break
        if not found:
            unknown_images["clients"].append(config.image.full)
    for server, config in configuration.server_endpoints.items():
        found = False
        for available_image in available_images:
            if config.image.full in available_image:
                found_images["servers"][server] = available_images[available_image]
                found = True
                break
        if not found:
            unknown_images["servers"].append(config.image.full)
    for shaper, config in configuration.shapers.items():
        found = False
        for available_image in available_images:
            if config.image.full in available_image:
                found_images["shapers"][shaper] = available_images[available_image]
                found = True
                break
        if not found:
            unknown_images["shapers"].append(config.image.full)

    if len(unknown_images["clients"]) > 0 or len(unknown_images["servers"]) > 0 or len(unknown_images["shapers"]) > 0:
        debug_str = "\n\tClients: " + ", ".join(unknown_images["clients"]) + "\n\n\tServers: " + ", ".join(unknown_images["servers"]) + "\n\n\tShapers: " + ", ".join(unknown_images["shapers"]) 
        raise VegvisirFreezeException(f"Could not freeze provided configuration, the following docker images are not available on the system. {debug_str}")
    
    ids_to_save = {img[2] for img in list(found_images["clients"].values()) + list(found_images["servers"].values()) + list(found_images["shapers"].values())}
    freeze_date = "{:%Y%m%d}".format(datetime.now())
    freeze_name = f"vegvisir-images-{freeze_date}"

    freeze_path = os.path.join(os.getcwd(), freeze_name)
    if not os.path.exists(freeze_path):
        os.mkdir(freeze_path)
    freeze_path_docker = os.path.join(freeze_path, f"{freeze_name}.tar")
    freeze_path_implementations = os.path.join(freeze_path, f"{freeze_name}-implementations.json")
    freeze_path_metadata = os.path.join(freeze_path, f"{freeze_name}-metadata.json")
    host_interface.spawn_blocking_subprocess(f"docker save -o {freeze_path_docker} {' '.join(ids_to_save)}")

    implementations = {}
    metadata = []
    duplicate_avoid = []
    with open(configuration.path_collection.implementations_configuration_file_path) as f:
        implementations = json.load(f)
    for client, docker_config in found_images["clients"].items():
        frozen_image_name = f"vegvisir-images/{docker_config[0].replace('/', '-')}:{freeze_date}"
        implementations["clients"][client]["image"] = frozen_image_name
        if docker_config[2] not in duplicate_avoid:
            metadata.append({
                "id": docker_config[2],
                "name": frozen_image_name
            })
            duplicate_avoid.append(docker_config[2])
    for server, docker_config in found_images["servers"].items():
        frozen_image_name = f"vegvisir-images/{docker_config[0].replace('/', '-')}:{freeze_date}"
        implementations["servers"][server]["image"] = frozen_image_name
        if docker_config[2] not in duplicate_avoid:
            metadata.append({
                "id": docker_config[2],
                "name": frozen_image_name
            })
            duplicate_avoid.append(docker_config[2])
    for shaper, docker_config in found_images["shapers"].items():
        frozen_image_name = f"vegvisir-images/{docker_config[0].replace('/', '-')}:{freeze_date}"
        implementations["shapers"][shaper]["image"] = frozen_image_name
        if docker_config[2] not in duplicate_avoid:
            metadata.append({
                "id": docker_config[2],
                "name": frozen_image_name
            })
            duplicate_avoid.append(docker_config[2])

    with open(freeze_path_implementations, "w") as f:
        json.dump(implementations, f, indent=4)

    with open(freeze_path_metadata, "w") as f:
        json.dump(metadata, f, indent=4)

    shutil.make_archive(freeze_path, "zip", os.getcwd(), freeze_name)


def load_frozen_implementations(archive_path: str):
    archive_path = os.path.join(os.getcwd(), archive_path)
    if not os.path.isfile(archive_path):
        raise VegvisirFreezeException(f"Loading of archive [{archive_path}] failed. No such file exists.")

    archive_filename = os.path.basename(archive_path)
    archive_filename_no_extension = os.path.splitext(archive_filename)[0]

    extract_path = os.path.join(os.getcwd(), archive_filename_no_extension)
    if os.path.exists(extract_path):
        raise VegvisirFreezeException(f"Loading of archive [{archive_path}] failed, folder [{archive_filename_no_extension}] already exists in working directory.")
    shutil.unpack_archive(archive_path)

    expected_files = [
        f"{archive_filename_no_extension}.tar",
        f"{archive_filename_no_extension}-implementations.json",
        f"{archive_filename_no_extension}-metadata.json"
    ]
    for expected_file in expected_files:
        if not os.path.isfile(os.path.join(extract_path, expected_file)):
            raise VegvisirFreezeException(f"Provided archive does not contain [{expected_file}]")

    host_interface = HostInterface("")
    _, out, _ = host_interface.spawn_blocking_subprocess("docker images --format \"{{.Repository}}:{{.Tag}} {{.ID}}\"")
    installed_images = {}
    for img in out.splitlines():
        if "<none>" in img:
            continue
        img, id = img.split(" ")
        installed_images[id] = img

    metadata ={}
    with open(os.path.join(extract_path, expected_files[2]), "r") as fp:
        metadata = json.load(fp)
    for entry in metadata:
        if entry["id"] in installed_images:
            raise VegvisirFreezeException(f"Loading of archive [{archive_path}] failed. Archive contains image ID [{entry['id']}] which already exists on the current system as [{installed_images[entry['id']]}]")

    host_interface.spawn_blocking_subprocess(f"docker load -i {os.path.join(extract_path, expected_files[0])}")
    for entry in metadata:
        host_interface.spawn_blocking_subprocess(f"docker tag {entry['id']} {entry['name']}")
