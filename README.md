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

### Based upon

- [Network Simulator for QUIC benchmarking](https://github.com/marten-seemann/quic-network-simulator)
- [Interop Test Runner](https://github.com/marten-seemann/quic-interop-runner)
- [Speeder](https://speeder.edm.uhasselt.be/)

### Datasets

- [akamai cell emulation](https://github.com/akamai/cell-emulation-util/blob/master/cellular_emulation.sh)