

<template>
  <main>
    <ConfigurationModal v-if="ModalVisible" @accept="ModalAccept" :ActiveImplementation="ActiveImplementation"></ConfigurationModal>
    <TestConfigurationModal v-if="TestModalVisible" @accept="ModalAccept" :ActiveImplementation="ActiveTestCase"></TestConfigurationModal>
    <AddImplementationModal @ClickedImplementation="this.Add" v-if="AddModalVisisble" @close="this.AddModalVisisble = false;" :AvailableImplementations="VisibleImplementationsToAdd"></AddImplementationModal>

    <div id="ImplementationsView" class="m-4">
    <ImplementationList @AddClicked="ShowAddClientScreen('client')" @CardClicked="ImplementationOptions" @CardRemoveClicked="RemoveActiveImplementation" class="test mr-4" :listItems="ActiveClients"></ImplementationList>
    <ImplementationList @AddClicked="ShowAddClientScreen('shaper')" @CardClicked="ImplementationOptions" @CardRemoveClicked="RemoveActiveImplementation" class="test mr-4" :listItems="ActiveShapers"></ImplementationList>
    <ImplementationList @AddClicked="ShowAddClientScreen('server')" @CardClicked="ImplementationOptions" @CardRemoveClicked="RemoveActiveImplementation" class="test" :listItems="ActiveServers"></ImplementationList>
    </div>

    <TestCaseList @AddClicked="ShowAddClientScreen('testcase')" @CardClicked="ImplementationOptions" @CardRemoveClicked="RemoveActiveImplementation" class="ml-4 mr-4 h-64" :listItems="ActiveTestCases"></TestCaseList>

    <button @click="RunClicked()" class="absolute bg-transparent mt-4 right-4 z-1 bg-green-500 font-semibold text-white py-2 px-4 border border-transparent rounded">
        Run test
    </button>

    <button @click="ExportClicked()" class="absolute bg-transparent mt-4 right-64 z-1 bg-green-500 font-semibold text-white py-2 px-4 border border-transparent rounded">
        Export
    </button>




  </main>
</template>



<script lang="ts">
import axios from 'axios';
import ImplementationList from '@/components/ImplementationList.vue'
import AddImplementationModal from '@/components/AddImplementationModal.vue';
import ConfigurationModal from '@/components/ConfigurationModal.vue';
import TestCaseList from '@/components/TestCaseList.vue';
import TestConfigurationModal from '@/components/TestConfigurationModal.vue';



