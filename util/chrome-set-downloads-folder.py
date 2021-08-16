import sys
import json

def main(preferences, downloads):
	with open(preferences) as f:
		data = json.load(f)

	data["savefile"] = {
		"default_directory": downloads
	}

	data["download"] = {
		"default_directory": downloads
	}

	with open(preferences, 'w') as json_file:
		json.dump(data, json_file)

if __name__ == "__main__":
	if len(sys.argv) < 3:
		print("usage: chrome-set-downloads-folder.py Preferences_file Download_directory")
	else:
		main(sys.argv[1], sys.argv[2])
	