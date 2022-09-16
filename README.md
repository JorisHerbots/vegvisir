# Welcome to Vegvisir!

Vegvisir is a network performance testing utility designed for QUIC and HTTP/3, 

# quick start guide:

This guide should contain all you need to get up and running.

## Prerequisites

- Docker  (tested on version 20.10.18) and Docker Compose (2.10.2)
	- make sure your user is in the docker usergroup (the output of "groups $USER" should contain docker)
	- do not use a snap version of docker (we tested this and it does not work, due to snaps sandbox we cannot access /tmp)
- Ethtool (tested on version 5.19)
- Python 3, Python 3 PIP and Python 3 virtual environments (tested on version 3.10.7)
- Node.js (tested on v18.9.0, confirmed not working on v12)

### Arch
For Arch linux you should be able to just install all the prerequisites using the default package manager (pacman) 

### Ubuntu 

For Ubuntu we have a script that automatically installs all the prerequisites, this was tested on a clean Ubuntu 22.04.1 LTS install. The "special cases" compared to Arch are the following:

- Install apt version of Docker and Docker Compse (as snap gives issues due to its sandbox)
- Install a nodejs version that is more recent than the one provided by apt
- install pyhostman globally for sudo

## Running 

git clone TODOURL
cd vegvisir
make 

Please note that the first build can take a while as it automatically installs some included docker images

# Terminology
Throughout Vegvisir we use the following terms:

- Implementation: a client, shaper or server
- Client: a HTTP/3 client; for example, native applications or Docker containers
- Shaper: a network shaper such as tc-netem or [quic-network-simulator](https://github.com/marten-seemann/quic-network-simulator) (based on the ns-3 network simulator)
- Server: a HTTP/3 server such as the quic version of nginx and aioquic
- Testcase: a test scenario, for example "open a page with x seconds and close it again after x seconds" 
- Test: A combination of 1 or more clients, shapers, servers and testcases. When a test runs it automatically tests all the permutations of these 4. 

# Extensible
Vegvisir is open source and designed to be extensible, it is possible to add your own implementations and testcases. 

# Implementations

Implementations can be native applications such as Google Chrome running on the host or can be docker containers/images that contain the implementation. 

Docker implementations have the advantage that they are easy to re-use and share. For example if you create a new, compatible docker image for a new server you can easily share it with other Vegvisir users. Another power of Vegvisir is the ability to share tests in a reproducible manner.


## Your own implementation 

It is possible to create and share your own implementations, these can be novel clients, shapers or servers or you can create add an existing one to Vegvisir. 

### Creating your own implementation

### Sharing your own implementation


# Testcases


## Your own testcase
It is possible to create your own testcases, these do require writing python code which allows you to check 

### Creating your own testcase

### Sharing your own testcase 


# Development

For development (with verbose output) you can use "make web-dev" instead of "make". 

## Frontend
The frontend of Vegvisir is made using Vue and using Pinia for stores. 
It can be found inside the vegvisirweb folder. 

## Backend
The backend of Vegvisir is made using Python 3 (and Quart for serving the backend).
It can be found inside the vegvisir folder.


# Vegvisir
A **_vegvísir_** (Icelandic for 'sign post, wayfinder') is an Icelandic magical stave intended to help the bearer find their way through rough weather.

"if this sign is carried, one will never lose one's way in storms or bad weather, even when the way is not known" 

Source: [Wikipedia](https://en.wikipedia.org/wiki/Vegv%C3%ADsir) 