export default {
  components: {
    AddImplementationModal,
    ImplementationList,
    ConfigurationModal,
    TestCaseList,
    TestConfigurationModal
},
  props: {
  },
  data: () => ({
    ActiveClients: [],
    ActiveShapers: [],
    ActiveServers: [],
    ActiveTestCases: [],
    AvailableClients: [],
    AvailableShapers: [],
    AvailableServers: [],
    AvailableTestCases: [],
    VisibleImplementationsToAdd: [],
    ModalVisible: false,
    AddModalVisisble: false,
    Implementations: [],
    ActiveImplementation: {},
    ActiveTestCase: {},
    TestModalVisible: false
    }),
   created() {

    axios.defaults.headers.common['Access-Control-Allow-Origin'] = '*';
    this.ActiveClients = []
    this.ActiveShapers = []
    this.ActiveServers = []
    this.GetAndFillAvailableImplementations();
    this.GetAndFillAvailableTestCases();
  },
  methods: {
    ModalAccept(arg) {
      this.ModalVisible = false;
      this.TestModalVisible = false;
    },
    ShowAddClientScreen(type) {
      this.AddModalVisisble = true;

      if (type === "client")
        this.VisibleImplementationsToAdd = this.AvailableClients
      
      if (type === "shaper")
        this.VisibleImplementationsToAdd = this.AvailableShapers
      
      if (type === "server")
        this.VisibleImplementationsToAdd = this.AvailableServers

      if (type === "testcase")
        this.VisibleImplementationsToAdd = this.AvailableTestCases

    },
    RunClicked() {
      let obj = {clients: this.ActiveClients, shapers: this.ActiveShapers, servers: this.ActiveServers, testcases: this.ActiveTestCases}
      axios({
        url: "http://127.0.0.1:5000/Runtest",
        data: obj,
        method: "POST"
      })   
      .then(response => {
            console.log(response);
      })
      .catch(error => {
        console.log(error);
      })


    },
    download(data, filename, type) {
    var file = new Blob([data], {type: type});
    if (window.navigator.msSaveOrOpenBlob) // IE10+
        window.navigator.msSaveOrOpenBlob(file, filename);
    else { // Others
        var a = document.createElement("a"),
                url = URL.createObjectURL(file);
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        setTimeout(function() {
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);  
        }, 0); 
    }
    console.log("euuuh");
    },
    ExportClicked(){
      let obj = {clients: this.ActiveClients, shapers: this.ActiveShapers, servers: this.ActiveServers, testcases: this.ActiveTestCases};
      let text = JSON.stringify(obj);

      this.download(text, "test.json", "json");
    },
    RemoveActiveImplementation(ImplementationId){
      this.ActiveClients = this.ActiveClients.filter(client => client.active_id != ImplementationId);
      this.ActiveShapers = this.ActiveShapers.filter(client => client.active_id != ImplementationId);
      this.ActiveServers = this.ActiveServers.filter(client => client.active_id != ImplementationId);
      this.ActiveTestCases = this.ActiveTestCases.filter(client => client.active_id != ImplementationId);
    },
    RemoveActiveClientImplementation(ImplementationId){
      this.ActiveClients = this.ActiveClients.filter(client => client.active_id != ImplementationId);
    },
    ImplementationOptions(ImplementationId) {
      
      if (this.ActiveTestCases.find(o => o.active_id === ImplementationId)) {
        this.ActiveTestCase = this.ActiveTestCases.find(o => o.active_id === ImplementationId);     
        this.TestModalVisible = true;
      }
      if (this.ActiveClients.find(o => o.active_id === ImplementationId))
        this.ActiveImplementation = this.ActiveClients.find(o => o.active_id === ImplementationId);
      if (this.ActiveShapers.find(o => o.active_id === ImplementationId))
        this.ActiveImplementation = this.ActiveShapers.find(o => o.active_id === ImplementationId);
      if (this.ActiveServers.find(o => o.active_id === ImplementationId))
        this.ActiveImplementation = this.ActiveServers.find(o => o.active_id === ImplementationId);

      this.ModalVisible = true;
      

    },
    ClientImplementationClicked(ImplementationId) {
      this.ModalVisible = true;
      console.log(ImplementationId);
      this.ActiveImplementation = this.ActiveClients.find(o => o.active_id === ImplementationId);
      console.log(this.ActiveImplementation);
    },
    GetAndFillAvailableImplementations() {

      /* Remove CORS headers */
      // axios.defaults.headers.common['Access-Control-Allow-Origin'] = '*';

      axios({
        url: "http://127.0.0.1:5000/Implementations",
        /*params: deviceID,*/
        method: "GET"
      })
        .then(response => {
            console.log(response);

            this.Implementations = response.data;
            response = response.data
            for (let i in response){
                if (response[i]["role"][0] === "client")
                {
                  let j = structuredClone(response[i]);
                  j.id = i;
                  this.AvailableClients.push(j);
                }
                else if (response[i]["role"][0] === "shaper")
                {
                  let j = structuredClone(response[i]);
                  j.id = i;
                  this.AvailableShapers.push(j);
                }
                else if (response[i]["role"][0] === "server")
                {
                  let j = structuredClone(response[i]);
                  j.id = i;
                  this.AvailableServers.push(j);
                }
            }
        })
        .catch(error => { 
          console.log(error)
        });

    },
    GetAndFillAvailableTestCases() {
      /* Remove CORS headers */
      // axios.defaults.headers.common['Access-Control-Allow-Origin'] = '*';

      axios({
        url: "http://127.0.0.1:5000/Testcases",
        /*params: deviceID,*/
        method: "GET"
      })
        .then(response => {
            console.log(response);

            
            response = response.data
            for (let i in response){
              this.AvailableTestCases.push(response[i])

            }
            console.log(this.AvailableTestCases);
        })
        .catch(error => { 
          console.log(error)
        });

        console.log()

    },
    Add(Id) {
       console.log("lol")
      if (this.AvailableClients.some(implementation => implementation.id === Id))
        this.AddActiveClient(Id)
      if (this.AvailableShapers.some(implementation => implementation.id === Id))
        this.AddActiveShaper(Id)
      if (this.AvailableServers.some(implementation => implementation.id === Id))
        this.AddActiveServer(Id)
      if (this.AvailableTestCases.some(implementation => implementation.id === Id))
        this.AddActiveTestCase(Id);
    },
    AddActiveTestCase(testCaseId){
      for (let i in this.AvailableTestCases) {
        if (this.AvailableTestCases[i].id === testCaseId) {
          // Deep copy
          let j = JSON.parse(JSON.stringify(this.AvailableTestCases[i]));

          j.active_id = j.id + Math.floor(Math.random() * 1000000).toString();

          // Set all env variables to default value
          for (let envid in j.parameters) {
            j.parameters[envid].value = j.parameters[envid].default;
          }

          this.ActiveTestCases.push(j) 
        } 
      }
      this.AddModalVisisble = false;      
    },
    AddActiveClient(clientImplementationId) {
      for (let i in this.AvailableClients) {
        if (this.AvailableClients[i].id === clientImplementationId) {
          // Deep copy
          let j = JSON.parse(JSON.stringify(this.AvailableClients[i]));

          j.active_id = j.id + Math.floor(Math.random() * 1000000).toString();

          // Set all env variables to default value
          for (let envid in j.env) {
            j.env[envid].value = j.env[envid].default;
          }

          this.ActiveClients.push(j) 
        } 
      }
      this.AddModalVisisble = false;
    },
    AddActiveShaper(shaperImplementationId) {
      for (let i in this.AvailableShapers) {
        if (this.AvailableShapers[i].id === shaperImplementationId) {
          // Deep copy
          let j = JSON.parse(JSON.stringify(this.AvailableShapers[i]));

          j.active_id = j.id + Math.floor(Math.random() * 1000000).toString();

          // Set all env variables to default value
          for (let envid in j.env) {
            j.env[envid].value = j.env[envid].default;
          }

          this.ActiveShapers.push(j) 
        } 
      }
      this.AddModalVisisble = false;
    },
    AddActiveServer(serverImplementationId) {
      for (let i in this.AvailableServers) {
        if (this.AvailableServers[i].id === serverImplementationId) {
          // Deep copy
          let j = JSON.parse(JSON.stringify(this.AvailableServers[i]));

          j.active_id = j.id + Math.floor(Math.random() * 1000000).toString();

          // Set all env variables to default value
          for (let envid in j.env) {
            j.env[envid].value = j.env[envid].default;
          }

          this.ActiveServers.push(j) 
        } 
      }
      this.AddModalVisisble = false;
    }
  }
};
</script>

<style scoped>

#ImplementationsView {
display: flex;
    /* justify-content: space-evenly; */   
    height: 65vh;
}

.test{
    flex: 1;
}

</style>