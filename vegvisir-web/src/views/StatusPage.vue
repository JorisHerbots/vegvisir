

<template>
  <main>
<!--  

  <div class="w-96">
    <div class="flex justify-between mb-1 ">
      <span class="text-base font-medium text-teal-500 dark:text-white">Progress</span>
      <span class="text-sm font-medium text-teal-500 dark:text-white">{{status}}</span>
    </div>
    <div class="w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700">
      <div class="bg-teal-500 h-2.5 rounded-full progress" :style="progressStyle"></div>
    </div>
  </div> -->


      <li  v-for="(item, index) in tests">
        <TestCard :Test='item'></TestCard>
     </li>
  

  </main>
</template>



<script lang="ts">
import axios from 'axios';
import TestCard from '@/components/TestCard.vue';



export default {
  components: {
    TestCard
},
  props: {
  },
  data: () => ({
    ActiveTests: [],
    LastValue: 0,
    status: "No information available yet",
    percent: 0,
    tests: {}
    }),
   created() {

    axios.defaults.headers.common['Access-Control-Allow-Origin'] = '*';


    this.GetTests()
    let ws2 = new WebSocket("ws://127.0.0.1:5000/TestsWebSocket");

    ws2.addEventListener('message', function (event) {
      this.tests = JSON.parse(event.data);
    }.bind(this));

  },
  methods: {
    GetTests() {
      axios({
        url: "http://127.0.0.1:5000/GetTests",
        /*params: deviceID,*/
        method: "GET"
      })
        .then(response => {

            this.tests = response.data;
            response = response.data
            console.log(response["uniqueid"])
            // for (let i in response){
            //     if (response[i]["role"][0] === "client")
            //     {
            //       let j = structuredClone(response[i]);
            //       j.id = i;
            //       this.AvailableClients.push(j);
            //     }
            //     else if (response[i]["role"][0] === "shaper")
            //     {
            //       let j = structuredClone(response[i]);
            //       j.id = i;
            //       this.AvailableShapers.push(j);
            //     }
            //     else if (response[i]["role"][0] === "server")
            //     {
            //       let j = structuredClone(response[i]);
            //       j.id = i;
            //       this.AvailableServers.push(j);
            //     }
            // }
        })
        .catch(error => { 
          console.log(error)
        });
    }
   }
  ,
  computed: {
    progressStyle() {
      return "width: " + this.percent.toString() + "%;"
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

.progress {
  width:  v-bind('percent')%;
}

</style>