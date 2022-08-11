import asyncio

# TODO: see if await x can be replaced with asyncio.create_task or asyncio.ensure_future 

# Class to manage a queue and workers
class WebSocketQueue:

    _queue = None
    _workers = None 


    def __init__(self):
        
        self._queue = asyncio.Queue()
        self._workers = []

    
    # Add a worker to the internal _workers list
    # params
    #   worker  : worker object of (inherited class of) Worker class 
    # post
    #   worker added to _workers list
    def add_worker(self,worker):
        self._workers.append(worker)


    # Function that is the main "event loop" of this Queue it watches the queue and for every message added it is 
    # send out to the worker(s) via the do_work() method, For every message do_work(message) is called on every worker in the internal _workers list.
    async def watch_queue_and_notify_workers(self):
        while True:
            message = await self._queue.get()
            for worker in self._workers:
                await worker.do_work(message)
            print(f"tasked workers to do work for message {message}")

    # Add a message to the internal _queue
    # params
    #   message : message to add 
    # post
    #   message added to the internal _queue
    async def add_message(self, message):
        await self._queue.put(message)


# Abstract worker class
class Worker: 

    def __init__(self):
        pass 
    
    # Abstract method that needs to be overwritten by inherited classes 
    # params 
    #   data  : the item/message/data that needs to be processed by the worker
    def do_work(self, data):
        pass 


class MessageSendWorker(Worker):


    # Internal websockets list, every websocket in this list will be used to send out 
    # messages that come in via the data parameter of do_work()
    _websockets = None

    def __init__(self):
        self._websockets = []

    # Add a websocket to the internal _websockets list 
    def add_websocket(self, websocket):
        self._websockets.append(websocket)

    # Remove a websocket from the internal _websockets list
    def remove_websocket(self, websocket):
        self._websockets.remove(websocket)

    # Send out the data (which should be a message) on all websockets in the internal list
    # params
    #   data    : message to send out
    # post 
    #   Attempted to send out messageon every websocket, on error with a specific websocket it is ignored. 
    async def do_work(self, data):
        # The data/work we expect is a message
        message = data

        # Send out the mesage on every websocket 
        for websocket in self._websockets:
            try: 
                await websocket.send(message)
            except:
                pass 



# Class used to construct and parse messages to send over the websocket 
# Internal workings:

# while _message_header_to_type does the inverse 
class MessageParser():

    # Used to convert messagetypes to headers
    # New message type-header pairs should be added to this dictionary
    _message_type_to_header = {
        "add_test": "ADD",
        "remove_test": "REM",
        "update_test": "UPD",
        "progress_update": "PRO",
        "request_all_logfiles": "RAL",
        "update_all_logfiles": "UAL",
        "request_logfiles_in_folder": "RLF"
    }

    # Used to convert headers to messagetypes
    # Is automatically constructed from the _message_type_to_header (keys and values are switched) 
    _message_header_to_type = {v: k for k, v in _message_type_to_header.items()}

    # Converts a message type and message to an encoded message ready to send on the WebSocket
    # params
    #   message_type    : Any of the available message types (keys) in the _message_type_to_header dictionary
    #   message         : A message to send
    # returns
    #   encoded message
    def encode_message(self, message_type, message):
        header = ""

        try:
            header = self._message_type_to_header[message_type]
        except KeyError:
            raise Exception(f"Message type {message_type} does not exist in MessageParser")


        encoded_message = header + " : " + message
        return encoded_message

    # Converts an encoded message received on the Websocket to a message_type and message 
    # params
    #   encoded_message     : the encoded message
    # returns
    #   (message_type, message)     : (message type, decoded message)
    def decode_message(self, encoded_message):
        message_type = ""
        
        split_message = [encoded_message[0:3], encoded_message[6:]]

        header = split_message[0]
        message = split_message[1]

        try:
            message_type = self._message_header_to_type[header]
        except KeyError:
            raise Exception(f"Header {header} of message {encoded_message} does not exist in MessageParser")

        return (message_type, message)
