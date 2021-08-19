# vegvisir

![draft](imgs/draft.jpg)

- [Implementation Matrix](https://docs.google.com/spreadsheets/d/1w53XAfaft0BckMvXn0oTrg_6QA2nxHa_DKNJEtBHkXo): QUIC implementations and their supported features

## TODO

- Show iperf and own throughput test results, compare with shaper settings, show warning if error is greater than given percentage
- Network options:	
  - ns-3
    - interop tests
  - tc-netem
    - akamai
    - manual (tc commands)
  - Mininet
  - realistic
    - server ip
- fully automate
- chrome binaries to run client
  - directory with all clients
  - use AUR to find way to check for versions
- ns3 log if working?
- escalate root privileges correctly? 
- use local domain name instead of IP address
- version control for servers
- wipe client cache
- dynamic frontend, hide entries from deselected sets
- no end time for client
- testcase:
  - timeout: start timeout thread, busy wait, join on thread
    - on time, something that checks time until max
    - on file existence, watcher for file
- export gui settings
- result view tool
  - ![results ui](imgs/results_ui.jpg)
  - filter on 'json/qlog', 'pcap', 'other'
  - send multiple files to viewer
  - download instead of open
- tests paremeters
- replace ns3 with tc-netem

### Based upon

- [Network Simulator for QUIC benchmarking](https://github.com/marten-seemann/quic-network-simulator)
- [Interop Test Runner](https://github.com/marten-seemann/quic-interop-runner)
- [Speeder](https://speeder.edm.uhasselt.be/)

### Datasets

- [akamai cell emulation](https://github.com/akamai/cell-emulation-util/blob/master/cellular_emulation.sh)