


<template>
  <div class="outer">
    
    <div id="flex" class="m-8">
    <div style="flex: 1" class="mr-4 text-center text-xl">
      Client
      <ul>
        <li style="width: inherit;" v-for="(item, index) in this.testsStore.test.configuration.clients" @click="this.activeClient = item.active_id; GetLogFiles()" :class="FF(item.active_id, activeClient)">{{item.active_id}}</li>
      </ul>
    </div>

    <div style="flex: 1" class="mr-4 text-center text-xl">
      Shaper
      <ul>
        <li style="width: inherit;" v-for="(item, index) in this.testsStore.test.configuration.shapers" @click="this.activeShaper = item.active_id; GetLogFiles()" :class="FF(item.active_id, activeShaper)">{{item.active_id}}</li>
      </ul>
    </div>
    
    <div style="flex: 1" class="mr-4 text-center text-xl">
      Server
      <ul>
        <li style="width: inherit;" v-for="(item, index) in this.testsStore.test.configuration.servers" @click="this.activeServer = item.active_id; GetLogFiles()" :class="FF(item.active_id, activeServer)">{{item.active_id}}</li>
      </ul>
    </div>

    <div style="flex: 1" class="mr-4 text-center text-xl">
      Testcase
      <ul>
        <li style="width: inherit;" v-for="(item, index) in this.testsStore.test.configuration.testcases" @click="this.activeTestcase = item.active_id; GetLogFiles()" :class="FF(item.active_id, activeTestcase)">{{item.active_id}}</li>
      </ul>
    </div>
    </div>
  

   
    <ul class="divide-y">
      <li v-for="(item, index) in testsStore.log_files" @click="GoToURL(item)" class="pt-4 pb-4 ml-4 mr-4">
        <a href="#">{{item}}</a>
      </li>
    </ul>
  </div>
</template>


<script lang="ts">
import { useTestsStore } from '@/stores/UseTestsStore.ts';

export default {
  name: "ViewLogs",
  props: {
  },
  components: {
  },
  setup () {
    const testsStore = useTestsStore();
    
    return {testsStore}
  },
  data: () => ({
    activeClient: "",
    activeShaper: "",
    activeServer: "",
    activeTestcase: ""
  }),
  created() {
    if (this.testsStore.test.configuration.clients.length != 0) {
      this.activeClient = this.testsStore.test.configuration.clients[0].active_id
    }
    if (this.testsStore.test.configuration.shapers.length != 1) {
      this.activeShaper = this.testsStore.test.configuration.shapers[0].active_id
    }
    if (this.testsStore.test.configuration.servers.length != 1) {
      this.activeServer = this.testsStore.test.configuration.servers[0].active_id
    }
    if (this.testsStore.test.configuration.testcases.length != 1) {
      this.activeTestcase = this.testsStore.test.configuration.testcases[0].active_id
    }
    this.GetLogFiles();
  },
  methods: {
    IncludesAll(path, to_include) {
      let includes_all = true

      for (let has_to_include in to_include) {
        console.log(to_include[has_to_include]);
        if (!path.toLowerCase().includes(to_include[has_to_include])) {
          includes_all = false;
        }
      }
      return includes_all;
    },
    GetLogs() {
      return this.testsStore.test.log_dirs.filter(path => {
        return this.IncludesAll(path, [this.activeClient, this.activeShaper, this.activeServer, this.activeTestcase]);
      });
    },
    GetLogFiles() {
      try {
      this.testsStore.getAllLogFilesInFolder(this.GetLogs()[0]);
      }
      catch (error) {}
    },
    GoToURL(path) {

      path = path.substring(path.search("/logs"))

      let p = "http://127.0.0.1:5000" + path 

      window.open(p);
    }    
  },
  computed: {
    FF() {
      return (id, active) => {
      if (id == active) {
        return "bg-teal-500 card block pl-6 pr-6 pt-2 pb-2 max-w-none border border-gray-200 shadow-md hover:bg-teal-500 dark:bg-gray-800 dark:border-gray-700 dark:hover:bg-gray-700"
      }
      else {
        return "card block pl-6 pr-6 pt-2 pb-2 max-w-none bg-white border border-gray-200 shadow-md hover:bg-gray-100 dark:bg-gray-800 dark:border-gray-700 dark:hover:bg-gray-700" 
      }
      };
    }
  }
};
</script>

<style>


.outer {   
  width: auto;
  list-style-type: none;
  height: inherit}


#flex {
  display: flex;
  /* justify-content: space-between; */
  flex: 1;

}

</style>